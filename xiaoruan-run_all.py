
import os
import sys
import ast
import time
import queue
import threading
import subprocess
import fcntl
import shutil
import random
from pathlib import Path

import requests

# ============================================================
# TELEGRAM
# ============================================================

BOT_TOKEN = "8994992623:AAGc4TRHHEPHujeOUCa9VBPCYIR3bff6r6Y"
CHAT_ID = "-5268959413"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1gfsTt_nL0wK2mepUAXkBgRqZHLYRY3xqWmbAxkzp0ao/edit?pli=1&gid=846636141#gid=846636141"
WEB_URL = "https://xiafaxiaoliansocute-stack.github.io/76b-xiaoruan/"

# ============================================================
# PROJECT PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

# ============================================================
# NETWORK / RETRY POLICY
# ============================================================
# Giữ nguyên logic cũ, chỉ tăng khả năng chịu lỗi mạng tạm thời.
TELEGRAM_MAX_RETRIES = 6
TELEGRAM_RETRY_BASE_SECONDS = 2
TELEGRAM_TIMEOUT = (10, 30)

WORKER_RESTART_ALERT_AFTER = 5   # Chỉ cảnh báo Telegram sau nhiều lần restart liên tiếp.
WORKER_RESTART_BASE_SECONDS = 5
WORKER_RESTART_MAX_SECONDS = 60
WORKER_STABLE_RESET_SECONDS = 300  # Chạy ổn 5 phút thì reset bộ đếm restart liên tiếp.

# Auto Hot Reload: chỉ theo dõi đúng file chính của từng task trong TASKS.
# Save nhiều lần liên tiếp sẽ được gộp lại, chỉ reload sau khi file ổn định.
HOT_RELOAD_CHECK_SECONDS = 1.0
HOT_RELOAD_DEBOUNCE_SECONDS = 2.0
HOT_RELOAD_GRACEFUL_STOP_SECONDS = 5.0


# ============================================================
# SINGLE INSTANCE / PROCESS SAFETY
# ============================================================

RUN_ALL_LOCK_FILE = BASE_DIR / ".run_all.lock"
_run_all_lock_handle = None


def acquire_single_instance_lock():
    """Chỉ cho phép 1 bản RUN ALL chạy tại một thời điểm."""
    global _run_all_lock_handle

    _run_all_lock_handle = open(RUN_ALL_LOCK_FILE, "w")

    try:
        fcntl.flock(
            _run_all_lock_handle.fileno(),
            fcntl.LOCK_EX | fcntl.LOCK_NB
        )
    except BlockingIOError:
        print("❌ RUN ALL 已经在运行，禁止重复启动。")
        return False

    _run_all_lock_handle.write(str(os.getpid()))
    _run_all_lock_handle.flush()
    return True


def find_script_processes(script_path):
    """Tìm process Python đang chạy đúng script_path."""
    target = str(Path(script_path).resolve())
    found = []

    try:
        result = subprocess.run(
            ["ps", "-axo", "pid=,command="],
            capture_output=True,
            text=True,
            check=False
        )

        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            parts = line.split(None, 1)
            if len(parts) != 2:
                continue

            try:
                pid = int(parts[0])
            except ValueError:
                continue

            command = parts[1]

            if pid == os.getpid():
                continue

            if target in command:
                found.append(pid)

    except Exception as e:
        print(f"[Process Check Error] {e}")

    return found


def stop_existing_script_processes(script_path):
    """Dừng TELEGRAM_BOT cũ để tránh Conflict getUpdates."""
    pids = find_script_processes(script_path)

    for pid in pids:
        try:
            print(f"⚠️ Stop duplicate process PID={pid}: {script_path}")
            os.kill(pid, 15)
        except ProcessLookupError:
            pass
        except Exception as e:
            print(f"⚠️ Cannot stop PID={pid}: {e}")

    if pids:
        time.sleep(2)

        for pid in pids:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                continue
            except Exception:
                continue

            try:
                print(f"⚠️ Force stop duplicate PID={pid}")
                os.kill(pid, 9)
            except Exception:
                pass


# ============================================================
# TASK CONFIG
# ============================================================

