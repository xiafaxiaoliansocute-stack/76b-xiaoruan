import warnings
warnings.filterwarnings("ignore")
import subprocess
import time
from datetime import datetime, timedelta
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

while True:

    try:
        print("🚀 Run:", datetime.now())

        files = [
            "main.py",
            "nn22.py",
            "23a.py",
            "23e.py"
        ]

        for file in files:
            subprocess.run(
                ["python3", os.path.join(BASE_DIR, file)],
                check=True
            )

        print("✅ Done")

    except Exception as e:
        print("❌", e)

    now = datetime.now()

    next_hour = (
        now + timedelta(hours=1)
    ).replace(
        minute=0,
        second=0,
        microsecond=0
    )

    sleep_seconds = (
        next_hour - now
    ).total_seconds()

    print("⏰ Next run:", next_hour)
    print("✅ 推广汇总更新完成", flush=True)

    time.sleep(sleep_seconds)
