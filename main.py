import requests
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ======================
# CONFIG
# ======================

ACCOUNT = "xiaoruan2300"
TOKEN = "41kv9ahnev4zv9uaihf5iviuaecoclw0uwsnm19t"

BASE_URL = "https://api3.a-b-c-5.com/api/backend/trpc/channel.effect"

TENANT_ID = 5317688
REGION_ID = 1

CHANNELS = {
    "fb-h5": 5554,
    "fb-pwa": 5552,
    "fb-ios": 5553,
    "tt-pwa": 5551,
    "kwai-pwa": 5555,
    "回访": 5585,
        "ws-h5": 5586

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
    "origin": "https://admin-2306-66b1c5.m-b-d-1.com",
    "referer": "https://admin-2306-66b1c5.m-b-d-1.com/",
}

# ======================
# TIME (BRAZIL)
# ======================

brazil_time = datetime.now(ZoneInfo("America/Sao_Paulo"))

today = brazil_time.strftime("%Y-%m-%d")

retention_start = (
    brazil_time - timedelta(days=29)
).strftime("%Y-%m-%d")

result_data = {
    "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

# ======================
# SAFE PARSE
# ======================

def safe_get(data):
    try:
        return data.get("result", {}).get("data", {}).get("json", {})
    except:
        return {}
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
        "repeatRechargeAmount",
        "amount"
    ]

    for key in list(row.keys()):

        if key in money_fields:
            if isinstance(row[key], (int, float)):
                row[key] = round(row[key] / 100)

        if key.startswith("amount"):
            if isinstance(row[key], (int, float)):
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
    res_all = requests.get(BASE_URL, headers=headers, params=params_all, timeout=30)
    all_json = safe_get(res_all.json())

    result_data["ALL_TOTAL"] = {
    "normalList": fix_amounts(all_json.get("normalList", {})),
    "parentList": fix_amounts(all_json.get("parentList", {})),
    "childList": fix_amounts(all_json.get("childList", {}))
}

    print("✅ ALL_TOTAL success")

except Exception as e:
    print("❌ ALL_TOTAL error:", e)
    result_data["ALL_TOTAL"] = {}

# ======================
# STEP 2: GET EACH CHANNEL
# ======================


for name, cid in CHANNELS.items():

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

    try:
        res = requests.get(BASE_URL, headers=headers, params=params, timeout=30)
        data = safe_get(res.json())

        result_data[name] = {
            "normalList": fix_amounts(data.get("normalList", {})),
            "parentList": fix_amounts(data.get("parentList", {})),
            "childList": fix_amounts(data.get("childList", {}))
        }

        print(f"✅ {name} success")

    except Exception as e:
        print(f"❌ {name} error:", e)


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

    retention_res = requests.get(
        RETENTION_URL,
        headers=headers,
        params=retention_params,
        timeout=30
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
for name, cid in CHANNELS.items():
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

        retention_res = requests.get(
            RETENTION_URL,
            headers=headers,
            params=retention_params,
            timeout=30
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

            result_data["retention"][day][name] = row

        print(f"✅ retention {name}")

    except Exception as e:
        print(f"❌ retention {name} error:", e)
# ======================
# SAVE JSON
# ======================

output_file = "/Users/xiaoruan/Desktop/76b-getdata/data.json"

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(
        result_data,
        f,
        ensure_ascii=False,
        indent=2
    )

print(f"✅ Saved: {output_file}")