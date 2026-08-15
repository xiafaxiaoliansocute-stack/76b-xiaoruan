import warnings
warnings.filterwarnings("ignore")

import os
import subprocess
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FILES = [
    "main.py",
    "nn22.py",
    "23a.py",
    "23e.py",
]


def run_script(filename):
    """
    Chạy 1 web.
    4 file tương ứng 4 web khác nhau nên launcher cho phép chạy đồng thời.
    """
    path = os.path.join(BASE_DIR, filename)

    if not os.path.exists(path):
        return filename, False, f"Không tìm thấy file: {path}"

    try:
        start = datetime.now()

        print(
            f"🚀 {filename} 开始: {start.strftime('%H:%M:%S')}",
            flush=True
        )

        subprocess.run(
            ["python3", path],
            cwd=BASE_DIR,
            check=True
        )

        elapsed = (datetime.now() - start).total_seconds()

        return filename, True, elapsed

    except subprocess.CalledProcessError as e:
        return filename, False, f"exit code {e.returncode}"

    except Exception as e:
        return filename, False, str(e)


while True:

    try:
        print("=" * 60, flush=True)
        print(
            "🚀 开始更新:",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            flush=True
        )

        success_count = 0

        # 4 web khác nhau -> chạy 4 file cùng lúc
        with ThreadPoolExecutor(max_workers=4) as executor:

            futures = [
                executor.submit(run_script, filename)
                for filename in FILES
            ]

            for future in as_completed(futures):

                filename, success, info = future.result()

                if success:
                    success_count += 1
                    print(
                        f"✅ {filename} 完成 | {info:.1f} 秒",
                        flush=True
                    )
                else:
                    print(
                        f"❌ {filename} 错误: {info}",
                        flush=True
                    )

        print(
            f"📊 更新结果: {success_count}/{len(FILES)}",
            flush=True
        )

    except Exception as e:
        print(
            f"❌ Launcher error: {e}",
            flush=True
        )

    # ==========================
    # TÍNH THỜI GIAN CHẠY LẦN SAU
    # ==========================

    now = datetime.now()

    next_hour = (
        now + timedelta(hours=1)
    ).replace(
        minute=0,
        second=0,
        microsecond=0
    )

    sleep_seconds = max(
        1,
        (next_hour - now).total_seconds()
    )

    # ==================================================
    # GIỮ ĐÚNG 4 DÒNG NÀY
    # GUI/BOT CỦA BẠN ĐANG ĐỌC ĐÚNG FORMAT NÀY
    # ==================================================

    print("✅ 推广汇总更新完成", flush=True)
    print("⏳ 下次运行:", flush=True)
    print(
        next_hour.strftime("%Y-%m-%d %H:%M:%S"),
        flush=True
    )
    print(
        f"等待: {round(sleep_seconds / 3600, 2)} 小时",
        flush=True
    )

    # Chờ tới đầu giờ tiếp theo
    time.sleep(sleep_seconds)