import warnings
warnings.filterwarnings("ignore")
import requests
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

# ======================
# CONFIG
# ======================

ACCOUNT = "jqr73j"
TOKEN = "zj62gcom0g1muuv5220hkj3iftcwrzdxlkvb51s6"

BASE_URL = "https://api5.v-n-r-1.com/api/backend/trpc/channel.effect"
HOUR_URL = "https://api5.v-n-r-1.com/api/backend/trpc/channel.hourReportSum"
REALTIME_URL = "https://api5.v-n-r-1.com/api/backend/trpc/realTimeData.list"

TENANT_ID = 1634560
REGION_ID = 1

CHANNELS = {
    "fb-h5": 2786,
    "fb-h5-a": 2833,
    "fb-pwa": 2787,
    "fb-pwa-a": 2788,
    "fb-pwa-b": 2789,
    "fb-ios": 2790,
    "kwai-pwa": 2791,
    "tt-h5": 2793,
    "tt-pwa": 2792,
    "上架包": 2795,
    "DL": 2794,
    "其他": 2796

}

# ======================
# HEADER
# ======================

headers = {
    "accept": "*/*",
    "account": ACCOUNT,
    "authorization": f"Bearer {TOKEN}",
    "client-language": "zh-CN",
    "content-type": "application/json",
    "origin": "https://admin-15016-e3adb6.y-7-l-x.com",
    "referer": "https://admin-15016-e3adb6.y-7-l-x.com/",
}
from requests.adapters import HTTPAdapter

session = requests.Session()
session.headers.update(headers)

from requests.adapters import HTTPAdapter

adapter = HTTPAdapter(
    pool_connections=50,
    pool_maxsize=50
)

session.mount("https://", adapter)
session.mount("http://", adapter)

# ======================
# TIME (BRAZIL)
# ======================

BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")
now_br = datetime.now(BRAZIL_TZ)
# 00:00 ~ 00:59 => toàn bộ báo cáo lùi về 1 ngày
if now_br.hour == 0:
    report_day = (now_br - timedelta(days=1)).date()
else:
    report_day = now_br.date()

# "hôm nay" của báo cáo
today = report_day.strftime("%Y-%m-%d")

# "昨日" của báo cáo
yesterday_day = report_day - timedelta(days=1)
yesterday = yesterday_day.strftime("%Y-%m-%d")


# retention lấy theo ngày báo cáo
retention_start = (report_day - timedelta(days=29)).strftime("%Y-%m-%d")

result_data = {
    "update_time_brazil":
        now_br.strftime("%Y-%m-%d %H:%M"),
    "report_day":
        report_day.strftime("%Y-%m-%d")
}
result_data["realtime"] = {}
result_data["hour_report"] = {}

# ======================
# SAFE PARSE
# ======================

def safe_get(data):
    try:
        return data.get("result", {}).get("data", {}).get("json", {})
    except:
        return {}

def make_session():
    s = requests.Session()
    s.headers.update(headers)
    return s

def json_input(payload):
    return {"input": json.dumps({"json": payload}, separators=(',', ':'))}

def build_promotion(parent, child):
    promotion = {}
    for key in set(parent.keys()) | set(child.keys()):
        p = parent.get(key, 0)
        c = child.get(key, 0)
        if isinstance(p, (int, float)) and isinstance(c, (int, float)):
            promotion[key] = p + c
    return promotion

def fix_amounts(obj):
    if not isinstance(obj, dict):
        return obj

    amount_fields = [
        "rechargeAmount",
        "firstRechargeAmount",
        "withdrawAmount",
        "bonusAmount",
        "betAmount",
        "validBetAmount",
        "profitAmount"
    ]

    for k in amount_fields:
        if k in obj and isinstance(obj[k], (int, float)):
            obj[k] = round(obj[k] / 100)

    return obj
def fix_retention_amounts(row):

    money_fields = [
        "recharge",
        "withdrawals",
        "repeatRechargeAmount"
    ]

    for key in list(row.keys()):

        if isinstance(row.get(key), (int, float)):

            # amount, amount1, amount2... amount59
            if key.startswith("amount"):
                row[key] = round(row[key] / 100)

            # các trường tiền khác
            elif key in money_fields:
                row[key] = round(row[key] / 100)

    return row
# ======================
# STEP 1: GET ALL TOTAL (IMPORTANT)
# ======================

params_all = {
    "input": json.dumps({
        "json": {
            "startTime": today,
            "endTime": today,
            "tenantId": TENANT_ID,
            "regionId": REGION_ID,
            "page": 1,
            "pageSize": 50,
            "channelId": []   # 👈 ALL DATA FROM BACKEND
        }
    }, separators=(',', ':'))
}