TASKS = [
    {
        "name": "数据跟进",
        "type": "数据跟进",
       "file": BASE_DIR / "shujugenjin" / "shujugenjin.py",
    },

    {
        "name": "TELEGRAM_BOT",
        "type": "TELEGRAM_BOT",
        "file": BASE_DIR / "telegram_bot.py",
    },

    {
        "name": "全局报表",
        "type": "全局报表",
        "file": BASE_DIR / "quanju-baobiao" / "runquanju.py",
    },

    {
        "name": "推广汇总",
        "type": "推广汇总",
        "file": BASE_DIR / "run_forever.py",
    },
    {
        "name": "检查彩金",
        "type": "检查彩金",
        "file": BASE_DIR / "jiancha.py",
    },
   {
        "name": "游戏跟进",
        "type": "游戏跟进",
        "file": BASE_DIR / "test-data-py" / "datahuiyuan.py",
    },       
   {
        "name": "K1自动",
        "type": "K1自动",
        "file": BASE_DIR / "test-data-py" / "K1.py",
    },
   {
        "name": "操作记录",
        "type": "操作记录",
        "file": BASE_DIR / "caozuojilu.py",
    },          
   {
        "name": "菲律宾",
        "type": "菲律宾",
        "file": "/Users/xiaoruan/Documents/philippin/run.py",
    },   
]

# ============================================================
# GLOBAL
# ============================================================

workers = []

# Khóa danh sách worker khi thêm task động trong lúc hệ thống đang chạy.
WORKERS_LOCK = threading.RLock()

# Dynamic TASKS: khi chính file RUN ALL được Save, hệ thống đọc lại biến TASKS
# và tự start các task mới mà không cần restart RUN ALL.
DYNAMIC_TASK_CHECK_SECONDS = 1.0
DYNAMIC_TASK_DEBOUNCE_SECONDS = 2.0

lock = threading.Lock()

# ============================================================
# TELEGRAM
# ============================================================

def telegram(text):
    """Gửi Telegram có retry/backoff; lỗi mạng tạm thời không báo đỏ ngay."""

    if not text:
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text[:4000],
        "disable_web_page_preview": True,
        "parse_mode": "HTML",
    }

    last_error = None

    for attempt in range(1, TELEGRAM_MAX_RETRIES + 1):
        try:
            resp = requests.post(
                url,
                data=payload,
                timeout=TELEGRAM_TIMEOUT,
            )

            # 429/5xx thường là tạm thời -> retry.
            if resp.status_code == 429 or 500 <= resp.status_code <= 599:
                retry_after = None
                try:
                    retry_after = int(resp.json().get("parameters", {}).get("retry_after", 0) or 0)
                except Exception:
                    retry_after = 0
                raise requests.RequestException(
                    f"Telegram HTTP {resp.status_code}; retry_after={retry_after}"
                )

            resp.raise_for_status()
            return True

        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.RequestException,
        ) as e:
            last_error = e

            if attempt >= TELEGRAM_MAX_RETRIES:
                break

            delay = min(
                TELEGRAM_RETRY_BASE_SECONDS * (2 ** (attempt - 1)),
                30,
            )
            delay += random.uniform(0, 0.8)
            print(
                f"[Telegram Retry] {attempt}/{TELEGRAM_MAX_RETRIES} - "
                f"{type(e).__name__}: {e} | retry in {delay:.1f}s"
            )
            time.sleep(delay)

        except Exception as e:
            # Lỗi không phải mạng/API tạm thời: không retry vô ích.
            last_error = e
            break

    print(f"[Telegram Error] after {TELEGRAM_MAX_RETRIES} attempts: {last_error}")
    return False

# ============================================================
# LOG
# ============================================================

def log(name, text):

    with lock:

        print(f"[{name}] {text}")

# ============================================================
# CHECK FILE
# ============================================================

def check_file(path):

    if path.exists():
        return True

    telegram(
        "❌ File not found\n\n"
        f"{path}"
    )

    print(f"❌ File not found : {path}")

    return False


# ============================================================
# ALWAYS LOAD LATEST CHILD FILES
# ============================================================

def clear_python_cache(script_path):
    """Xóa __pycache__ trước khi chạy để luôn nạp code/config .py mới nhất đã lưu."""
    script_dir = Path(script_path).resolve().parent

    try:
        for cache_dir in script_dir.rglob("__pycache__"):
            try:
                shutil.rmtree(cache_dir, ignore_errors=True)
            except Exception:
                pass
    except Exception as e:
        print(f"[Cache Clean Warning] {script_dir}: {e}")


