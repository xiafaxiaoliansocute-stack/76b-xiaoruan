import asyncio
import aiohttp
import json
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from aiohttp import ClientTimeout

# Fast async data fetcher for the same backend API.
# This file is separate from main.py and does not modify the original script.

ACCOUNT = "xiaoruan2300"
TOKEN = "icp5obt3jiro5zzhwjo7fucdaue569udcz4cmag7"

BASE_URL = "https://api3.a-b-c-5.com/api/backend/trpc/channel.effect"
HOUR_URL = "https://api3.a-b-c-5.com/api/backend/trpc/channel.hourReportSum"
RETENTION_URL = "https://api3.a-b-c-5.com/api/backend/trpc/channel.dayRetention"

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

HEADERS = {
    "accept": "*/*",
    "account": ACCOUNT,
    "authorization": f"Bearer {TOKEN}",
    "client-language": "zh-CN",
    "content-type": "application/json",
    "origin": "https://admin-2306-66b1c5.m-b-d-1.com",
    "referer": "https://admin-2306-66b1c5.m-b-d-1.com/",
}

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "data.json")


def safe_get(data):
    try:
        return data.get("result", {}).get("data", {}).get("json", {})
    except Exception:
        return {}


def json_input(payload):
    return {"input": json.dumps({"json": payload}, separators=(",", ":"))}


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


def fix_retention_amounts(row):
    money_fields = [
        "recharge",
        "withdrawals",
        "repeatRechargeAmount",
        "amount"
    ]

    for key in list(row.keys()):
        if key in money_fields and isinstance(row[key], (int, float)):
            row[key] = round(row[key] / 100)
        if key.startswith("amount") and isinstance(row[key], (int, float)):
            row[key] = round(row[key] / 100)

    return row


async def fetch_json(session, url, payload, sem):
    async with sem:
        timeout = ClientTimeout(total=30)
        async with session.get(url, params=json_input(payload), timeout=timeout) as response:
            response.raise_for_status()
            return await response.json()


async def get_all_total(session, sem, today):
    payload = {
        "startTime": today,
        "endTime": today,
        "tenantId": TENANT_ID,
        "regionId": REGION_ID,
        "page": 1,
        "pageSize": 50,
        "channelId": []
    }
    data = safe_get(await fetch_json(session, BASE_URL, payload, sem))
    normal = fix_amounts(data.get("normalList", {}))
    parent = fix_amounts(data.get("parentList", {}))
    child = fix_amounts(data.get("childList", {}))
    return (
        "all_total",
        {
            "normalList": normal,
            "parentList": parent,
            "childList": child,
            "promotionList": build_promotion(parent, child)
        }
    )


async def get_channel(session, name, cid, sem, today):
    payload = {
        "startTime": today,
        "endTime": today,
        "tenantId": TENANT_ID,
        "regionId": REGION_ID,
        "page": 1,
        "pageSize": 50,
        "channelId": [],
        "channelPromoterId": cid
    }
    data = safe_get(await fetch_json(session, BASE_URL, payload, sem))
    normal = fix_amounts(data.get("normalList", {}))
    parent = fix_amounts(data.get("parentList", {}))
    child = fix_amounts(data.get("childList", {}))
    return (
        "channel",
        name,
        {
            "normalList": normal,
            "parentList": parent,
            "childList": child,
            "promotionList": build_promotion(parent, child)
        }
    )


async def get_hour_report(session, name, cid, sem, hour_start, hour_end):
    payload = {
        "tenantId": TENANT_ID,
        "regionId": REGION_ID,
        "channelId": [],
        "page": 1,
        "pageSize": 50,
        "order": [{"key": "firstRechargeCount", "type": "asc"}],
        "startTime": hour_start,
        "endTime": hour_end
    }
    if cid is not None:
        payload["channelPromoterId"] = cid
    hour_json = (await fetch_json(session, HOUR_URL, payload, sem)).get("result", {}).get("data", {}).get("json", {})
    fixed = fix_hour_amounts(hour_json)
    fixed["promotionList"] = {
        "firstRechargeCount": fixed.get("firstRechargeCount", 0) + fixed.get("splitFirstRechargeCount", 0),
        "firstRechargeAmount": fixed.get("firstRechargeAmount", 0) + fixed.get("splitFirstRechargeAmount", 0),
        "rechargeCount": fixed.get("rechargeCount", 0) + fixed.get("splitRechargeCount", 0),
        "rechargeAmount": fixed.get("rechargeAmount", 0) + fixed.get("splitRechargeAmount", 0)
    }
    return ("hour_report", name, fixed)