try:
    res_all = session.get(
    BASE_URL,
    params=params_all,
    timeout=30
)
    all_json = safe_get(res_all.json())

    result_data["ALL_TOTAL"] = {
        "normalList": fix_amounts(all_json.get("normalList", {})),
        "parentList": fix_amounts(all_json.get("parentList", {})),
        "childList": fix_amounts(all_json.get("childList", {}))
    }

    # 推广 = 直推 + 裂变
    parent = result_data["ALL_TOTAL"]["parentList"]
    child = result_data["ALL_TOTAL"]["childList"]

    promotion = {}

    for key in set(parent.keys()) | set(child.keys()):
        p = parent.get(key, 0)
        c = child.get(key, 0)

        if isinstance(p, (int, float)) and isinstance(c, (int, float)):
            promotion[key] = p + c

    result_data["ALL_TOTAL"]["promotionList"] = promotion

    print("✅ ALL_TOTAL success")

except Exception as e:
    print("❌ ALL_TOTAL error:", e)
    result_data["ALL_TOTAL"] = {}

# ======================
# STEP 2: GET EACH CHANNEL (FAST)
# ======================

def load_channel(name, cid):

    try:

        params = {
            "input": json.dumps({
                "json": {
                    "startTime": today,
                    "endTime": today,
                    "tenantId": TENANT_ID,
                    "regionId": REGION_ID,
                    "page": 1,
                    "pageSize": 50,
                    "channelId": [],
                    "channelPromoterId": cid
                }
            }, separators=(',', ':'))
        }

        res = session.get(
            BASE_URL,
            params=params,
            timeout=(3, 20)
        )

        data = safe_get(res.json())

        result = {
            "normalList": fix_amounts(data.get("normalList", {})),
            "parentList": fix_amounts(data.get("parentList", {})),
            "childList": fix_amounts(data.get("childList", {}))
        }

        parent = result["parentList"]
        child = result["childList"]

        promotion = {}

        for key in set(parent.keys()) | set(child.keys()):
            p = parent.get(key, 0)
            c = child.get(key, 0)

            if isinstance(p, (int, float)) and isinstance(c, (int, float)):
                promotion[key] = p + c

        result["promotionList"] = promotion

        return name, result

    except Exception as e:
        print(f"❌ {name} error:", e)
        return None


with ThreadPoolExecutor(max_workers=10) as executor:

    futures = [
        executor.submit(load_channel, name, cid)
        for name, cid in CHANNELS.items()
    ]

    for future in as_completed(futures):

        data = future.result()

        if data:
            name, result = data
            result_data[name] = result
            print(f"✅ {name} success")
        
def fix_hour_amounts(obj):
    if not isinstance(obj, dict):
        return obj

    amount_fields = [
        "firstRechargeAmount",
        "rechargeAmount",
        "withdrawAmount",
        "betAmount",
        "validBetAmount",
        "reward",
        "rechargeWithdrawDiff",
        "splitFirstRechargeAmount",
        "splitRechargeAmount",
        "splitWithdrawAmount",
        "splitBetAmount",
        "splitValidBetAmount",
        "splitReward"
    ]

    for k in amount_fields:
        if k in obj and isinstance(obj[k], (int, float)):
            obj[k] = round(obj[k] / 100)

    return obj

def fix_realtime_amounts(item):

    recharge = round(item.get("rechargeAmount", 0) / 100)
    withdraw = round(item.get("withdrawAmount", 0) / 100)

    return {

        "loginCount": item.get("loginCount", 0),

        "registerCount": item.get("registerCount", 0),

        "betCount": item.get("betCount", 0),

        "onlineCount": item.get("onlineCount", 0),

        "firstRechargeCount":
            item.get("firstRechargeCount", 0),

        "subFirstRechargeCount":
            item.get("subFirstRechargeCount", 0),

        "rechargeCount":
            item.get("rechargeCount", 0),

        "tenantProfit":
            round(item.get("tenantProfitAmount", 0) / 100, 2),

        "manualRecharge":
            f'{round(item.get("manualRechargeAmount",0)/100)} / {item.get("manualRechargeTimes",0)}',

        "orderRecharge":
            f'{round(item.get("orderRechargeAmount",0)/100)} / {item.get("orderRechargeTimes",0)}',

        "manualWithdraw":
            f'{round(item.get("manualWithdrawAmount",0)/100)} / {item.get("manualWithdrawTimes",0)}',

        "orderWithdraw":
            f'{round(item.get("orderWithdrawAmount",0)/100)} / {item.get("orderWithdrawTimes",0)}',

        "diff":
            recharge - withdraw,

        "discount":
            round(item.get("discountAmount",0)/100,2)

    }