def fresh_child_env():
    """Môi trường subprocess: không ghi bytecode cache và giữ stdout realtime."""
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    return env

# ============================================================
# BANNER
# ============================================================

def banner():

    print()

    print("=" * 70)
    print("           XIAORUAN RUN ALL v2.0")
    print("=" * 70)

    print(f"Python : {sys.executable}")
    print(f"Project: {BASE_DIR}")

    print("=" * 70)

    for task in TASKS:

        status = "✅" if Path(task["file"]).exists() else "❌"

        print(
            f"{status} {task['name']:<10} {task['file']}"
        )

    print("=" * 70)
    print()

# ============================================================
# START MESSAGE
# ============================================================

def startup_message():

    lines = [

        "🚀 🚀 开始执行全部任务....",

        "",

        f"Python : {sys.executable}",

        f"Folder : {BASE_DIR}",

        "",

        "Task List:",

    ]

    for task in TASKS:

        if task["file"].exists():

            lines.append(
                f"✅ {task['name']}"
            )

        else:

            lines.append(
                f"❌ {task['name']}"
            )

    telegram("\n".join(lines))
    # ============================================================
# WORKER
# ============================================================

class Worker:

    def __init__(self, cfg):

        self.name = cfg["name"]
        self.type = cfg["type"]
        self.file = Path(cfg["file"])

        self.process = None
        self.thread = None

        self.running = False
        self.finished = False
        self.restarting = False

        self.restart_count = 0
        self.consecutive_restarts = 0
        self.last_started_at = 0.0
        self.alerted_restart_storm = False
        self.intentional_reload = False
        self.last_loaded_mtime_ns = self._get_file_mtime_ns()
        self.lock = threading.Lock()

    def _get_file_mtime_ns(self):
        try:
            return self.file.stat().st_mtime_ns
        except Exception:
            return 0

    # ========================================================

    def start(self):

        with self.lock:

            if self.running:
                return

            if not check_file(self.file):
                self.restarting = False
                return

            self.finished = False

            # TELEGRAM polling chỉ được có 1 instance.
            if self.type == "TELEGRAM_BOT":
                stop_existing_script_processes(self.file)

            log(self.name, "=" * 60)
            log(self.name, "START")
            log(self.name, str(self.file))
            log(self.name, "=" * 60)

            try:

                # Luôn chạy theo file con mới nhất vừa lưu, tránh dùng __pycache__ cũ.
                clear_python_cache(self.file)

                file_mtime = time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(self.file.stat().st_mtime)
                )
                log(self.name, f"LOAD LATEST SAVED FILE : {file_mtime}")

                self.process = subprocess.Popen(

                    [sys.executable, "-B", "-u", str(self.file)],

                    cwd=str(self.file.parent),

                    stdout=subprocess.PIPE,

                    stderr=subprocess.STDOUT,

                    text=True,

                    encoding="utf-8",

                    errors="ignore",

                    bufsize=1,

                    env=fresh_child_env(),

                )

            except Exception as e:

                self.restarting = False

                # Nếu đây là lần start do Hot Reload sau khi Save thì chỉ ghi log.
                # Auto-recovery phía sau sẽ tự thử lại và chỉ cảnh báo Telegram
                # khi lỗi kéo dài vượt ngưỡng như policy chung.
                if self.intentional_reload:
                    log(self.name, f"Hot reload start error: {type(e).__name__}: {e}")
                else:
                    telegram(
                        f"❌ {self.name}\n\n"
                        f"Start Failed\n\n"
                        f"{e}"
                    )

                return

            self.running = True
            self.restarting = False
            self.intentional_reload = False
            self.last_started_at = time.time()
            self.last_loaded_mtime_ns = self._get_file_mtime_ns()

            self.thread = threading.Thread(
                target=self.reader,
                daemon=True,
                name=f"{self.name}_reader"
            )

            self.thread.start()

    # ========================================================

    def stop(self):

        with self.lock:

            self.running = False

            try:
                if self.process:
                    self.process.kill()
            except:
                pass

    # ========================================================

    def hot_reload(self):
        """Reload đúng worker này khi file chính được Save; hoàn toàn im lặng trên Telegram."""
        with self.lock:
            if self.restarting or self.intentional_reload:
                return False

            self.intentional_reload = True
            proc = self.process
            self.running = False

        log(self.name, "🔄 检测到文件更新，正在加载最新代码...")

        # Đây là reload chủ động, không phải lỗi -> không tăng bộ đếm restart.
        self.consecutive_restarts = 0
        self.alerted_restart_storm = False

        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=HOT_RELOAD_GRACEFUL_STOP_SECONDS)
            except subprocess.TimeoutExpired:
                try:
                    proc.kill()
                    proc.wait(timeout=2)
                except Exception:
                    pass
            except Exception as e:
                log(self.name, f"Hot reload stop warning: {e}")

        # Đợi reader cũ rời finally trước khi start process mới để tránh race.
        old_thread = self.thread
        if old_thread and old_thread is not threading.current_thread():
            try:
                old_thread.join(timeout=2)
            except Exception:
                pass

        with self.lock:
            self.process = None
            self.thread = None
            self.running = False
            self.restarting = False
            # start() sẽ hạ cờ này sau khi process mới mở thành công.

        self.start()

        if self.running:
            log(self.name, "🔄 已自动重新加载最新保存文件（Telegram静默）")
            return True

        # Start mới không thành công: không báo Telegram ngay; chuyển về cơ chế
        # auto-recovery bình thường để chỉ cảnh báo nếu thất bại kéo dài.
        log(self.name, "Hot reload start failed, chuyển sang auto recovery")
        with self.lock:
            self.intentional_reload = False
        self.restart()
        return False

    # ========================================================

    def restart(self):

        with self.lock:

            # reader() và watchdog() có thể cùng phát hiện 1 lần process chết.
            # restarting ngăn việc tạo 2 process mới cùng lúc.
            if self.running or self.restarting:
                return

            self.restarting = True
            self.restart_count += 1
            self.consecutive_restarts += 1

            current_restart = self.restart_count
            current_streak = self.consecutive_restarts
            log(self.name, f"Restart #{current_restart} (streak={current_streak})")

            # Không spam Telegram khi lỗi mạng/process chỉ chập chờn ngắn.
            # Chỉ cảnh báo khi đã restart liên tiếp nhiều lần.
            if (
                current_streak >= WORKER_RESTART_ALERT_AFTER
                and not self.alerted_restart_storm
            ):
                self.alerted_restart_storm = True
                telegram(
                    f"⚠️ {self.name}\n"
                    f"Đã tự khởi động lại {current_streak} lần liên tiếp.\n"
                    f"Hệ thống vẫn tiếp tục tự phục hồi."
                )

        delay = min(
            WORKER_RESTART_BASE_SECONDS * (2 ** min(current_streak - 1, 4)),
            WORKER_RESTART_MAX_SECONDS,
        )
        delay += random.uniform(0, 1.0)
        log(self.name, f"Auto restart in {delay:.1f}s")
        time.sleep(delay)

        self.start()

    # ========================================================

    def reader(self):

        try:

            while True:

                if self.process is None:
                    break

                line = self.process.stdout.readline()

                if line == "" and self.process.poll() is not None:
                    break

                if not line:
                    continue

                line = line.rstrip()

                log(self.name, line)

                self.handle_line(line)

        except Exception as e:

            # Reader lỗi cục bộ cũng ưu tiên tự phục hồi trước, tránh spam Telegram.
            log(self.name, f"Reader error: {type(e).__name__}: {e}")

        finally:

            # Nếu process đã chạy ổn đủ lâu, lỗi sau đó được tính là sự cố mới.
            try:
                if self.last_started_at and (time.time() - self.last_started_at) >= WORKER_STABLE_RESET_SECONDS:
                    self.consecutive_restarts = 0
                    self.alerted_restart_storm = False
            except Exception:
                pass

            self.running = False

            code = -1

            try:
                code = self.process.poll()
            except:
                pass

            log(self.name, f"Exit Code = {code}")

            # Hot reload chủ động đã terminate process cũ; không được coi đó là crash.
            if self.intentional_reload:
                log(self.name, "🔄 Old process stopped for hot reload")
                return

            if not self.finished:
                self.restart()

    # ========================================================
    # HANDLE OUTPUT
    # ========================================================

    def handle_line(self, line):

        # QUANJU
        if self.type == "全局报表":
            if line == "✅ 全站汇总更新完成":

                self.finished = True
                next_title = self.process.stdout.readline().strip()
                next_time = self.process.stdout.readline().strip()
                wait_time = self.process.stdout.readline().strip()

                telegram(
                    "✅ 全站汇总更新完成\n\n"
                    f"📊 数据表: <a href='{SHEET_URL}'>打开</a>\n\n"
                    f"{next_title}\n"
                    f"{next_time}\n"
                    f"{wait_time}")
                return


        # DASHBOARD
        if self.type == "推广汇总":
            if line == "✅ 推广汇总更新完成":

                self.finished = True
                next_title = self.process.stdout.readline().strip()
                next_time = self.process.stdout.readline().strip()
                wait_time = self.process.stdout.readline().strip()

                telegram(
                    "✅ 推广汇总更新完成\n\n"
                    f"🌐 数据网页: <a href='{WEB_URL}'>打开</a>\n\n"
                    f"{next_title}\n"
                    f"{next_time}\n"
                    f"{wait_time}")
                return

