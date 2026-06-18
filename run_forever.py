import subprocess
import time
from datetime import datetime, timedelta

while True:

    try:
        print("🚀 Run:", datetime.now())

        subprocess.run(
            ["python3", "/Users/xiaoruan/Desktop/76b-getdata/main.py"],
            check=True
        )
        subprocess.run(
           ["python3", "/Users/xiaoruan/Desktop/76b-getdata/nn22.py"],
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

    time.sleep(sleep_seconds)