# ======================
# HOUR REPORT (昨日)
# ======================

hour_report_day = yesterday_day

hour_start = datetime.combine(
    hour_report_day,
    datetime.min.time(),
    tzinfo=BRAZIL_TZ
)

# 00:00~00:59 Brazil
# 昨日 lấy full ngày
if now_br.hour == 0:

    hour_end = datetime.combine(
        hour_report_day,
        datetime.max.time().replace(microsecond=0),
        tzinfo=BRAZIL_TZ
    )

# Sau 01:00
# 昨日 lấy tới cùng giờ hôm nay
else:

    cutoff = now_br - timedelta(minutes=42)

    hour_end = datetime.combine(
        hour_report_day,
        datetime.min.time(),
        tzinfo=BRAZIL_TZ
    ).replace(
        hour=cutoff.hour,
        minute=59,
        second=59
    )

hour_start = hour_start.astimezone(timezone.utc)
hour_end = hour_end.astimezone(timezone.utc)


print("Brazil now :", now_br)
print("Report day :", report_day)
print("Yesterday  :", yesterday_day)
print("Hour start :", hour_start)
print("Hour end   :", hour_end)

print("Brazil now :", now_br)
print("Hour start :", hour_start)
print("Hour end   :", hour_end)

# ALL TOTAL
try:
    params = {
        "input": json.dumps({
            "json": {
                "tenantId": TENANT_ID,
                "regionId": REGION_ID,
                "channelId": [],
                "page": 1,
                "pageSize": 50,
                "order": [
                    {
                        "key": "firstRechargeCount",
                        "type": "asc"
                    }
                ],
                "startTime": hour_start.isoformat().replace("+00:00", "Z"),
                "endTime": hour_end.isoformat().replace("+00:00", "Z")
            }
        }, separators=(',', ':'))
    }

    res = session.get(
    HOUR_URL,
    params=params,
    timeout=(3, 20)
)

    hour_json = (
        res.json()
        .get("result", {})
        .get("data", {})
        .get("json", {})
    )

    result_data["hour_report"]["ALL_TOTAL"] = fix_hour_amounts(hour_json)
    result_data["hour_report"]["ALL_TOTAL"]["promotionList"] = {
    "firstRechargeCount":
        result_data["hour_report"]["ALL_TOTAL"].get("firstRechargeCount", 0)
        + result_data["hour_report"]["ALL_TOTAL"].get("splitFirstRechargeCount", 0),

    "firstRechargeAmount":
        result_data["hour_report"]["ALL_TOTAL"].get("firstRechargeAmount", 0)
        + result_data["hour_report"]["ALL_TOTAL"].get("splitFirstRechargeAmount", 0),

    "rechargeCount":
        result_data["hour_report"]["ALL_TOTAL"].get("rechargeCount", 0)
        + result_data["hour_report"]["ALL_TOTAL"].get("splitRechargeCount", 0),

    "rechargeAmount":
        result_data["hour_report"]["ALL_TOTAL"].get("rechargeAmount", 0)
        + result_data["hour_report"]["ALL_TOTAL"].get("splitRechargeAmount", 0)
}

    print("✅ hour ALL_TOTAL")

except Exception as e:
    print("❌ hour ALL_TOTAL", e)

# ======================
# HOUR REPORT EACH CHANNEL (FAST)
# ======================

def load_hour_channel(name, cid):

    try:

        params = {
            "input": json.dumps({
                "json": {
                    "tenantId": TENANT_ID,
                    "regionId": REGION_ID,
                    "channelId": [],
                    "channelPromoterId": cid,
                    "page": 1,
                    "pageSize": 50,
                    "order": [
                        {
                            "key": "firstRechargeCount",
                            "type": "asc"
                        }
                    ],
                    "startTime": hour_start.isoformat().replace("+00:00", "Z"),
                    "endTime": hour_end.isoformat().replace("+00:00", "Z")
                }
            }, separators=(',', ':'))
        }

        res = session.get(
            HOUR_URL,
            params=params,
            timeout=(3, 20)
        )

        hour_json = (
            res.json()
            .get("result", {})
            .get("data", {})
            .get("json", {})
        )

        data = fix_hour_amounts(hour_json)

        data["promotionList"] = {
            "firstRechargeCount":
                data.get("firstRechargeCount", 0)
                + data.get("splitFirstRechargeCount", 0),

            "firstRechargeAmount":
                data.get("firstRechargeAmount", 0)
                + data.get("splitFirstRechargeAmount", 0),

            "rechargeCount":
                data.get("rechargeCount", 0)
                + data.get("splitRechargeCount", 0),

            "rechargeAmount":
                data.get("rechargeAmount", 0)
                + data.get("splitRechargeAmount", 0)
        }

        return name, data

    except Exception as e:
        print(f"❌ hour {name}", e)
        return None


