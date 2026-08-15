import warnings
warnings.filterwarnings("ignore")

import json
import os
import re
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FILES = [
    "main.py",
    "nn22.py",
    "23a.py",
    "23e.py",
]

SITE_TO_JSON = {
    "73J": "data.json",
    "NN22": "nn22.json",
    "23A": "23a.json",
    "23E": "23e.json",
}

SITE_TO_SCRIPT = {
    "73J": "main.py",
    "NN22": "nn22.py",
    "23A": "23a.py",
    "23E": "23e.py",
}

API_HOST = "127.0.0.1"
API_PORT = int(os.environ.get("RUN_API_PORT", "8765"))

# =====================================================================
# CLOUDFLARE QUICK TUNNEL TỰ ĐỘNG
# - Chỉ cần chạy run_forever.py.
# - File này tự mở cloudflared, tự lấy URL *.trycloudflare.com.
# - URL hiện tại được ghi vào tunnel.json và tự push lên GitHub.
# - HTML đọc tunnel.json nên không cần sửa URL mỗi lần Mac/restart Tunnel.
# =====================================================================
TUNNEL_INFO_NAME = "tunnel.json"
TUNNEL_INFO_PATH = os.path.join(BASE_DIR, TUNNEL_INFO_NAME)
TUNNEL_URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com", re.I)
TUNNEL_STOP_EVENT = threading.Event()
TUNNEL_READY_EVENT = threading.Event()
TUNNEL_PUBLISH_DONE_EVENT = threading.Event()
TUNNEL_PROCESS_LOCK = threading.Lock()
TUNNEL_PROCESS = None
CURRENT_TUNNEL_URL = ""

# Khóa các lệnh git của chính run_forever.py để tunnel.json và JSON dữ liệu
# không tự giẫm nhau. Các script con vẫn được giữ nguyên như trước.
GIT_LOCK = threading.Lock()

# Có thể ghi đè bằng biến môi trường RUN_ALLOWED_ORIGINS, phân cách bằng dấu phẩy.
DEFAULT_ALLOWED_ORIGINS = {
    "https://xiaoruan.vip",
    "https://www.xiaoruan.vip",
    "https://xiafaxiaoliansocute-stack.github.io",
    "http://localhost",
    "http://127.0.0.1",
    "null",  # Cho phép test index.html mở trực tiếp bằng file:// trên chính máy.
}

_raw_origins = os.environ.get("RUN_ALLOWED_ORIGINS", "").strip()
if _raw_origins:
    ALLOWED_ORIGINS = {
        item.strip().rstrip("/")
        for item in _raw_origins.split(",")
        if item.strip()
    }
else:
    ALLOWED_ORIGINS = DEFAULT_ALLOWED_ORIGINS



# =====================================================================
# TRẠNG THÁI CHẠY - tránh bấm nhiều lần chạy chồng bot
# =====================================================================
RUN_CONDITION = threading.Condition()
IS_RUNNING = False
RUN_NUMBER = 0
LAST_RESULT = None


def run_script(filename):
    """Chạy 1 bot Python và trả kết quả."""
    path = os.path.join(BASE_DIR, filename)

    if not os.path.exists(path):
        return filename, False, f"Không tìm thấy file: {path}"

    try:
        start = datetime.now()
        print(
            f"🚀 {filename} 开始: {start.strftime('%H:%M:%S')}",
            flush=True,
        )

        subprocess.run(
            ["python3", path],
            cwd=BASE_DIR,
            check=True,
        )

        elapsed = (datetime.now() - start).total_seconds()
        return filename, True, elapsed

    except subprocess.CalledProcessError as e:
        return filename, False, f"exit code {e.returncode}"
    except Exception as e:
        return filename, False, str(e)


