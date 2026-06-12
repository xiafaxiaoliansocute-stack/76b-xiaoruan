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

        print("✅ Done")

    except Exception as e:
        print("❌", e)
        
    now = datetime.now()

if now.hour == 23:
    next_hour = now.replace(
        minute=59,
        second=0,
        microsecond=0
    )

    if now.minute >= 59:
        next_hour = (
            now + timedelta(days=1)
        ).replace(
            hour=1,
            minute=0,
            second=0,
            microsecond=0
        )
else:
    next_hour = (
        now + timedelta(hours=1)
    ).replace(
        minute=0,
        second=0,
        microsecond=0
    )
    sleep_seconds = (next_hour - now).total_seconds()

    print("⏰ Next run:", next_hour)

    time.sleep(sleep_seconds)