with ThreadPoolExecutor(max_workers=10) as executor:

    futures = [
        executor.submit(load_hour_channel, name, cid)
        for name, cid in CHANNELS.items()
    ]

    for future in as_completed(futures):

        result = future.result()

        if result:
            name, data = result
            result_data["hour_report"][name] = data
            print(f"✅ hour {name}")

    
# ======================
# STEP 3: GET RETENTION
# ======================



RETENTION_URL = "https://api3.a-b-c-5.com/api/backend/trpc/channel.dayRetention"

result_data["retention"] = {}
# ======================
# ALL RETENTION
# ======================

try:

    retention_params = {
        "input": json.dumps({
            "json": {
                "tenantId": TENANT_ID,
                "regionId": REGION_ID,
                "startTime": retention_start,
                "endTime": today,
                "type": "recharge",

                "channelIds": [],

                "parentType": "none",
                "page": 1,
                "pageSize": 50,
                "timeType": "days_90",

                "order": [
                    {
                        "key": "time",
                        "type": "desc"
                    }
                ],

                "retentionDays": [0,1,2,3,4,5,6,9,13,29,59]
            }
        }, separators=(',', ':'))
    }

    retention_res = session.get(
    RETENTION_URL,
    params=retention_params,
    timeout=(3, 20)
)

    retention_json = retention_res.json()

    retention_data = (
        retention_json.get("result", {})
        .get("data", {})
        .get("json", {})
        .get("data", {})
        .get("retentionList", [])
    )

    for row in retention_data:
        row = fix_retention_amounts(row)
        day = row.get("time")

        if day not in result_data["retention"]:
            result_data["retention"][day] = {}

        result_data["retention"][day]["ALL"] = row

    print("✅ retention ALL")

except Exception as e:
    print("❌ retention ALL error:", e)
# ======================
# RETENTION EACH CHANNEL (FAST)
# ======================

def load_retention_channel(name, cid):

    try:

        retention_params = {
            "input": json.dumps({
                "json": {
                    "tenantId": TENANT_ID,
                    "regionId": REGION_ID,
                    "startTime": retention_start,
                    "endTime": today,
                    "type": "recharge",
                    "channelIds": [],
                    "channelPromoterId": cid,
                    "parentType": "none",
                    "page": 1,
                    "pageSize": 50,
                    "timeType": "days_90",
                    "order": [
                        {
                            "key": "time",
                            "type": "desc"
                        }
                    ],
                    "retentionDays": [0,1,2,3,4,5,6,9,13,29,59]
                }
            }, separators=(',', ':'))
        }

        retention_res = session.get(
            RETENTION_URL,
            params=retention_params,
            timeout=(3, 20)
        )

        retention_json = retention_res.json()

        retention_data = (
            retention_json.get("result", {})
            .get("data", {})
            .get("json", {})
            .get("data", {})
            .get("retentionList", [])
        )

        return name, retention_data

    except Exception as e:
        print(f"❌ retention {name} error:", e)
        return None


with ThreadPoolExecutor(max_workers=10) as executor:

    futures = [
        executor.submit(load_retention_channel, name, cid)
        for name, cid in CHANNELS.items()
    ]

    for future in as_completed(futures):

        result = future.result()

        if not result:
            continue

        name, retention_data = result

        for row in retention_data:

            row = fix_retention_amounts(row)
            day = row.get("time")

            if day not in result_data["retention"]:
                result_data["retention"][day] = {}

            result_data["retention"][day][name] = row

        print(f"✅ retention {name}")

        # ======================
# REPEAT RATE
# ======================

result_data["repeat_rate"] = {}
# ======================
# NEXT AVG
# ======================

result_data["next_avg"] = {}

NEXT_TYPES = {
    "first": "none",
    "parent": "direct",
    "child": "split"
}