# ============================================================
# DYNAMIC TASK CONFIG RELOAD
# ============================================================

def _eval_task_ast(node):
    """Đọc an toàn biểu thức TASKS từ source, không exec lại RUN ALL."""
    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.List):
        return [_eval_task_ast(x) for x in node.elts]

    if isinstance(node, ast.Tuple):
        return tuple(_eval_task_ast(x) for x in node.elts)

    if isinstance(node, ast.Dict):
        return {
            _eval_task_ast(k): _eval_task_ast(v)
            for k, v in zip(node.keys, node.values)
        }

    # Hỗ trợ đúng kiểu đang dùng: BASE_DIR / "folder" / "file.py"
    if isinstance(node, ast.Name) and node.id == "BASE_DIR":
        return BASE_DIR

    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = _eval_task_ast(node.left)
        right = _eval_task_ast(node.right)
        if isinstance(left, Path) and isinstance(right, (str, Path)):
            return left / right

    raise ValueError(f"Unsupported TASKS expression: {ast.dump(node, include_attributes=False)}")


def load_tasks_from_running_source():
    """Đọc biến TASKS mới nhất trực tiếp từ file RUN ALL đang nằm trên ổ đĩa."""
    source_path = Path(__file__).resolve()
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))

    task_node = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "TASKS":
                    task_node = node.value
                    break
        if task_node is not None:
            break

    if task_node is None:
        raise ValueError("Không tìm thấy TASKS trong file RUN ALL")

    parsed = _eval_task_ast(task_node)
    if not isinstance(parsed, list):
        raise ValueError("TASKS phải là list")

    result = []
    for index, cfg in enumerate(parsed, start=1):
        if not isinstance(cfg, dict):
            raise ValueError(f"TASKS[{index}] không phải dict")

        name = str(cfg.get("name", "")).strip()
        task_type = str(cfg.get("type", name)).strip()
        file_value = cfg.get("file")

        if not name or not file_value:
            raise ValueError(f"TASKS[{index}] thiếu name/file")

        file_path = Path(file_value)
        if not file_path.is_absolute():
            file_path = BASE_DIR / file_path

        result.append({
            "name": name,
            "type": task_type,
            "file": file_path.resolve(),
        })

    return result


