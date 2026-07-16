import requests
import json
import time
import random

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# =====================================================
# CONFIG
# =====================================================

TOKEN = "ajgnfuepdrbjhle6orecg93ed4yf6nds0url8cru"

ACCOUNT = "xiaoruan16021"
TENANT_ID = 2654039
REGION_ID = 1

URL = "https://api6.o-9-d-4.com/api/backend/trpc/user.list"

HEADERS = {
    "accept": "*/*",
    "authorization": f"Bearer {TOKEN}",
    "account": ACCOUNT,
    "client-language": "zh-CN",
    "content-type": "application/json",
    "fingerprint-id": "6hUecf0K0ity09A0YcED",
    "origin": "https://admin-16021-9fab47.c-9-m-1.com",
    "referer": "https://admin-16021-9fab47.c-9-m-1.com/",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
    "accept-language": "vi,fr-FR;q=0.9,fr;q=0.8,en-US;q=0.7,en;q=0.6,zh-CN;q=0.5",
"cache-control": "no-cache",
"pragma": "no-cache",
    "x-admin-host": "admin-16021-9fab47.c-9-m-1.com",
}
session = requests.Session()
session.headers.update(HEADERS)
# =====================================================
# 登录类型
# =====================================================

APP_TYPES = {
    "全部": None,
    "安卓H5": "AndroidH5",
    "苹果H5": "iOSH5",
    "PWA": "PWA",
    "APK": "APK",
    "苹果APP": "iOSApp",
    "电脑系统": "DesktopOS",
}

# =====================================================
# Brazil yesterday
# =====================================================

def get_yesterday_range():
    tz = ZoneInfo("America/Sao_Paulo")

    now = datetime.now(tz)

    yesterday = now.date() - timedelta(days=1)

    start = datetime.combine(
        yesterday,
        datetime.min.time(),
        tzinfo=tz
    )

    end = datetime.combine(
        yesterday,
        datetime.max.time().replace(microsecond=0),
        tzinfo=tz
    )

    return (
        yesterday.strftime("%Y-%m-%d"),
        start.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        end.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    )


# =====================================================
# API
# =====================================================

def get_total(app_type, start_time, end_time):

    payload = {
        "json": {
            "queryType": "userId",
            "regionId": REGION_ID,
            "tenantId": TENANT_ID,
            "loginStartTime": start_time,
            "loginEndTime": end_time,
            "page": 1,
            "pageSize": 1,
            "order": [
                {
                    "key": "",
                    "type": "desc"
                }
            ]
        }
    }

    if app_type is not None:
        payload["json"]["appType"] = app_type

    params = {
        "input": json.dumps(payload, separators=(",", ":"))
    }

    for retry in range(10):

        try:

            r = session.get(
                URL,
                params=params,
                timeout=30,
                allow_redirects=True
            )

            # =========================
            # 成功
            # =========================
            if r.status_code == 200:

                data = r.json()

                # In JSON khi cần debug
                # print(json.dumps(data, indent=2, ensure_ascii=False))

                total = (
                    data.get("result", {})
                        .get("data", {})
                        .get("json", {})
                        .get("userList", {})
                        .get("total")
                )

                if total is None:
                    print("❌ Không tìm thấy userList.total")
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                    return 0

                return total

            # =========================
            # 被限流
            # =========================
            elif r.status_code == 429:

                wait = random.randint(1, 5)
                print(f"⚠️ 429，等待 {wait} 秒...")
                time.sleep(wait)
                continue

            # =========================
            # TOKEN失效
            # =========================
            elif r.status_code == 401:

                print("❌ TOKEN 已失效")
                return 0

            else:

                print(f"HTTP {r.status_code}")
                print(r.text)
                time.sleep(3)

        except Exception as e:

            print("Exception:", e)
            time.sleep(5)

    return 0


# =====================================================
# MAIN
# =====================================================

def main():

    day, start_time, end_time = get_yesterday_range()

    print("=" * 60)
    print("Brazil Date :", day)
    print("Start       :", start_time)
    print("End         :", end_time)
    print("=" * 60)

    results = {}

    for i, (name, app) in enumerate(APP_TYPES.items(), 1):

        print(f"\n[{i}/{len(APP_TYPES)}] 查询 {name}")

        total = get_total(app, start_time, end_time)

        results[name] = total

        print(f"{name:<12}: {total:,}")

        if i != len(APP_TYPES):

          sleep_time = random.randint(3, 5)

    print(f"休息 {sleep_time} 秒...")

    time.sleep(sleep_time)

    print()
    print("=" * 60)
    print(f"{'登录类型':<15}{'人数':>15}")
    print("=" * 60)

    for name, total in results.items():
        print(f"{name:<15}{total:>15,}")

    print("=" * 60)
if __name__ == "__main__":
    main()