for key, parent_type in NEXT_TYPES.items():

    try:

        params = {
            "input": json.dumps({
                "json": {
                    "tenantId": TENANT_ID,
                    "regionId": REGION_ID,
                    "startTime": retention_start,
                    "endTime": today,
                    "type": "recharge",
                    "channelIds": [],
                    "parentType": parent_type,
                    "page": 1,
                    "pageSize": 50,
                    "timeType": "days_90",
                    "retentionDays": [0,1]
                }
            }, separators=(',', ':'))
        }

        res = session.get(
    RETENTION_URL,
    params=params,
    timeout=30
)

        data = (
            res.json()
            .get("result", {})
            .get("data", {})
            .get("json", {})
            .get("data", {})
            .get("retentionList", [])
        )

        if len(data) >= 2:

            yesterday = yesterday_day.strftime("%Y-%m-%d")

            row = next(
                (r for r in data if r.get("time") == yesterday),
                None
            )

            if row:

                amount1 = row.get("amount1", 0) / 100
                count1 = row.get("count1", 0)

                result_data["next_avg"][key] = (
                    round(amount1 / count1, 2)
                    if count1 else 0
                )

            else:
                result_data["next_avg"][key] = 0

        else:
            result_data["next_avg"][key] = 0

    except Exception as e:
        print("next avg error:", key, e)
        result_data["next_avg"][key] = 0

REPEAT_TYPES = {
    "first": "none",      # 首充
    "parent": "direct",   # 直推首充
    "child": "split"      # 裂变首充
}

for key, parent_type in REPEAT_TYPES.items():

    try:

        params = {
            "input": json.dumps({
                "json": {
                    "tenantId": TENANT_ID,
                    "regionId": REGION_ID,
                    "startTime": today,
                    "endTime": today,
                    "type": "recharge",
                    "channelIds": [],
                    "parentType": parent_type,
                    "page": 1,
                    "pageSize": 50,
                    "timeType": "days_90",
                    "retentionDays": [0]
                }
            }, separators=(',', ':'))
        }

        res = session.get(
    RETENTION_URL,
    params=params,
    timeout=30
)

        data = (
            res.json()
            .get("result", {})
            .get("data", {})
            .get("json", {})
            .get("data", {})
            .get("retentionList", [])
        )

        if data:
            row = data[-1]   # hôm nay

            count = row.get("count", 0)
            repeat = row.get("repeatRechargeCount", 0)

            result_data["repeat_rate"][key] = (
                round(repeat / count * 100, 2)
                if count else 0
            )
        else:
            result_data["repeat_rate"][key] = 0

    except Exception as e:
        print("repeat rate error:", key, e)
        result_data["repeat_rate"][key] = 0

 # ======================
# REALTIME (4 DAYS)
# ======================

print("Loading realtime data...")

from datetime import datetime

dates = [
    (report_day - timedelta(days=i)).strftime("%Y-%m-%d")
    for i in range(4)
]

for date in dates:

    try:

        params = {
            "input": json.dumps({
                "json": {
                    "tenantId": TENANT_ID,
                    "dateTime": date
                }
            }, separators=(',', ':'))
        }

        res = session.get(
            REALTIME_URL,
            params=params,
            timeout=(3,20)
        )

        realtime_json = (
            res.json()
            .get("result", {})
            .get("data", {})
            .get("json", [])
        )

        for item in realtime_json:

            try:

                utc_time = datetime.fromisoformat(
                    item["createTime"].replace("Z","")
                )

                brazil_time = utc_time - timedelta(hours=3)

                   # lấy đầy đủ 5 phút/lần
                time_key = brazil_time.strftime("%H:%M")

                time_key = brazil_time.strftime("%H:%M")

                if time_key not in result_data["realtime"]:
                    result_data["realtime"][time_key] = {}

                result_data["realtime"][time_key][date] = fix_realtime_amounts(item)
                    
                result_data["realtime"] = dict(
    sorted(result_data["realtime"].items())
)

            except Exception as e:
                print("Realtime Parse Error:", e)

        print(f"✅ realtime {date}")

    except Exception as e:

        print(f"❌ realtime {date}", e)      
# ======================
# SAVE JSON
# ======================


output_file = "/Users/xiaoruan/Documents/76b-getdata/data.json"

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(
        result_data,
        f,
        ensure_ascii=False,
        indent=4
    )

print(f"✅ Saved: {output_file}")
import subprocess

try:
    subprocess.run(
        ["git", "add", "data.json"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    result = subprocess.run(
        ["git", "commit", "-m", "auto update data"],
        capture_output=True,
        text=True
    )

    if "nothing to commit" in result.stdout:
        print("ℹ️ No data changes")
    else:
        print("✅ Commit success")

    subprocess.run(
        ["git", "push", "origin", "main"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    print("✅ GitHub updated")

except Exception as e:
    print("❌ GitHub push error:", e)