async def get_retention(session, name, cid, sem, retention_start, today):
    payload = {
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
        "order": [{"key": "time", "type": "desc"}],
        "retentionDays": [0, 1, 2, 3, 4, 5, 6, 9, 13, 29, 59]
    }
    if cid is not None:
        payload["channelPromoterId"] = cid
    retention_json = await fetch_json(session, RETENTION_URL, payload, sem)
    retention_data = (
        retention_json.get("result", {})
        .get("data", {})
        .get("json", {})
        .get("data", {})
        .get("retentionList", [])
    )
    output = {}
    for row in retention_data:
        row = fix_retention_amounts(row)
        day = row.get("time")
        if day:
            output[day] = row
    return ("retention", name, output)


async def get_next_avg(session, key, parent_type, sem, retention_start, today, report_br):
    payload = {
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
        "retentionDays": [0, 1]
    }
    data = (await fetch_json(session, RETENTION_URL, payload, sem)).get("result", {}).get("data", {}).get("json", {}).get("data", {}).get("retentionList", [])
    yesterday = (report_br - timedelta(days=1)).strftime("%Y-%m-%d")
    row = next((r for r in data if r.get("time") == yesterday), None)
    if row:
        amount1 = row.get("amount1", 0) / 100
        count1 = row.get("count1", 0)
        return ("next_avg", key, round(amount1 / count1, 2) if count1 else 0)
    return ("next_avg", key, 0)


async def get_repeat_rate(session, key, parent_type, sem, today):
    payload = {
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
    data = (await fetch_json(session, RETENTION_URL, payload, sem)).get("result", {}).get("data", {}).get("json", {}).get("data", {}).get("retentionList", [])
    if data:
        row = data[-1]
        count = row.get("count", 0)
        repeat = row.get("repeatRechargeCount", 0)
        return ("repeat_rate", key, round(repeat / count * 100, 2) if count else 0)
    return ("repeat_rate", key, 0)


async def main():
    now_br = datetime.now(ZoneInfo("America/Sao_Paulo"))
    report_br = now_br - timedelta(days=1) if now_br.hour == 0 else now_br
    today = report_br.strftime("%Y-%m-%d")
    retention_start = (report_br - timedelta(days=29)).strftime("%Y-%m-%d")

    result_data = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hour_report": {},
        "retention": {},
        "repeat_rate": {},
        "next_avg": {}
    }

    sem = asyncio.Semaphore(24)
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        tasks = [get_all_total(session, sem, today)]
        tasks += [get_channel(session, name, cid, sem, today) for name, cid in CHANNELS.items()]

        hour_start = (report_br - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        hour_end = (report_br - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999000).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        tasks.append(get_hour_report(session, "ALL_TOTAL", None, sem, hour_start, hour_end))
        tasks += [get_hour_report(session, name, cid, sem, hour_start, hour_end) for name, cid in CHANNELS.items()]

        tasks.append(get_retention(session, "ALL", None, sem, retention_start, today))
        tasks += [get_retention(session, name, cid, sem, retention_start, today) for name, cid in CHANNELS.items()]

        next_types = {"first": "none", "parent": "direct", "child": "split"}
        tasks += [get_next_avg(session, key, parent_type, sem, retention_start, today, report_br) for key, parent_type in next_types.items()]
        tasks += [get_repeat_rate(session, key, parent_type, sem, today) for key, parent_type in next_types.items()]

        results = await asyncio.gather(*tasks, return_exceptions=True)

    for item in results:
        if isinstance(item, Exception):
            print("❌ request error:", item)
            continue
        tag = item[0]
        if tag == "all_total":
            result_data["ALL_TOTAL"] = item[1]
        elif tag == "channel":
            _, name, data = item
            result_data[name] = data
        elif tag == "hour_report":
            _, name, data = item
            result_data["hour_report"][name] = data
        elif tag == "retention":
            _, name, data = item
            for day, row in data.items():
                if day not in result_data["retention"]:
                    result_data["retention"][day] = {}
                result_data["retention"][day][name] = row
        elif tag == "next_avg":
            _, key, value = item
            result_data["next_avg"][key] = value
        elif tag == "repeat_rate":
            _, key, value = item
            result_data["repeat_rate"][key] = value

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