def run_all(trigger="hourly"):
    """
    Chạy 4 bot.

    Nếu đang có một lượt chạy (ví dụ đúng lúc chạy hàng giờ), yêu cầu từ HTML
    sẽ chờ lượt hiện tại xong rồi dùng luôn kết quả đó, không chạy chồng thêm lần nữa.
    """
    global IS_RUNNING, RUN_NUMBER, LAST_RESULT

    with RUN_CONDITION:
        if IS_RUNNING:
            waiting_for = RUN_NUMBER
            print(
                f"⏳ Có lượt #{waiting_for} đang chạy, yêu cầu {trigger} chờ kết quả...",
                flush=True,
            )

            # Chờ tối đa 30 phút. Các bot hiện tại có cơ chế retry nên không để
            # request web treo vô hạn nếu có sự cố kéo dài.
            deadline = time.time() + 30 * 60
            while IS_RUNNING and RUN_NUMBER == waiting_for:
                remaining = deadline - time.time()
                if remaining <= 0:
                    return {
                        "success": False,
                        "error": "Timeout: bot vẫn đang chạy quá 30 phút",
                        "run_number": waiting_for,
                    }
                RUN_CONDITION.wait(timeout=min(5, remaining))

            if LAST_RESULT is not None:
                result = dict(LAST_RESULT)
                result["reused_running_job"] = True
                return result

        IS_RUNNING = True
        RUN_NUMBER += 1
        current_run = RUN_NUMBER

    started_at = datetime.now()
    details = {}
    success_count = 0

    try:
        print("=" * 60, flush=True)
        print(
            f"🚀 开始更新 #{current_run} [{trigger}]: "
            f"{started_at.strftime('%Y-%m-%d %H:%M:%S')}",
            flush=True,
        )

        # Giữ cách chạy hiện tại: 4 web chạy đồng thời.
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(run_script, filename)
                for filename in FILES
            ]

            for future in as_completed(futures):
                filename, success, info = future.result()
                details[filename] = {
                    "success": success,
                    "info": info,
                }

                if success:
                    success_count += 1
                    print(
                        f"✅ {filename} 完成 | {info:.1f} 秒",
                        flush=True,
                    )
                else:
                    print(
                        f"❌ {filename} 错误: {info}",
                        flush=True,
                    )

        github_sync = sync_json_to_github()

        finished_at = datetime.now()
        result = {
            "success": success_count == len(FILES),
            "success_count": success_count,
            "total": len(FILES),
            "run_number": current_run,
            "trigger": trigger,
            "started_at": started_at.strftime("%Y-%m-%d %H:%M:%S"),
            "finished_at": finished_at.strftime("%Y-%m-%d %H:%M:%S"),
            "elapsed_seconds": round((finished_at - started_at).total_seconds(), 1),
            "details": details,
            "github_sync": github_sync,
        }

        print(
            f"📊 更新结果: {success_count}/{len(FILES)}",
            flush=True,
        )
        return result

    except Exception as e:
        result = {
            "success": False,
            "error": str(e),
            "success_count": success_count,
            "total": len(FILES),
            "run_number": current_run,
            "trigger": trigger,
            "details": details,
        }
        print(f"❌ Launcher error: {e}", flush=True)
        return result

    finally:
        with RUN_CONDITION:
            LAST_RESULT = locals().get("result", {
                "success": False,
                "error": "Unknown launcher error",
                "run_number": current_run,
            })
            IS_RUNNING = False
            RUN_CONDITION.notify_all()



def _git_sync_files(file_names, commit_message, success_message):
    """Commit/push một nhóm file với retry, tránh tranh chấp git trong process cha."""
    existing = [
        name for name in file_names
        if os.path.exists(os.path.join(BASE_DIR, name))
    ]

    if not existing:
        return {"success": False, "error": "Không có file để sync"}

    last_error = "unknown git error"

    with GIT_LOCK:
        for attempt in range(1, 6):
            try:
                add = subprocess.run(
                    # -f để tunnel.json vẫn được sync ngay cả khi .gitignore đang bỏ qua file này.
                    ["git", "add", "-f", "--", *existing],
                    cwd=BASE_DIR,
                    capture_output=True,
                    text=True,
                )
                if add.returncode != 0:
                    raise RuntimeError((add.stderr or add.stdout or "git add failed").strip())

                diff = subprocess.run(
                    ["git", "diff", "--cached", "--quiet", "--", *existing],
                    cwd=BASE_DIR,
                )

                committed = False
                if diff.returncode == 1:
                    commit = subprocess.run(
                        ["git", "commit", "-m", commit_message, "--only", "--", *existing],
                        cwd=BASE_DIR,
                        capture_output=True,
                        text=True,
                    )
                    if commit.returncode != 0:
                        raise RuntimeError(
                            (commit.stderr or commit.stdout or "git commit failed").strip()
                        )
                    committed = True
                elif diff.returncode not in (0, 1):
                    raise RuntimeError("git diff --cached failed")

                push = subprocess.run(
                    ["git", "push", "origin", "main"],
                    cwd=BASE_DIR,
                    capture_output=True,
                    text=True,
                )
                if push.returncode != 0:
                    raise RuntimeError(
                        (push.stderr or push.stdout or "git push failed").strip()
                    )

                print(success_message, flush=True)
                return {"success": True, "committed": committed}

            except Exception as e:
                last_error = str(e)
                if attempt < 5:
                    print(
                        f"⚠️ Git sync lần {attempt}/5 lỗi, thử lại: {last_error}",
                        flush=True,
                    )
                    time.sleep(min(2 * attempt, 8))

    return {"success": False, "error": last_error}


