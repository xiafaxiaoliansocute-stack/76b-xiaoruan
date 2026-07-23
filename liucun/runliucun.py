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
    "chongzhijilu.py",
    "meirishoucun.py",
    "liucun.py",
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

    print("\n" + "="*60)
    print("开始执行:", filename)
    print(
        "巴西时间:",
        datetime.now(BRAZIL_TZ)
    )
    print("="*60)


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


    print(
        "✅ 完成:",
        filename
    )



# ==========================================
# 执行全部流程
# ==========================================

def run_all():


    print(
        "🚀 总任务开始"
    )


    start=time.time()


    try:

        for file in FILES:

            run_file(file)

            time.sleep(3)


        print(
            "🎉 全部完成"
        )


    except Exception as e:

        print(
            "❌ 错误:",
            e
        )


    print(
        "耗时:",
        round(
            time.time()-start,
            2
        ),
        "秒"
    )



# ==========================================
# 计算下一次 Brazil 00:05
# ==========================================

def wait_next_run():

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


        # 今天已经过了00:05
        # 等明天

        if now >= target:

            target += timedelta(
                days=1
            )


        seconds = (
            target-now
        ).total_seconds()


        print(
            "⏳ 下次运行:",
            target
        )

        print(
            "等待:",
            round(seconds/3600,2),
            "小时"
        )


        time.sleep(
            seconds
        )


        run_all()



# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":


    print(
        "🇧🇷 Brazil 自动任务启动"
    )


    wait_next_run()