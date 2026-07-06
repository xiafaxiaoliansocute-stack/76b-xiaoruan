import time
import subprocess
from datetime import datetime

PYTHON = "/usr/local/bin/python3"
SCRIPT = "/Users/xiaoruan/Desktop/76b-getdata/jituan1.py"

while True:
    now = datetime.now()

    # mỗi giờ đúng phút 10 chạy
    if now.minute == 10 and now.second < 5:
        print("开始执行:", now)

        subprocess.run(
            [PYTHON, SCRIPT]
        )

        print("执行完成")

        # tránh chạy lại trong cùng phút
        time.sleep(60)

    time.sleep(5)