def _worker_task_key(worker):
    try:
        file_key = str(worker.file.resolve())
    except Exception:
        file_key = str(worker.file)
    return (worker.name, worker.type, file_key)


def _cfg_task_key(cfg):
    try:
        file_key = str(Path(cfg["file"]).resolve())
    except Exception:
        file_key = str(cfg.get("file", ""))
    return (str(cfg.get("name", "")), str(cfg.get("type", "")), file_key)


def add_dynamic_tasks(new_tasks):
    """
    Chỉ thêm task chưa tồn tại. Task đang chạy không bị restart/đụng tới.
    Việc thêm task là thay đổi chủ động nên không gửi Telegram.
    """
    added = 0

    with WORKERS_LOCK:
        existing = {_worker_task_key(w) for w in workers}

        for cfg in new_tasks:
            key = _cfg_task_key(cfg)
            if key in existing:
                continue

            w = Worker(cfg)
            workers.append(w)
            existing.add(key)

            log(w.name, "➕ 检测到新的TASK，正在自动启动（Telegram静默）")
            w.start()

            if w.running:
                log(w.name, "✅ 新TASK已自动启动")
            else:
                log(w.name, "⚠️ 新TASK暂未启动成功，交给自动恢复机制")

            added += 1
            time.sleep(0.5)

    return added