def sync_json_to_github():
    """
    Sau khi 4 bot chạy xong, đồng bộ lại JSON dữ liệu.
    Nếu tunnel.json đang có thay đổi chưa push được trước đó thì đồng bộ luôn.
    """
    files_to_sync = ["data.json", "nn22.json", "23a.json", "23e.json"]
    if os.path.exists(TUNNEL_INFO_PATH):
        files_to_sync.append(TUNNEL_INFO_NAME)

    result = _git_sync_files(
        files_to_sync,
        "auto update all data",
        "✅ JSON/tunnel 已同步到 GitHub",
    )
    if not result.get("success"):
        print(f"❌ GitHub JSON sync error: {result.get('error')}", flush=True)
    return result


def _find_cloudflared():
    """Tìm cloudflared cả khi PATH của app/GUI trên macOS không đầy đủ."""
    candidates = [
        shutil.which("cloudflared"),
        "/opt/homebrew/bin/cloudflared",   # Apple Silicon Homebrew
        "/usr/local/bin/cloudflared",      # Intel Homebrew
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def _write_tunnel_info(public_url):
    """Ghi tunnel.json theo kiểu atomic rồi push lên GitHub."""
    payload = {
        "success": True,
        "api_base": public_url.rstrip("/"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "cloudflare-quick-tunnel",
        "version": 1,
    }

    temp_path = TUNNEL_INFO_PATH + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    os.replace(temp_path, TUNNEL_INFO_PATH)

    print(f"🌍 Public API: {public_url}", flush=True)
    print(f"📝 已更新 {TUNNEL_INFO_NAME}", flush=True)

    result = _git_sync_files(
        [TUNNEL_INFO_NAME],
        "auto update tunnel url",
        "✅ Tunnel URL 已同步到 GitHub",
    )
    if not result.get("success"):
        print(
            f"⚠️ tunnel.json 暂时无法 push: {result.get('error')}. "
            "Sau lượt bot tiếp theo hệ thống sẽ thử sync lại.",
            flush=True,
        )

    TUNNEL_PUBLISH_DONE_EVENT.set()
    return result


def tunnel_manager_loop():
    """
    Giữ Quick Tunnel chạy liên tục.
    Nếu cloudflared bị rớt, tự khởi động tunnel mới và cập nhật tunnel.json.
    """
    global TUNNEL_PROCESS, CURRENT_TUNNEL_URL

    while not TUNNEL_STOP_EVENT.is_set():
        cloudflared = _find_cloudflared()
        if not cloudflared:
            print(
                "❌ Không tìm thấy cloudflared. Cài bằng: brew install cloudflared",
                flush=True,
            )
            TUNNEL_PUBLISH_DONE_EVENT.set()
            TUNNEL_STOP_EVENT.wait(60)
            continue

        cmd = [
            cloudflared,
            "tunnel",
            "--url",
            f"http://{API_HOST}:{API_PORT}",
        ]

        print("☁️ 正在自动启动 Cloudflare Quick Tunnel...", flush=True)

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=BASE_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            with TUNNEL_PROCESS_LOCK:
                TUNNEL_PROCESS = proc

            found_url = False

            if proc.stdout is not None:
                for raw_line in proc.stdout:
                    if TUNNEL_STOP_EVENT.is_set():
                        break

                    line = raw_line.rstrip()
                    if line:
                        print(f"[Tunnel] {line}", flush=True)

                    match = TUNNEL_URL_RE.search(line)
                    if match:
                        public_url = match.group(0).rstrip("/")
                        if public_url != CURRENT_TUNNEL_URL:
                            CURRENT_TUNNEL_URL = public_url
                            found_url = True
                            TUNNEL_READY_EVENT.set()
                            TUNNEL_PUBLISH_DONE_EVENT.clear()
                            _write_tunnel_info(public_url)

            if TUNNEL_STOP_EVENT.is_set():
                break

            return_code = proc.wait()
            print(
                f"⚠️ Cloudflare Tunnel 已断开 (exit={return_code}), 5秒后自动重连...",
                flush=True,
            )

            if not found_url:
                TUNNEL_PUBLISH_DONE_EVENT.set()

        except Exception as e:
            print(f"❌ Cloudflare Tunnel error: {e}", flush=True)
            TUNNEL_PUBLISH_DONE_EVENT.set()

        finally:
            with TUNNEL_PROCESS_LOCK:
                if TUNNEL_PROCESS is not None and TUNNEL_PROCESS.poll() is not None:
                    TUNNEL_PROCESS = None

        TUNNEL_STOP_EVENT.wait(5)


def stop_tunnel_manager():
    """Dừng cloudflared con khi run_forever.py thoát bình thường."""
    global TUNNEL_PROCESS
    TUNNEL_STOP_EVENT.set()

    with TUNNEL_PROCESS_LOCK:
        proc = TUNNEL_PROCESS

    if proc and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    with TUNNEL_PROCESS_LOCK:
        TUNNEL_PROCESS = None


def read_json_file(filename):
    path = os.path.join(BASE_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# =====================================================================
# HTTP API CHO index.html
# =====================================================================
class RunApiHandler(BaseHTTPRequestHandler):
    server_version = "XiaoruanRunAPI/1.0"

    def log_message(self, fmt, *args):
        # Không in log request /health, giữ nguyên toàn bộ logic chạy cũ.
        if len(args) > 0 and "/health" in str(args[0]):
            return

        print(
            f"🌐 {self.address_string()} - {fmt % args}",
            flush=True,
        )

    def _origin_allowed(self):
        origin = (self.headers.get("Origin") or "").rstrip("/")
        if not origin:
            return True, ""
        return origin in ALLOWED_ORIGINS, origin

    def _send_cors(self, origin):
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type",
        )
        self.send_header("Access-Control-Max-Age", "600")

    def _json_response(self, status, payload):
        allowed, origin = self._origin_allowed()
        if not allowed:
            status = 403
            payload = {
                "success": False,
                "error": "Origin không được phép",
            }

        body = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        try:
            self.send_response(status)
            self._send_cors(origin if allowed else "")
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # Trình duyệt/client đã đóng hoặc hủy request trước khi server trả xong.
            # Đây không phải lỗi chạy bot, nên bỏ qua để tránh in traceback dài ra terminal.
            return

    def do_OPTIONS(self):
        allowed, origin = self._origin_allowed()
        if not allowed:
            self.send_response(403)
            self.end_headers()
            return

        self.send_response(204)
        self._send_cors(origin)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        # HTML giữ 1 kết nối chờ ở đây. Chỉ trả về khi một lượt run đã KẾT THÚC.
        # Nhờ vậy không cần gọi /health liên tục mỗi vài giây.
        if path == "/wait-finish":
            query = parse_qs(parsed.query)

            try:
                after_run = max(0, int((query.get("after") or ["0"])[0]))
            except Exception:
                after_run = 0

            # 70 phút: đủ để chờ qua lượt chạy tự động kế tiếp theo giờ.
            deadline = time.time() + 70 * 60
            timed_out = False
            reset_counter = False
            last_result = None
            last_number = 0

            with RUN_CONDITION:
                while True:
                    running = IS_RUNNING
                    current_number = int(RUN_NUMBER or 0)
                    last_result = dict(LAST_RESULT) if LAST_RESULT else None
                    last_number = int((last_result or {}).get("run_number", 0) or 0)

                    # Nếu đang chạy thì chờ đúng lượt hiện tại kết thúc, không đọc file giữa chừng.
                    if not running:
                        # run_forever.py vừa được restart => RUN_NUMBER quay về nhỏ hơn
                        # số mà HTML đang nhớ. Báo reset để HTML bắt đầu theo dõi lại.
                        if after_run > current_number and last_number > 0:
                            reset_counter = True
                            break

                        # Có một lượt mới đã hoàn thành.
                        if last_number > after_run:
                            break

                    remaining = deadline - time.time()
                    if remaining <= 0:
                        timed_out = True
                        break

                    # Đây chỉ là wait nội bộ trong Python, KHÔNG tạo request /health.
                    RUN_CONDITION.wait(timeout=min(60, remaining))

            if timed_out:
                self._json_response(
                    200,
                    {
                        "success": True,
                        "timeout": True,
                        "run_number": last_number,
                    },
                )
                return

            self._json_response(
                200,
                {
                    "success": True,
                    "finished": True,
                    "reset": reset_counter,
                    "run_number": last_number,
                    "finished_at": (last_result or {}).get("finished_at"),
                },
            )
            return

        if path == "/health":
            with RUN_CONDITION:
                running = IS_RUNNING
                run_number = RUN_NUMBER
                last_result = dict(LAST_RESULT) if LAST_RESULT else None

            self._json_response(
                200,
                {
                    "success": True,
                    "service": "xiaoruan-run-api",
                    "running": running,
                    "run_number": run_number,
                    "last_finished_run_number": (last_result or {}).get("run_number", 0),
                    "last_finished_at": (last_result or {}).get("finished_at"),
                    "tunnel_url": CURRENT_TUNNEL_URL or None,
                    "tunnel_ready": bool(CURRENT_TUNNEL_URL),
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
            )
            return

        # Trạng thái của một lượt chạy được HTML công khai kiểm tra ngắn hạn.
        # Không giữ kết nối lâu, phù hợp khi API đi qua HTTPS tunnel/proxy.
        if path == "/run-status":
            query = parse_qs(parsed.query)
            site = str((query.get("site") or ["73J"])[0]).upper()

            try:
                target_run = max(0, int((query.get("run") or ["0"])[0]))
            except Exception:
                target_run = 0

            if site not in SITE_TO_JSON:
                self._json_response(
                    400,
                    {
                        "success": False,
                        "error": f"Không hỗ trợ site: {site}",
                    },
                )
                return

            with RUN_CONDITION:
                running = bool(IS_RUNNING)
                current_number = int(RUN_NUMBER or 0)
                last_result = dict(LAST_RESULT) if LAST_RESULT else None

            last_number = int((last_result or {}).get("run_number", 0) or 0)

            if target_run <= 0:
                target_run = current_number or last_number

            if target_run > 0 and last_number >= target_run:
                current_script = SITE_TO_SCRIPT[site]
                current_detail = (last_result or {}).get("details", {}).get(current_script, {})
                site_success = bool(current_detail.get("success"))

                self._json_response(
                    200,
                    {
                        "success": True,
                        "finished": True,
                        "running": running,
                        "run_number": target_run,
                        "last_finished_run_number": last_number,
                        "site_success": site_success,
                        "error": None if site_success else (
                            f"{current_script} chạy thất bại: "
                            f"{current_detail.get('info', (last_result or {}).get('error', 'unknown error'))}"
                        ),
                        "finished_at": (last_result or {}).get("finished_at"),
                    },
                )
                return

            self._json_response(
                200,
                {
                    "success": True,
                    "finished": False,
                    "running": running,
                    "run_number": target_run,
                    "current_run_number": current_number,
                    "last_finished_run_number": last_number,
                },
            )
            return

        # HTML dùng endpoint này để lấy JSON TRỰC TIẾP từ Mac sau khi
        # lượt chạy xong. Không phải chờ GitHub Pages/CDN.
        if path == "/latest":
            query = parse_qs(parsed.query)
            site = str((query.get("site") or ["73J"])[0]).upper()

            if site not in SITE_TO_JSON:
                self._json_response(
                    400,
                    {
                        "success": False,
                        "error": f"Không hỗ trợ site: {site}",
                    },
                )
                return

            try:
                current_data = read_json_file(SITE_TO_JSON[site])
                master_data = read_json_file("data.json")
                master_update_time = (
                    master_data.get("update_time_brazil")
                    or master_data.get("update_time")
                    or "--"
                )

                with RUN_CONDITION:
                    running = IS_RUNNING
                    run_number = RUN_NUMBER

                self._json_response(
                    200,
                    {
                        "success": True,
                        "site": site,
                        "data": current_data,
                        "master_update_time": master_update_time,
                        "running": running,
                        "run_number": run_number,
                    },
                )
            except Exception as e:
                self._json_response(
                    500,
                    {
                        "success": False,
                        "error": f"Không đọc được JSON local: {e}",
                    },
                )
            return

        self._json_response(404, {"success": False, "error": "Not found"})

    def do_POST(self):
        if self.path.rstrip("/") != "/run":
            self._json_response(404, {"success": False, "error": "Not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0") or 0)
            if content_length > 16 * 1024:
                self._json_response(
                    413,
                    {"success": False, "error": "Request too large"},
                )
                return

            raw = self.rfile.read(content_length) if content_length else b"{}"
            body = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            self._json_response(
                400,
                {"success": False, "error": "JSON request không hợp lệ"},
            )
            return

        site = str(body.get("site", "73J")).upper()
        if site not in SITE_TO_JSON:
            self._json_response(
                400,
                {
                    "success": False,
                    "error": f"Không hỗ trợ site: {site}",
                },
            )
            return

        # API công khai: nút HTML gọi trực tiếp, không dùng token.
        # Nếu đang có lượt chạy, người bấm dùng luôn lượt đó.
        # Nếu chưa chạy, khởi động ở background để request HTTP trả ngay.
        with RUN_CONDITION:
            already_running = bool(IS_RUNNING)
            current_number = int(RUN_NUMBER or 0)
            target_run = current_number if already_running else current_number + 1

        if not already_running:
            worker = threading.Thread(
                target=run_all,
                kwargs={"trigger": f"html:{site}"},
                name=f"html-run-{target_run}",
                daemon=True,
            )
            worker.start()

        self._json_response(
            202,
            {
                "success": True,
                "accepted": True,
                "site": site,
                "run_number": target_run,
                "reused_running_job": already_running,
            },
        )


# =====================================================================
# LỊCH TỰ ĐỘNG MỖI GIỜ - GIỮ HÀNH VI CŨ
# =====================================================================
def scheduler_loop():
    # Chạy ngay một lượt khi mở run_forever.py giống phiên bản cũ.
    while True:
        run_all(trigger="hourly")

        now = datetime.now()
        next_hour = (
            now + timedelta(hours=1)
        ).replace(
            minute=0,
            second=0,
            microsecond=0,
        )

        sleep_seconds = max(
            1,
            (next_hour - now).total_seconds(),
        )

        # GIỮ ĐÚNG FORMAT mà GUI/BOT hiện tại đang đọc.
        print("✅ 推广汇总更新完成", flush=True)
        print("⏳ 下次运行:", flush=True)
        print(
            next_hour.strftime("%Y-%m-%d %H:%M:%S"),
            flush=True,
        )
        print(
            f"等待: {round(sleep_seconds / 3600, 2)} 小时",
            flush=True,
        )

        time.sleep(sleep_seconds)


def main():
    print("=" * 60, flush=True)
    print("Xiaoruan Run Forever + Auto Cloudflare Tunnel", flush=True)
    print(f"📁 BASE_DIR: {BASE_DIR}", flush=True)
    print(f"🌐 Local API: http://{API_HOST}:{API_PORT}", flush=True)
    print("☁️ Tunnel: 自动管理 trycloudflare.com", flush=True)
    print("=" * 60, flush=True)

    # Tạo/bind HTTP server trước để cloudflared có local service đích.
    server = ThreadingHTTPServer((API_HOST, API_PORT), RunApiHandler)

    # Tunnel tự động: URL mới sẽ được ghi tunnel.json và push lên GitHub.
    tunnel_thread = threading.Thread(
        target=tunnel_manager_loop,
        name="cloudflare-tunnel-manager",
        daemon=True,
    )
    tunnel_thread.start()

    # Chờ một chút để tunnel có URL trước khi 4 bot bắt đầu thao tác git.
    # Nếu Cloudflare chậm/mất mạng thì không chặn hệ thống quá lâu.
    if TUNNEL_READY_EVENT.wait(timeout=25):
        TUNNEL_PUBLISH_DONE_EVENT.wait(timeout=20)
    else:
        print(
            "⚠️ 25秒内还没拿到 Tunnel URL，API 本地和定时任务仍会继续运行。",
            flush=True,
        )

    scheduler = threading.Thread(
        target=scheduler_loop,
        name="hourly-scheduler",
        daemon=True,
    )
    scheduler.start()

    try:
        print("✅ HTML 查询 API 已启动", flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Stopping...", flush=True)
    finally:
        server.server_close()
        stop_tunnel_manager()


if __name__ == "__main__":
    main()