import warnings
warnings.filterwarnings("ignore")

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import subprocess
import time

BRAZIL = ZoneInfo("America/Sao_Paulo")

SCRIPT = "/Users/xiaoruan/Documents/76b-getdata/quanju-baobiao/quanjubaobiao.py"


def run_job():
    print("=" * 60)
    print("🚀", datetime.now(BRAZIL))

    subprocess.run(
        ["/usr/bin/python3", SCRIPT]
    )

    print("✅ Finish")
    print("✅ 全站汇总更新完成", flush=True)   # <-- thêm dòng này

    print("=" * 60)


# -------------------
# Chạy ngay khi mở
# -------------------
run_job()


while True:

    now = datetime.now(BRAZIL)

    today = now.date()

    run1 = datetime.combine(
        today,
        datetime.min.time(),
        tzinfo=BRAZIL
    ).replace(hour=0, minute=5)

    run2 = datetime.combine(
        today,
        datetime.min.time(),
        tzinfo=BRAZIL
    ).replace(hour=1, minute=5)

    if now < run1:
        target = run1

    elif now < run2:
        target = run2

    else:
        target = run1 + timedelta(days=1)

    wait = (target - now).total_seconds()

    print(f"⏳ Waiting until {target}")

    time.sleep(wait)

    run_job()