def dynamic_task_watcher():
    """
    Theo dõi chính file RUN ALL. Khi Save, debounce rồi đọc lại TASKS.
    Task mới được start ngay; task cũ giữ nguyên trạng thái/process.
    """
    source_path = Path(__file__).resolve()

    try:
        seen_mtime = source_path.stat().st_mtime_ns
    except Exception:
        seen_mtime = 0

    pending_mtime = 0
    changed_at = 0.0

    while True:
        try:
            current_mtime = source_path.stat().st_mtime_ns
            now = time.time()

            if current_mtime != seen_mtime and current_mtime != pending_mtime:
                pending_mtime = current_mtime
                changed_at = now
                print("[RUN ALL] 🔄 检测到RUN ALL配置已保存，等待稳定后读取TASKS...")

            elif pending_mtime and current_mtime != pending_mtime:
                pending_mtime = current_mtime
                changed_at = now

            elif pending_mtime and (now - changed_at) >= DYNAMIC_TASK_DEBOUNCE_SECONDS:
                # Trước hết nhận mtime này để tránh loop lặp nếu source có lỗi cú pháp tạm thời.
                seen_mtime = pending_mtime
                pending_mtime = 0
                changed_at = 0.0

                try:
                    newest_tasks = load_tasks_from_running_source()
                    added = add_dynamic_tasks(newest_tasks)
                    if added:
                        print(f"[RUN ALL] ✅ 已动态新增并启动 {added} 个TASK")
                    else:
                        print("[RUN ALL] ✅ TASKS已重新读取，无新增TASK")
                except SyntaxError as e:
                    # Save giữa chừng/cú pháp chưa hoàn chỉnh: chỉ terminal, không Telegram.
                    print(f"[RUN ALL] ⚠️ TASKS暂时无法读取（语法未完成）: {e}")
                except Exception as e:
                    print(f"[RUN ALL] ⚠️ 动态TASK读取失败: {type(e).__name__}: {e}")

        except Exception as e:
            print(f"[RUN ALL] Dynamic task watcher warning: {type(e).__name__}: {e}")

        time.sleep(DYNAMIC_TASK_CHECK_SECONDS)


# ============================================================
# START ALL
# ============================================================

def start_all():

    banner()

    # Startup Telegram message disabled by user request.
    # startup_message()

    with WORKERS_LOCK:
        workers.clear()

    print("🚀 Starting all tasks...\n")

    for cfg in TASKS:

        w = Worker(cfg)

        with WORKERS_LOCK:
            workers.append(w)

        w.start()

        # tránh mở 4 process cùng lúc
        time.sleep(1)

    print("\n✅ All workers started.\n")

# ============================================================
# WATCHDOG
# ============================================================

def watchdog():

    while True:

        with WORKERS_LOCK:
            snapshot = list(workers)

        for w in snapshot:

            try:

                if w.intentional_reload:
                    continue

                if w.process is None:
                    continue

                code = w.process.poll()

                # Process còn chạy
                if code is None:
                    continue

                # Nếu worker đang restart thì bỏ qua
                if w.running:
                    continue

                log(
                    w.name,
                    f"Process Exit ({code})"
                )

                # Process chết chưa chắc là lỗi nghiêm trọng (có thể mạng chập chờn).
                # Ghi log và để cơ chế restart tự phục hồi; restart() sẽ chỉ báo
                # Telegram khi thất bại liên tiếp vượt ngưỡng.
                log(w.name, f"Auto recovery after exit code {code}")

                time.sleep(3)

                w.restart()

            except Exception as e:

                telegram(
                    f"❌ WATCHDOG\n"
                    f"{w.name}\n\n"
                    f"{e}"
                )

        time.sleep(5)

# ============================================================
# AUTO HOT RELOAD WATCHER
# ============================================================

