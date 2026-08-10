# ============================================================
# XIAORUAN RUN ALL
# Version 2.0
# Multi Process Manager
# ============================================================

import os
import sys
import time
import queue
import threading
import subprocess
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
        "name": "集团数据",
        "type": "集团数据",
        "file": BASE_DIR / "jituan-shuju" / "jituan1.py",
    },
    

]

# ============================================================
# GLOBAL
# ============================================================

workers = []

lock = threading.Lock()

# ============================================================
# TELEGRAM
# ============================================================

def telegram(text):

    if not text:
        return

    try:

        requests.post(

            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",

            data={

                "chat_id": CHAT_ID,

                "text": text[:4000],

                "disable_web_page_preview": True,
                "parse_mode": "HTML",

            },

            timeout=30,

        )

    except Exception as e:

        print(f"[Telegram Error] {e}")

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

        status = "✅" if task["file"].exists() else "❌"

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

        self.restart_count = 0
        self.lock = threading.Lock()

    # ========================================================

    def start(self):

        with self.lock:

            if self.running:
                return

            if not check_file(self.file):
                return

            self.finished = False

            log(self.name, "=" * 60)
            log(self.name, "START")
            log(self.name, str(self.file))
            log(self.name, "=" * 60)

            try:

                self.process = subprocess.Popen(

                    [sys.executable, "-u", str(self.file)],

                    cwd=str(self.file.parent),

                    stdout=subprocess.PIPE,

                    stderr=subprocess.STDOUT,

                    text=True,

                    encoding="utf-8",

                    errors="ignore",

                    bufsize=1,

                )

            except Exception as e:

                telegram(
                    f"❌ {self.name}\n\n"
                    f"Start Failed\n\n"
                    f"{e}"
                )

                return

            self.running = True

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

    def restart(self):

        with self.lock:

            if self.running:
                return

            self.restart_count += 1

            log(self.name, f"Restart #{self.restart_count}")

            telegram(
                f"♻️ {self.name}\n"
                f"Restart #{self.restart_count}"
            )

        time.sleep(5)

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

            telegram(
                f"❌ {self.name}\n\n{e}"
            )

        finally:

            self.running = False

            code = -1

            try:
                code = self.process.poll()
            except:
                pass

            log(self.name, f"Exit Code = {code}")

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
# START ALL
# ============================================================

def start_all():

    banner()

    startup_message()

    workers.clear()

    print("🚀 Starting all tasks...\n")

    for cfg in TASKS:

        w = Worker(cfg)

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

        for w in workers:

            try:

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

                telegram(
                    f"⚠️ {w.name}\n"
                    f"Process Exit\n"
                    f"Exit Code : {code}"
                )

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
# START BACKGROUND THREADS
# ============================================================

def start_background():

    threading.Thread(

        target=watchdog,

        daemon=True,

        name="WATCHDOG"

    ).start()
    
# ============================================================
# MAIN
# ============================================================

def main():

    start_all()

    start_background()

    telegram("✅全量任务启动成功")

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

            for w in workers:

                if len(w.buffer) > 500:
                    w.buffer = w.buffer[-100:]

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

        main()

    except Exception as e:

        print(e)

        telegram(

            "❌ RUN ALL CRASH\n\n"

            + str(e)

        )

        raise
