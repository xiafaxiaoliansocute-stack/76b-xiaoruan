import time
import subprocess
from datetime import datetime

PYTHON = "/usr/bin/python3"
SCRIPT = "/Users/xiaoruan/Documents/76b-getdata/jituan-shuju/jituan1.py"


def run_script():
    print("开始执行:", datetime.now())

    subprocess.run(
        [PYTHON, SCRIPT]
    )

    print("执行完成:", datetime.now())


# ===== 启动时立即执行一次 =====
run_script()


# ===== 后续等待每小时10分执行 =====
last_run_hour = None

while True:
    now = datetime.now()

    # 每小时 10 分执行一次
    if now.minute == 15 and now.second < 5:

        # 防止同一分钟重复执行
        if last_run_hour != now.hour:
            run_script()
            last_run_hour = now.hour

    time.sleep(5)