def hot_reload_watcher():
    """
    Theo dõi mtime của đúng 7 file chính trong TASKS.
    Save -> debounce -> reload đúng worker đó. Không gửi Telegram.
    """
    state = {}

    for w in workers:
        mtime = w._get_file_mtime_ns()
        state[id(w)] = {
            "seen": mtime,
            "pending": 0,
            "changed_at": 0.0,
        }

    while True:
        now = time.time()

        for w in list(workers):
            try:
                key = id(w)
                s = state.setdefault(key, {
                    "seen": w._get_file_mtime_ns(),
                    "pending": 0,
                    "changed_at": 0.0,
                })

                current = w._get_file_mtime_ns()
                if current <= 0:
                    continue

                # Phát hiện một lần Save mới. Nếu editor Save tiếp, debounce bắt đầu lại.
                if current != s["seen"] and current != s["pending"]:
                    s["pending"] = current
                    s["changed_at"] = now
                    log(w.name, "🔄 发现文件保存，等待稳定后自动重载...")
                    continue

                if not s["pending"]:
                    continue

                # File lại đổi trong lúc debounce -> cập nhật mốc mới, chưa reload.
                if current != s["pending"]:
                    s["pending"] = current
                    s["changed_at"] = now
                    continue

                if (now - s["changed_at"]) < HOT_RELOAD_DEBOUNCE_SECONDS:
                    continue

                # Đánh dấu seen trước khi reload để chính thao tác reload không lặp lại.
                s["seen"] = current
                s["pending"] = 0
                s["changed_at"] = 0.0

                w.hot_reload()

            except Exception as e:
                # Watcher chỉ ghi terminal/log, tuyệt đối không spam Telegram.
                log(w.name, f"Hot reload watcher warning: {type(e).__name__}: {e}")

        time.sleep(HOT_RELOAD_CHECK_SECONDS)


# ============================================================
# START BACKGROUND THREADS
# ============================================================

def start_background():

    threading.Thread(

        target=watchdog,

        daemon=True,

        name="WATCHDOG"

    ).start()
    
    threading.Thread(

        target=hot_reload_watcher,

        daemon=True,

        name="HOT_RELOAD"

    ).start()

    threading.Thread(

        target=dynamic_task_watcher,

        daemon=True,

        name="DYNAMIC_TASKS"

    ).start()
    
# ============================================================
# MAIN
# ============================================================

def main():

    start_all()

    start_background()

    # Startup success Telegram message disabled by user request.
    # telegram("✅全量任务启动成功")

    print("\n🚀 System Running...\n")

    try:

        while True:
            time.sleep(60)

    except KeyboardInterrupt:

        print("\n")
        print("=" * 60)
        print("Stopping All Workers...")
        print("=" * 60)

        telegram("🛑 XIAORUAN RUN ALL Stopped")

        for w in workers:
            try:
                w.stop()
            except:
                pass

        time.sleep(2)

        print("Bye.")

# ============================================================
# ENTRY
# ============================================================
# ============================================================
# AUTO CLEAN BUFFER
# ============================================================

def clear_buffer():

    while True:

        try:

            # Worker đọc stdout trực tiếp, hiện không có thuộc tính buffer.
            for w in workers:
                pass

        except:
            pass

        time.sleep(60)

# ============================================================
# AUTO LOG
# ============================================================

def save_log(text):

    try:

        log_file = BASE_DIR / "run_all.log"

        with open(

            log_file,

            "a",

            encoding="utf-8"

        ) as f:

            f.write(

                time.strftime("%Y-%m-%d %H:%M:%S ")

                + text

                + "\n"

            )

    except:
        pass

# ============================================================
# PATCH LOG FUNCTION
# ============================================================

_old_log = log

def log(name, text):

    msg = f"[{name}] {text}"

    with lock:

        print(msg)

    save_log(msg)

# ============================================================
# UPTIME
# ============================================================

START_TIME = time.time()

def format_seconds(sec):

    sec = int(sec)

    h = sec // 3600

    m = (sec % 3600) // 60

    s = sec % 60

    return f"{h:02d}:{m:02d}:{s:02d}"

def uptime():

    while True:

        try:

            run = format_seconds(

                time.time() - START_TIME

            )

            print()

            print("=" * 70)

            print(f"RUN TIME : {run}")

            print("=" * 70)

        except:

            pass

        time.sleep(600)

# ============================================================
# EXTRA THREADS
# ============================================================

threading.Thread(

    target=clear_buffer,

    daemon=True,

    name="BUFFER"

).start()

threading.Thread(

    target=uptime,

    daemon=True,

    name="UPTIME"

).start()

print()

print("=" * 70)
print("SYSTEM READY")
print("=" * 70)

if __name__ == "__main__":

    try:

        if not acquire_single_instance_lock():
            sys.exit(1)

        main()

    except Exception as e:

        print(e)

        telegram(

            "❌ RUN ALL CRASH\n\n"

            + str(e)

        )

        raise