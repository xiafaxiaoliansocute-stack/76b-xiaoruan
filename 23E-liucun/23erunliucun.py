import warnings
warnings.filterwarnings("ignore")

import subprocess
import time
import os

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ==========================================
# 文件目录
# ==========================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

FILES = [
    "23eshoucun.py",
    "23echongzhi.py",
    "23eliucun.py",
]

BRAZIL_TZ = ZoneInfo(
    "America/Sao_Paulo"
)


# ==========================================
# 执行单个文件
# ==========================================

def run_file(filename):

    filepath = os.path.join(
        BASE_DIR,
        filename
    )

    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"找不到文件: {filepath}"
        )

    print("\n" + "=" * 60)
    print("开始执行:", filename)
    print(
        "巴西时间:",
        datetime.now(BRAZIL_TZ).strftime("%Y-%m-%d %H:%M:%S")
    )
    print("=" * 60)

    result = subprocess.run(
        [
            "/usr/bin/python3",
            filepath
        ]
    )

    if result.returncode != 0:
        raise Exception(
            f"{filename} 执行失败"
        )

    print(f"✅ {filename} 完成")


# ==========================================
# 执行全部流程
# ==========================================

def run_all():

    print("\n🚀 总任务开始")

    start = time.time()

    try:

        for file in FILES:

            run_file(file)

            # ----------------------------------
            # 首充、充值都完成后
            # 等30秒再计算留存
            # ----------------------------------
            if file == "23echongzhi.py":

                print()
                print("⏳ 等待30秒...")
                print("确保SQLite数据全部写入后开始计算留存")
                print()

                time.sleep(30)

        print("\n🎉 23E全部完成")

    except Exception as e:

        print("\n❌ 错误:", e)

    print(
        "耗时:",
        round(
            time.time() - start,
            2
        ),
        "秒"
    )

    print("✅ 23E留存计算完成", flush=True)


# ==========================================
# 等待 Brazil 每天00:05
# ==========================================

def wait_next_run():

    try:

        while True:

            now = datetime.now(
                BRAZIL_TZ
            )

            target = now.replace(
                hour=0,
                minute=5,
                second=0,
                microsecond=0
            )

            if now >= target:
                target += timedelta(days=1)

            seconds = (
                target - now
            ).total_seconds()

            print()
            print("⏳ 下次运行:")
            print(
                target.strftime("%Y-%m-%d %H:%M:%S")
            )
            print(
                "等待:",
                round(seconds / 3600, 2),
                "小时"
            )
            print()

            time.sleep(seconds)

            run_all()

    except KeyboardInterrupt:

        print("\n⛔ 已停止程序")


# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":

    print("🇧🇷 Brazil 23E自动任务启动")

    # 第一次启动立即执行
    run_all()

    # 每天00:05自动执行
    wait_next_run()