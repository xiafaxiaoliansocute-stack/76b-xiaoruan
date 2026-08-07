import os
import json
import ast
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import threading
from io import BytesIO, StringIO
import asyncio
import atexit
import re
import random

import pytz
import httpx
import pandas as pd

from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update

# ---------------- Config ----------------
send_folder = "rc_send"
hf_folder = "hf_files"
os.makedirs(send_folder, exist_ok=True)
os.makedirs(hf_folder, exist_ok=True)

with open("config_setting.json", "r", encoding="utf-8-sig") as f:
    cfg = json.load(f)

# -- bot --------------
TELEGRAM_TOKEN =cfg["bot_stt"]["bot_token"]
CHAT_ID = cfg["bot_stt"]["group_id"]

# -- houtai -----------
TENANT_ID = int(cfg["payload"].get("tenantId"))
PAGE_SIZE = int(cfg["payload"].get("pageSize",2000))
BASE_URL = cfg.get("url").rstrip("/")
HEADERS = cfg.get("headers", {})
operator = cfg.get("operator")
double_Type = cfg.get("doubleType", "RECHARGE")

bot_app = None
bot_loop = None
batch_start_time = None
batch_end_time = None
notify_dict = {}

# globals used by multiple functions
multiplier = 5
multiplier_2 = 1
expire_time = 1
bonus_map = {}
bonus_key = "on"

# ---------------- HTTP client (global, re-use) ----------------
limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
client = httpx.Client(timeout=30, limits=limits)
atexit.register(client.close)

# ---------------- Time helpers (Brazil / America/Sao_Paulo) ----------------
BRAZIL_TZ = pytz.timezone("America/Sao_Paulo")

def update_times():
    global now_brazil, brazil_tomorrow, now_date_str, yesterday_date_str
    global send_time_str, hf_time_str, today_brazil_midnight, date_tag
    global api_start_today, api_end_today, api_start_yesterday, api_end_yesterday

    now_brazil = datetime.now(BRAZIL_TZ)

    now_date_str       = now_brazil.strftime("%Y-%m-%d")
    brazil_tomorrow    = (now_brazil + timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_date_str = (now_brazil - timedelta(days=1)).strftime("%Y-%m-%d")

    send_time_str = now_brazil.strftime("%Y-%m-%d %H:%M:%S")
    hf_time_str   = now_brazil.strftime("%Y_%m_%d_%H_%M_%S")

    today_brazil_midnight = now_brazil.replace(hour=0, minute=0, second=0, microsecond=0)

    # Start / end of today in Brazil time → convert to UTC for API
    start_today_local = today_brazil_midnight
    end_today_local   = now_brazil.replace(hour=23, minute=59, second=59, microsecond=999000)

    start_yesterday_local = start_today_local - timedelta(days=1)
    end_yesterday_local   = start_today_local - timedelta(microseconds=1000)

    api_start_today     = start_today_local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    api_end_today       = end_today_local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.999Z")
    api_start_yesterday = start_yesterday_local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    api_end_yesterday   = end_yesterday_local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.999Z")

    date_tag = f"{now_brazil.month:02d}{now_brazil.day:02d}"


# ---------------- Telegram bot ----------------
def run_telegram_bot():
    global bot_app, bot_loop
    if not TELEGRAM_TOKEN:
        print("Telegram token not set, skipping bot start.")
        return

    bot_app = Application.builder().token(TELEGRAM_TOKEN).build()
    register_bot_commands(bot_app)

    async def _set_loop_and_run():
        global bot_loop
        bot_loop = asyncio.get_running_loop()
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling()
        await asyncio.Event().wait()

    asyncio.run(_set_loop_and_run())


async def _send_message_async(text):
    try:
        if bot_app and bot_app.bot:
            await bot_app.bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")
        else:
            print("bot_app not initialized")
    except Exception as e:
        print(f"Telegram send error: {e}")


async def _send_file_async(file_path, retries=3, delete_after_send=True):
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"File {file_path} not found")
        return

    for attempt in range(1, retries + 1):
        try:
            with open(file_path, "rb") as f:
                if bot_app and bot_app.bot:
                    await bot_app.bot.send_document(chat_id=CHAT_ID, document=f)
                else:
                    print("bot_app not initialized")
                    return

            print(f"File sent successfully: {file_path}")

            if delete_after_send and file_path.exists():
                try:
                    file_path.unlink()
                    print(f"Deleted file after send: {file_path}")
                except Exception as e:
                    print(f"Could not delete file {file_path}: {e}")
            return

        except Exception as e:
            print(f"Telegram send file error (attempt {attempt}): {e}")
            if attempt < retries:
                await asyncio.sleep(2)


def send_telegram_message(text=None, file_path=None):
    if not (text or file_path):
        print("Need to provide text or file_path")
        return
    if not bot_loop or not bot_app:
        print("Bot loop not ready; cannot send Telegram message")
        return

    if text:
        asyncio.run_coroutine_threadsafe(_send_message_async(text), bot_loop)

    if file_path:
        asyncio.run_coroutine_threadsafe(
            _send_file_async(file_path, delete_after_send=True),
            bot_loop
        )


def map_bonus(amount, bonus_map_local):
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return 0
    applied = 0
    for threshold, val in sorted(bonus_map_local.items(), key=lambda x: float(x[0])):
        try:
            threshold_num = float(threshold)
        except Exception:
            continue
        if amount >= threshold_num:
            applied = val
        else:
            break
    return applied


def calculate_percentage_bonus(amount, percent_rules, min_bonus=0.8, max_bonus=20):
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return 0

    applied_percent = 0
    for threshold, percent in sorted(percent_rules.items(), key=lambda x: float(x[0])):
        try:
            threshold_num = float(threshold)
            percent_num = float(percent)
        except (ValueError, TypeError):
            continue
        if amount >= threshold_num:
            applied_percent = percent_num
        else:
            break

    if applied_percent <= 0:
        return 0

    bonus = amount * applied_percent / 100.0
    return max(float(min_bonus), min(float(max_bonus), bonus))


# ---------------- HTTP helpers ----------------
def fetch_page(url, headers, payload, retries=8):
    params = {"input": json.dumps({"json": payload})}
    for attempt in range(1, retries + 1):
        try:
            resp = client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code == 429:
                retry_after = e.response.headers.get("Retry-After")
                try:
                    server_wait = float(retry_after)
                except (TypeError, ValueError):
                    server_wait = 0
                # Some servers return Retry-After: 0 even while the rate limit
                # is still active. Always enforce our own exponential delay.
                backoff_wait = min(90, 3 * (2 ** (attempt - 1)))
                wait_seconds = max(server_wait, backoff_wait)
                wait_seconds += random.uniform(0.5, 1.5)
                print(
                    f"Rate limited on page {payload.get('page', 1)} "
                    f"(attempt {attempt}/{retries}); waiting {wait_seconds:.1f}s"
                )
            else:
                wait_seconds = min(30, 2 ** attempt)
                print(
                    f"HTTP {status_code} on page {payload.get('page', 1)} "
                    f"(attempt {attempt}/{retries}); waiting {wait_seconds:.1f}s"
                )

            if attempt == retries:
                raise RuntimeError(
                    f"Failed to fetch page {payload.get('page', 1)} after {retries} attempts"
                ) from e
            time.sleep(wait_seconds)
        except Exception as e:
            print(f"Error fetching page {payload.get('page', 1)} (attempt {attempt}/{retries}): {e}")
            if attempt == retries:
                raise RuntimeError(
                    f"Failed to fetch page {payload.get('page', 1)} after {retries} attempts"
                ) from e
            time.sleep(min(30, 2 ** attempt) + random.uniform(0.2, 1.0))




def export_all_pages_main(headers, poll_attempts=120, wait_seconds=15):
    """Export the same user data/filter used by fetch_all_pages_main."""
    url_export = f"{BASE_URL}/user.list"
    url_export_list = f"{BASE_URL}/exportData.list"
    url_download = f"{BASE_URL}/exportData.download"

    export_payload = {
        "queryType": "userId",
        "regionId": 1,
        "tenantId": TENANT_ID,
        "loginStartTime": api_start_today,
        "loginEndTime": api_end_today.replace(".999Z", ".000Z"),
        "coinFilters": [
            {"coinType": "historicalPay", "coinValueStart": 2000},
            {"coinType": "dayPay", "coinValueEnd": 0},
        ],
        "queryDataType": "export",
        "order": [
            {"key": "registerTime", "type": "asc"},
            {"key": "id", "type": "asc"},
        ],
    }
    list_payload = {
        "page": 1,
        "pageSize": 50,
        "regionId": 1,
        "tenantId": TENANT_ID,
        "lastOperator": operator,
    }

    def get_export_list():
        response = client.get(
            url_export_list,
            headers=headers,
            params={"input": json.dumps({"json": list_payload})},
        )
        response.raise_for_status()
        return (
            response.json()
            .get("result", {})
            .get("data", {})
            .get("json", {})
            .get("exportDataList", [])
        )

    def is_matching_user_export(item):
        """Match this exact export, not merely the newest export job."""
        remark = str(item.get("remark", ""))
        module_type = str(item.get("moduleType", "")).lower()
        is_user_list = module_type == "userlist"
        is_same_operator = str(item.get("lastOperator", "")) == str(operator)
        is_same_date = now_date_str in remark
        is_same_filter = (
            "历史充值:20.00-未指定" in remark
            and "当日充值:未指定-0.00" in remark
        )
        return is_user_list and is_same_operator and is_same_date and is_same_filter

    # Reuse an unfinished/undownloaded matching export instead of creating duplicates.
    try:
        existing_items = get_export_list()
        existing_ids = {str(item.get("id")) for item in existing_items}
    except Exception as exc:
        print(f"Could not read existing export jobs: {exc}")
        existing_items = []
        existing_ids = set()

    reusable = [
        item for item in existing_items
        if is_matching_user_export(item)
        and item.get("downloadCount", 0) == 0
        and item.get("status") in ("Exporting", "Pending", "Ready", "ExportSuccess")
    ]
    reusable.sort(key=lambda item: item.get("createTime", ""), reverse=True)
    target_export_id = str(reusable[0]["id"]) if reusable else None

    if target_export_id:
        print(
            f"Reusing user export id={target_export_id}, "
            f"status={reusable[0].get('status')}"
        )
    else:
        print("Triggering user.list export (queryDataType=export)...")
        response = client.get(
            url_export,
            headers=headers,
            params={"input": json.dumps({"json": export_payload})},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"User export request failed ({response.status_code}): {response.text[:2000]}"
            ) from exc

        trigger_json = response.json().get("result", {}).get("data", {}).get("json", {})
        if isinstance(trigger_json, dict) and trigger_json.get("userList"):
            raise RuntimeError("Backend treated the export request as a normal user.list query")

    export_item = None
    for attempt in range(1, poll_attempts + 1):
        time.sleep(wait_seconds)
        try:
            items = get_export_list()
        except Exception as exc:
            print(f"Export poll {attempt}/{poll_attempts} failed: {exc}")
            continue

        candidates = [
            item for item in items
            if is_matching_user_export(item)
            and (
                str(item.get("id")) == target_export_id
                or (target_export_id is None and str(item.get("id")) not in existing_ids)
            )
        ]
        candidates.sort(key=lambda item: item.get("createTime", ""), reverse=True)
        if not candidates:
            print(
                f"Export poll {attempt}/{poll_attempts}: waiting for matching 会员列表 "
                f"({now_date_str}, operator={operator})..."
            )
            continue

        latest = candidates[0]
        status = latest.get("status")
        print(
            f"Export poll {attempt}/{poll_attempts}: "
            f"module={latest.get('moduleType')} status={status}"
        )
        if status in ("ExportSuccess", "Completed", "Finished", "已完成"):
            export_item = latest
            break
        if status not in ("Exporting", "Pending", "Ready", "处理中", None):
            raise RuntimeError(f"User export failed with status: {status}")

    if not export_item:
        raise RuntimeError("User export did not finish before timeout")

    response = client.post(
        url_download,
        headers=headers,
        json={"json": {"tenantId": TENANT_ID, "id": export_item["id"]}},
    )
    response.raise_for_status()
    file_url = response.json()["result"]["data"]["json"]["filePath"]

    file_response = client.get(file_url)
    file_response.raise_for_status()
    content_type = file_response.headers.get("content-type", "").lower()
    if file_url.lower().endswith((".xlsx", ".xls")) or "spreadsheet" in content_type:
        df_export = pd.read_excel(BytesIO(file_response.content), dtype=str)
    else:
        df_export = pd.read_csv(
            StringIO(file_response.text.lstrip("\ufeff")),
            dtype=str,
            low_memory=False,
        )

    # Keep only the columns used by process_file, in normal currency units.
    column_map = {
        "会员id": "会员id",
        "历史充值": "历史充值",
        "历史提款": "历史提现",
        "会员层级": "会员层级",
        "登录类型": "登录类型",
        "余额": "余额",
    }
    missing = [name for name in column_map if name not in df_export.columns]
    if missing:
        raise RuntimeError(f"User export is missing required columns: {missing}")

    df_export = df_export[list(column_map)].rename(columns=column_map)
    return df_export
    


def fetch_all_pages_3day_rc(url, headers):
    all_records = []
    MAX_PAGES = 100

    # Three complete Brazil calendar days, excluding the current partial day.
    end_date = (now_brazil - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (now_brazil - timedelta(days=3)).strftime("%Y-%m-%d")
    payload ={
        "page":1,
        "pageSize":PAGE_SIZE,
        "isRecharge":True,
        "type":"normal",
        "valueType":"phone",
        "regionId":1,
        "tenantId":TENANT_ID,
        "queryTime":[start_date, end_date],
        "queryData":[{"queryType":"recharge","startValue":0.001}],
        "order":[{"key":"userId","type":"desc"}],
        "queryType":"table",
        "startTime":start_date,
        "endTime":end_date
        }


    for page in range(1, MAX_PAGES + 1):
        payload["page"] = page
        payload["pageSize"] = PAGE_SIZE
        print(f"[3DAY_RC] Fetching page {page} (pageSize={PAGE_SIZE})...", flush=True)
        data = fetch_page(url, headers=headers, payload=payload)
        
        if data and data.get("result", {}).get("data", {}).get("json"):
            
            page_json = data["result"]["data"]["json"]
            all_records.extend(page_json)
            print(
                f"[3DAY_RC] Page {page}: {len(page_json)} rows; "
                f"total={len(all_records)}",
                flush=True,
            )
            if len(page_json) < PAGE_SIZE:
                print("[3DAY_RC] Last page reached.", flush=True)
                break
        else:
            print(f"Page {page} has no data, stopping fetch")
            break
        time.sleep(random.uniform(2.0, 3.5))

    if all_records:
        df_all = pd.DataFrame(all_records)
        before = len(df_all)
        if "userId" in df_all.columns:
            df_all = df_all.drop_duplicates(subset="userId")
        after = len(df_all)
        return df_all
    else:
        return pd.DataFrame()


def export_all_pages_3day_rc(headers, poll_attempts=120, wait_seconds=15):
    """Export three complete days of recharge data instead of paging it."""
    start_date = (now_brazil - timedelta(days=3)).strftime("%Y-%m-%d")
    end_date = (now_brazil - timedelta(days=1)).strftime("%Y-%m-%d")
    url_export = f"{BASE_URL}/payRecord.list"
    url_export_list = f"{BASE_URL}/exportData.list"
    url_download = f"{BASE_URL}/exportData.download"

    export_payload = {
        "isRecharge": True,
        "type": "normal",
        "valueType": "phone",
        "regionId": 1,
        "tenantId": TENANT_ID,
        "queryTime": [start_date, end_date],
        "queryData": [],
        "order": [
            {"key": "registerTime", "type": "asc"},
            {"key": "userId", "type": "asc"},
        ],
        "queryType": "export",
        "startTime": start_date,
        "endTime": end_date,
    }
    list_payload = {
        "page": 1,
        # Recharge exports may be deduplicated by the backend. Search a wider
        # history window so an older matching job can be reused.
        "pageSize": 500,
        "regionId": 1,
        "tenantId": TENANT_ID,
        "lastOperator": operator,
    }

    def get_export_list():
        response = client.get(
            url_export_list,
            headers=headers,
            params={"input": json.dumps({"json": list_payload})},
        )
        response.raise_for_status()
        return (
            response.json()
            .get("result", {})
            .get("data", {})
            .get("json", {})
            .get("exportDataList", [])
        )

    def matches(item):
        remark = str(item.get("remark", ""))
        return (
            str(item.get("moduleType", "")) == "UserDayDataMulti"
            and
            str(item.get("lastOperator", "")) == str(operator)
            and start_date in remark
            and end_date in remark
        )

    try:
        existing_items = get_export_list()
        existing_ids = {str(item.get("id")) for item in existing_items}
    except Exception as exc:
        print(f"Could not read existing recharge export jobs: {exc}")
        existing_items = []
        existing_ids = set()

    reusable = [
        item for item in existing_items
        if matches(item)
        and item.get("status") in ("Exporting", "Pending", "Ready", "ExportSuccess")
    ]
    reusable.sort(key=lambda item: item.get("createTime", ""), reverse=True)
    target_id = str(reusable[0]["id"]) if reusable else None

    if target_id:
        print(f"Reusing 3-day recharge export id={target_id}, status={reusable[0].get('status')}")
    else:
        print(f"Triggering 3-day recharge export: {start_date} -> {end_date}")
        response = client.get(
            url_export,
            headers=headers,
            params={"input": json.dumps({"json": export_payload})},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Recharge export request failed ({response.status_code}): {response.text[:2000]}"
            ) from exc

    export_item = None
    for attempt in range(1, poll_attempts + 1):
        time.sleep(wait_seconds)
        try:
            items = get_export_list()
        except Exception as exc:
            print(f"Recharge export poll {attempt}/{poll_attempts} failed: {exc}")
            continue

        candidates = [
            item for item in items
            if matches(item)
            and (
                str(item.get("id")) == target_id
                or (target_id is None and str(item.get("id")) not in existing_ids)
            )
        ]
        candidates.sort(key=lambda item: item.get("createTime", ""), reverse=True)
        if not candidates:
            print(f"Recharge export poll {attempt}/{poll_attempts}: waiting for matching job...")
            continue

        latest = candidates[0]
        status = latest.get("status")
        print(
            f"Recharge export poll {attempt}/{poll_attempts}: "
            f"id={latest.get('id')} module={latest.get('moduleType')} status={status}"
        )
        if status in ("ExportSuccess", "Completed", "Finished", "已完成"):
            export_item = latest
            break
        if status not in ("Exporting", "Pending", "Ready", "处理中", None):
            raise RuntimeError(f"Recharge export failed with status: {status}")

    if not export_item:
        raise RuntimeError("Recharge export did not finish before timeout")

    response = client.post(
        url_download,
        headers=headers,
        json={"json": {"tenantId": TENANT_ID, "id": export_item["id"]}},
    )
    response.raise_for_status()
    file_url = response.json()["result"]["data"]["json"]["filePath"]
    file_response = client.get(file_url)
    file_response.raise_for_status()

    content_type = file_response.headers.get("content-type", "").lower()
    if file_url.lower().endswith((".xlsx", ".xls")) or "spreadsheet" in content_type:
        df_export = pd.read_excel(BytesIO(file_response.content), dtype=str)
    else:
        df_export = pd.read_csv(
            StringIO(file_response.text.lstrip("\ufeff")), dtype=str, low_memory=False
        )

    required_columns = ["会员id", "累计充值"]
    missing_columns = [col for col in required_columns if col not in df_export.columns]
    if missing_columns:
        raise RuntimeError(
            f"Recharge export is missing columns {missing_columns}: "
            + ", ".join(map(str, df_export.columns))
        )

    # Keep the original Chinese export schema for CSV/debugging.
    df_export["会员id"] = df_export["会员id"].astype(str).str.strip()
    df_export["累计充值"] = pd.to_numeric(
        df_export["累计充值"], errors="coerce"
    ).fillna(0)
    df_export = df_export[df_export["会员id"] != ""]
    return df_export.drop_duplicates(subset="会员id", keep="last")





def build_summary_message(df_send, df_history_today, current_time):
    batch_count = len(df_send)
    batch_amount = pd.to_numeric(
        df_send["彩金"], errors="coerce"
    ).fillna(0).sum()

    history_count = len(df_history_today)
    if "彩金" in df_history_today.columns:
        history_amount = pd.to_numeric(
            df_history_today["彩金"], errors="coerce"
        ).fillna(0).sum()
    else:
        history_amount = 0

    total_count = history_count + batch_count
    total_amount = history_amount + batch_amount
    return (
        f"WZ2 时间派送：{current_time}\n"
        f"本次数量：{batch_count}\n"
        f"本次金额：{batch_amount:.2f}\n\n"
        f"总派送数量：{total_count}\n"
        f"总派送金额：{total_amount:.2f}"
    )


def parse_remark(remark: str):
    start_match = re.search(
        r"(?:开始时间|开始统计时间)[:：](\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
        remark
    )
    end_match = re.search(
        r"(?:结束时间|结束统计时间)[:：](\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
        remark
    )

    if not (start_match and end_match):
        return None, None

    return (
        datetime.strptime(start_match.group(1), "%Y-%m-%d %H:%M:%S"),
        datetime.strptime(end_match.group(1), "%Y-%m-%d %H:%M:%S")
    )


def export_and_download(mode="unclaimed"):
    update_times()
    if mode not in ("wz1", "unclaimed"):
        raise ValueError(f"Unsupported reward export mode: {mode}")

    print(f"Running export_and_download(mode={mode})...")
    empty_result = pd.DataFrame(columns=["会员id", "备注"])

    if mode == "wz1":
        time_starts = api_start_today
        expected_start_text = f"{now_date_str} 00:00:00"
    else:
        time_starts = "2026-07-06T03:00:00.000Z"
        expected_start_text = "2026-07-06 00:00:00"

    # 1. Trigger export job
    payload = {
        "json": {
            "type": "normal",
            "regionId": 1,
            "tenantId": TENANT_ID,
            "timeStarts": time_starts,
            "timeEnd": api_end_today,
            "page": 1,
            "pageSize": 50,
            "order": [{"key": "operationTime", "type": "desc"}],
            "operationType": "manual_reward",
            "queryType": "export"
        }
    }
    if mode == "unclaimed":
        payload["json"]["receiveStatus"] = "notReceived"
    url_trigger = f"{BASE_URL}/manualPageData.list"

    try:
        r1 = client.get(url_trigger, headers=HEADERS, params={"input": json.dumps(payload)})
        r1.raise_for_status()
        print("Export job triggered successfully")
    except Exception as e:
        print(f"Failed to trigger export: {e}")
        return empty_result.copy()

    # 2. Poll for export completion
    export_id = None
    payload_poll = {
        "json": {
            "page": 1,
            "pageSize": 50,
            "regionId": 1,
            "tenantId": TENANT_ID,
            "lastOperator": operator
        }
    }
    url_poll = f"{BASE_URL}/exportData.list"

    for attempt in range(30):
        try:
            time.sleep(30)
            r2 = client.get(url_poll, headers=HEADERS, params={"input": json.dumps(payload_poll)})
            r2.raise_for_status()
            data = r2.json()
        except Exception as e:
            print(f"Polling attempt {attempt+1} failed: {e}")
            time.sleep(10)
            continue

        export_list = (
            data.get("result", {})
                .get("data", {})
                .get("json", {})
                .get("exportDataList", [])
        )

        matching_exports = []
        expected_start = datetime.strptime(
            expected_start_text, "%Y-%m-%d %H:%M:%S"
        )
        expected_end = datetime.strptime(
            f"{now_date_str} 23:59:59", "%Y-%m-%d %H:%M:%S"
        )
        for item in export_list:
            if item.get("moduleType") != "manualRewardRecords":
                continue
            if str(item.get("lastOperator", "")) != str(operator):
                continue

            remark = str(item.get("remark", ""))
            if mode == "unclaimed" and "领取状态:未领取" not in remark:
                continue
            export_start_time, export_end_time = parse_remark(remark)
            if not export_start_time or not export_end_time:
                continue
            if (
                abs((export_start_time - expected_start).total_seconds()) < 60
                and abs((export_end_time - expected_end).total_seconds()) < 60
            ):
                matching_exports.append(item)

        export_list = matching_exports

        if not export_list:
            print(f"Attempt {attempt+1}/30: no export found yet, waiting 20s...")
            time.sleep(20)
            continue

        export_list.sort(key=lambda x: x.get("createTime", ""), reverse=True)
        latest_item = export_list[0]
        status = latest_item.get("status")

        if status == "Exporting":
            print(f"Attempt {attempt+1}/30: export is still exporting, waiting 20s...")
            time.sleep(20)
            continue
        elif status == "ExportSuccess":
            export_id = latest_item["id"]
            print(
                f"Matched export_id: {export_id} "
                f"(downloadCount={latest_item.get('downloadCount', 0)})"
            )
            break

    if not export_id:
        print("Export ID not found after polling 30 times.")
        return empty_result.copy()

    # 3. Download exported file
    payload_download = {"json": {"tenantId": TENANT_ID, "id": export_id}}
    url_get_link = f"{BASE_URL}/exportData.download"

    try:
        r3 = client.post(url_get_link, headers=HEADERS, json=payload_download)
        r3.raise_for_status()
        file_url = r3.json()["result"]["data"]["json"]["filePath"]
        print(f"File ready at {file_url}")
    except Exception as e:
        print(f"Failed to get reward export download link: {e}")
        return empty_result.copy()

    try:
        r4 = client.get(file_url)
        r4.raise_for_status()
        df = pd.read_csv(StringIO(r4.text.lstrip("\ufeff")), dtype=str, low_memory=False)
        required_columns = ["会员id", "备注"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"Reward export missing columns: {missing_columns}")
            return pd.DataFrame(columns=required_columns)

        if mode == "unclaimed":
            df["会员id"] = df["会员id"].astype(str).str.strip()
            df = df[df["会员id"] != ""].copy()
            unclaimed_path = os.path.join(
                send_folder, f"df_sent_未领取_{now_date_str}.xlsx"
            )
            df.to_excel(unclaimed_path, index=False)
            print(
                f"Downloaded and saved {len(df)} 未领取 rows to {unclaimed_path}."
            )
            return df

        df_wz1 = df[required_columns].copy()
        df_wz1["会员id"] = df_wz1["会员id"].astype(str).str.strip()
        df_wz1["备注"] = df_wz1["备注"].astype(str).str.strip()
        df_wz1 = df_wz1[
            (df_wz1["会员id"] != "") &
            (df_wz1["备注"].str.upper().str.endswith("WZ1"))
        ].copy()

        wz1_path = os.path.join(send_folder, f"df_sent_WZ1_{now_date_str}.xlsx")
        df_wz1.to_excel(wz1_path, index=False)
        print(
            f"Downloaded {len(df)} reward rows; "
            f"saved {len(df_wz1)} WZ1 rows to {wz1_path}."
        )
        return df_wz1
    except Exception as e:
        print(f"Failed to process reward export: {e}")
        return empty_result.copy()


# ---------------- Process file ----------------
def process_file(df_main, df_raw, df_sent, info, headers, df_wz1=None):
    global multiplier, multiplier_2, expire_time, bonus_map, bonus_key

    update_times()

    print("\n========== START process_file ==========")

    # ---------------- Config ----------------
    with open("config_setting.json", "r", encoding="utf-8-sig") as f:
        cfg_local = json.load(f)

    app_title    = cfg_local.get("app_title", "")
    multiplier   = int(cfg_local.get("jiabei", 1))
    multiplier_2 = int(cfg_local.get("beishu_2", 5))
    expire_time  = int(cfg_local.get("exp_time", 1))

    bonus_key    = cfg_local.get("key_bn", "on")
    dama_key     = cfg_local.get("key_dama", "on")

    bonus_map    = cfg_local.get("bonus_map", {})
    dama_map     = cfg_local.get("beishu_map", {})
    fixed_bonus  = float(cfg_local.get("bonus", 0))

    test_local = str(cfg_local.get("test_local", "off")).strip().lower() == "on"
    if test_local:
        print("[TEST_LOCAL] Test mode enabled: Telegram, rewards and batch update are disabled.")

    black_level = [
        "洗水套利",
        "测试层级",
        "黑名单",
        "无优惠",
        "观察层级",
        "CUSTOMIZE_NO_DISCOUNT"
    ]

    # ---------------- Helpers ----------------
    def parse_level(x):
        if not x:
            return ""
        if isinstance(x, str):
            try:
                parsed = ast.literal_eval(x)
                return parsed.get("name", "") if isinstance(parsed, dict) else x
            except Exception:
                # Exported UserList files contain the level name directly.
                return x.strip()
        if isinstance(x, dict):
            return x.get("name", "")
        return ""

    def safe_read_history(path):
        columns = [
            "会员id",
            "彩金",
            "打码倍数",
            "App备注",
            "后台备注",
            "time_send",
            "receive_no"
        ]

        if not os.path.exists(path):
            print("[HISTORY] old_list_data.xlsx does not exist.")
            return pd.DataFrame(columns=columns)

        try:
            df_h = pd.read_excel(path)
            print(f"[HISTORY] Loaded history rows: {len(df_h)}")

            for col in columns:
                if col not in df_h.columns:
                    df_h[col] = None

            return df_h
        except Exception:
            try:
                bad_path = path + f".bad_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(path, bad_path)
                print(f"[HISTORY] Bad history file renamed to: {bad_path}")
            except Exception as rename_err:
                print(f"[HISTORY] Could not rename bad history file: {rename_err}")

            return pd.DataFrame(columns=columns)

    def make_count_map(df, id_col="会员id"):
        if df is None or df.empty or id_col not in df.columns:
            return pd.Series(dtype=int)

        temp = df.copy()
        temp[id_col] = temp[id_col].astype(str).str.strip()
        temp = temp[temp[id_col] != ""]

        if temp.empty:
            return pd.Series(dtype=int)

        return temp.groupby(id_col).size()

    # ---------------- Validate input ----------------
    if df_main is None or df_main.empty:
        print("[STOP] df_main is empty.")
        return pd.DataFrame()

    if df_raw is None or df_raw.empty:
        print("[STOP] df_raw / FRC data is empty.")
        return pd.DataFrame()

    if df_sent is None:
        df_sent = pd.DataFrame()
    if df_wz1 is None:
        df_wz1 = pd.DataFrame(columns=["会员id", "备注"])

    print(f"[RAW] main={len(df_main)} raw={len(df_raw)} sent={len(df_sent)}")

    # ---------------- Prepare df_main ----------------
    required_main_cols = [
        "会员id",
        "历史充值",
        "历史提现",
        "会员层级",
        "登录类型",
        "余额",
    ]

    missing_main_cols = [c for c in required_main_cols if c not in df_main.columns]
    if missing_main_cols:
        print("[STOP] df_main missing columns:", missing_main_cols)
        return pd.DataFrame()

    df_main = df_main[required_main_cols].copy()

    df_main["会员id"] = df_main["会员id"].astype(str).str.strip()

    for col in ["历史充值", "历史提现", "余额"]:
        df_main[col] = pd.to_numeric(df_main[col], errors="coerce").fillna(0)

    df_main["充提差"] = (
        df_main["历史充值"] - (df_main["历史提现"] + df_main["余额"])
    ).round(0).astype(int)

    print("[MAIN] after prepare:", len(df_main))

    #df_main.to_csv(os.path.join(send_folder, f"df_main_prepared_{hf_time_str}.csv"), index=False, encoding="utf-8-sig")

    # ---------------- Remove every currently unclaimed member ----------------
    if not df_sent.empty and "会员id" in df_sent.columns:
        df_sent = df_sent.copy()
        df_sent["会员id"] = df_sent["会员id"].astype(str).str.strip()
        df_sent = df_sent[df_sent["会员id"] != ""]
        unclaimed_ids = set(df_sent["会员id"])
        df_main = df_main[~df_main["会员id"].isin(unclaimed_ids)].copy()
    else:
        df_sent = pd.DataFrame(columns=["会员id", "备注"])
        unclaimed_ids = set()

    print(f"[SENT] 未领取 member IDs removed from df_main: {len(unclaimed_ids)}")

    # WZ1 records are counted toward the daily limit but do not block outright.
    if not df_wz1.empty and "会员id" in df_wz1.columns:
        df_wz1 = df_wz1.copy()
        df_wz1["会员id"] = df_wz1["会员id"].astype(str).str.strip()
        df_wz1 = df_wz1[df_wz1["会员id"] != ""]
    else:
        df_wz1 = pd.DataFrame(columns=["会员id", "备注"])

    backend_count_map = make_count_map(df_wz1, "会员id")
    print(f"[SENT] WZ1 rows used for daily count: {len(df_wz1)}")

    # ---------------- Prepare history ----------------
    history_path = os.path.join(send_folder, "old_list_data.xlsx")

    df_history = safe_read_history(history_path)

    # Each member may be sent at most 5 times per Brazil calendar day.
    if not df_history.empty:
        df_history["会员id"] = df_history["会员id"].astype(str).str.strip()
        history_dates = df_history["time_send"].astype(str).str[:10]
        df_history_today = df_history[history_dates == now_date_str].copy()
    else:
        df_history_today = pd.DataFrame(columns=df_history.columns)

    history_count_map = make_count_map(df_history_today, "会员id")
    all_count_ids = set(backend_count_map.index).union(history_count_map.index)
    daily_count_map = pd.Series(
        {
            member_id: (
                int(backend_count_map.get(member_id, 0))
                + int(history_count_map.get(member_id, 0))
            )
            for member_id in all_count_ids
        },
        dtype=int,
    )
    df_main["today_send_count"] = (
        df_main["会员id"].map(daily_count_map).fillna(0).astype(int)
    )
    blocked_by_history = int((df_main["today_send_count"] >= 5).sum())
    df_main = df_main[df_main["today_send_count"] < 5].copy()
    df_main["receive_no"] = df_main["today_send_count"] + 1
    print(f"[HISTORY] IDs blocked at daily limit 5: {blocked_by_history}")

    # ---------------- Prepare FRC df_raw ----------------
    required_frc_cols = ["会员id", "累计充值"]
    missing_frc_cols = [c for c in required_frc_cols if c not in df_raw.columns]


    if missing_frc_cols:
        print("[STOP] df_raw missing columns:", missing_frc_cols)
        return df_main

    df_3days_rc = df_raw[required_frc_cols].copy()
    df_3days_rc = df_3days_rc.dropna(subset=["会员id"])
    df_3days_rc["会员id"] = df_3days_rc["会员id"].astype(str).str.strip()
    df_3days_rc["累计充值"] = pd.to_numeric(
        df_3days_rc["累计充值"], errors="coerce"
    ).fillna(0)
    df_3days_rc.rename(columns={"累计充值": "3天充值金额"}, inplace=True)

    df_main = df_main.merge(
        df_3days_rc[["会员id", "3天充值金额"]],
        how="left",
        left_on="会员id",
        right_on="会员id"
    )





    # ---------------- Main filters ----------------
    cond_level = ~df_main["会员层级"].isin(black_level)
    cond_type = df_main["登录类型"] != "DesktopOS"
    #cond_diff = df_main["充提差"] > 0
    cond_3day_recharge = (
        pd.to_numeric(df_main["3天充值金额"], errors="coerce").fillna(0) >= 20
    )


    print("\n========== FILTER DEBUG ==========")
    print("Total df_main:", len(df_main))


    df_filtered = df_main[
        cond_level &
        cond_type &
        #cond_diff &
        cond_3day_recharge

    ].copy()


    # ---------------- Create df_send ----------------
    send_cols = [
        "会员id", "3天充值金额", "历史充值", "历史提现",
        "余额", "充提差", "receive_no"
    ]

    if df_filtered.empty:
        df_send = pd.DataFrame(columns=[
            "会员id",
            "3天充值金额",
            "历史充值",
            "历史提现",
            "余额",
            "充提差",
            "receive_no",
            "彩金",
            "打码倍数",
            "App备注",
            "后台备注",
            "time_send"
        ])
    else:
        df_send = df_filtered[send_cols].copy()

        df_send["3天充值金额"] = pd.to_numeric(
            df_send["3天充值金额"],
            errors="coerce"
        ).fillna(0).round(0).astype(int)

        if bonus_key == "on":
            cond_positive_diff = (
                pd.to_numeric(df_send["充提差"], errors="coerce").fillna(0) > 0
            )
            df_send["彩金"] = 0.5
            df_send.loc[cond_positive_diff, "彩金"] = (
                df_send.loc[cond_positive_diff, "3天充值金额"]
                .apply(lambda x: map_bonus(x, bonus_map))
            )
        else:
            df_send["彩金"] = fixed_bonus

        if dama_key == "on":
            df_send["打码倍数"] = df_send["3天充值金额"].apply(lambda x: map_bonus(x, dama_map))
        else:
            df_send["打码倍数"] = 5

        df_send["App备注"] = app_title

        # Không đổi beizhu, tất cả đều CK0
        df_send["后台备注"] = f"{date_tag}-WZ2"

        df_send["彩金"] = pd.to_numeric(
            df_send["彩金"],
            errors="coerce"
        ).fillna(0).round(1)

        df_send["time_send"] = send_time_str


    if not df_send.empty:
        print("df_send bonus total:", df_send["彩金"].astype(float).sum())


    # ---------------- Save preview ----------------
    preview_path = None

    if not df_send.empty:
        # Mở dòng dưới nếu muốn xuất preview
        #preview_path = os.path.join(send_folder, f"76B_preview_{hf_time_str}.xlsx")

        try:
            if preview_path:
                df_send.to_excel(preview_path, index=False)
                print(f"[PREVIEW] saved: {preview_path}")
        except Exception as e:
            print(f"Error saving preview file: {e}")


    # ---------------- Stop if no data ----------------
    if df_send.empty:
        print(f"Processed {len(df_main)} users.")
        print("========== END process_file ==========\n")
        return df_main

    # ---------------- Send Telegram + Rewards ----------------
    total_s = len(df_send)
    message = build_summary_message(df_send, df_history_today, send_time_str)

    if test_local:
        print("[TEST_LOCAL] Telegram/API actions are disabled.")
        print(message)

        if preview_path and os.path.exists(preview_path):
            print(f"[TEST_LOCAL] Preview file: {preview_path}")

        print(f"Processed {len(df_main)} users.")
        print("========== END process_file ==========\n")
        return df_main

    try:
        time.sleep(0.3)
        send_telegram_message(text=message)
    except Exception as e:
        print("[TELEGRAM] Error sending message:", e)

    # ---------------- Send rewards ----------------
    reward_sent_ok = False

    try:
        time.sleep(0.5)

        df_send_api = df_send.copy()
        df_send_api["会员id"] = pd.to_numeric(
            df_send_api["会员id"],
            errors="coerce"
        )

        df_send_api = df_send_api.dropna(subset=["会员id"]).copy()
        df_send_api["会员id"] = df_send_api["会员id"].astype(int)

        if df_send_api.empty:
            print("[API] df_send_api empty after converting member id to int. Skip send_rewards.")
        else:
            reward_sent_ok = send_rewards(df_send_api, info, headers) is True

    except Exception as e:
        print("[API] Error in send_rewards:", e)

    # ---------------- Update batch ----------------
    updated_batch = None

    if reward_sent_ok:
        try:
            time.sleep(20)
            updated_batch = fetch_and_update_batch(headers, TENANT_ID, operator, total_s)
        except Exception:
            updated_batch = None

    # ---------------- Save history only after batch update success ----------------
    if updated_batch:
        try:
            df_history_save = pd.concat([df_history, df_send], ignore_index=True)
            df_history_save.to_excel(history_path, index=False)

            print(f"[HISTORY] Saved {len(df_send)} users to history after batch update success.")
        except Exception as e:
            print("[HISTORY] Error saving history:", e)
    else:
        print("[HISTORY] Batch update failed or skipped; history not updated.")

    print(f"Processed {len(df_main)} users.")
    print("========== END process_file ==========\n")
    return df_main

# ---------------- Rewards ----------------
def send_rewards(df_send, info, headers):
    global batch_start_time, batch_end_time, notify_dict, multiplier

    if df_send is None or df_send.empty:
        print("[REWARDS] No users to send.")
        return None

    # Load config
    with open("config_setting.json", "r", encoding="utf-8-sig") as f:
        cfg = json.load(f)

    level_list = cfg.get("cengji", {})
    url = f"{BASE_URL}/batch.createBatchDiff"

    df_send = df_send.copy()

    # =========================
    # FIX AMOUNT TO CENTS
    # =========================
    df_send["彩金"] = (pd.to_numeric(df_send["彩金"], errors="coerce").fillna(0) * 100).astype(int)

    reward_infos = []

    for _, row in df_send.iterrows():
        try:
            reward_infos.append({
                "userId": int(float(row["会员id"])),
                "amount": int(row["彩金"]),
                "needMultiple": int(row.get("打码倍数", multiplier)),
                "remark": str(row.get("后台备注", "")),
                "appRemark": str(row.get("App备注", ""))
            })
        except Exception as e:
            print(f"[REWARDS] Skip row error: {e}")
            continue

    if not reward_infos:
        print("[REWARDS] No valid reward rows after parsing.")
        return None

    payload = {
        "json": {
            "tenantId": TENANT_ID,
            "status": "ready",
            "batchDiffInfo": {
                "type": "UserReward",
                "infos": reward_infos,
                "levelIdList": level_list
            }
        }
    }

    print(f"[REWARDS] Sending {len(reward_infos)} users...")

    try:
        batch_start_time = datetime.now(BRAZIL_TZ).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

        resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()

        # =========================
        # SAFE RESPONSE PARSE
        # =========================
        raw = resp.text.lstrip("\ufeff")
        print("[REWARDS] Response:", raw[:300])

        batch_end_time = datetime.now(BRAZIL_TZ).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.999Z")

        try:
            result = json.loads(raw)
        except:
            result = None

        print(f"[REWARDS] Sent OK: {len(reward_infos)} users")

    except Exception as e:
        print(f"[REWARDS] Error sending rewards: {e}")
        return None

    # =========================
    # UPDATE NOTIFY
    # =========================
    total_users = len(reward_infos)
    total_amount = sum(i["amount"] for i in reward_infos) / 100.0

    notify_dict.update({
        "total_users": total_users,
        "total_amount": total_amount
    })

    return True

def fetch_and_update_batch(headers, tenant_id=TENANT_ID, operator=None, total_users=None, max_retries=6, wait_seconds=10):
    headers = {k: str(v) for k, v in headers.items()}
    url = f"{BASE_URL}/batch.list"

    payload_list = {
        "json": {
            "batchType": "UserReward",
            "tenantId": tenant_id,
            "page": 1,
            "pageSize": 50,
            "createStartTime": api_start_today,
            "createEndTime":   api_end_today
        }
    }

    with open("config_setting.json", "r", encoding="utf-8-sig") as f:
        cfg_local = json.load(f)

    double_recharge_config = [
        {
            "rechargeDoubleMultiplier": item["rechargeDoubleMultiplier"] * 100,
            "rechargeAmount":           item["rechargeAmount"] * 100
        }
        for item in cfg_local.get("rc_jiabei", [])
    ]

    for attempt in range(1, max_retries + 1):
        try:
            resp = client.get(url, params={"input": json.dumps(payload_list)}, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            batch_list = data.get("result", {}).get("data", {}).get("json", {}).get("batchInfoList", [])


            for b in batch_list[:10]:
                print({
                    "batchNo":       b.get("batchNo"),
                    "status":        b.get("status"),
                    "operationName": b.get("operationName"),
                    "total":         b.get("total"),
                    "createTime":    b.get("createTime"),
                })

            if not batch_list:
                print(f"Attempt {attempt}: no batch found, retry after {wait_seconds}s")
                time.sleep(wait_seconds)
                continue

            matched_batches = [
                b for b in batch_list
                if b.get("operationName") == str(operator)
            ]

            if not matched_batches:
                print(f"Attempt {attempt}: no operator match, retry after {wait_seconds}s")
                time.sleep(wait_seconds)
                continue

            latest_batch = sorted(matched_batches, key=lambda x: x.get("createTime", ""), reverse=True)[0]
            if update_batch(headers, latest_batch["batchNo"], double_recharge_config):
                return latest_batch
            print(f"Attempt {attempt}: batch update failed, retry after {wait_seconds}s")
            time.sleep(wait_seconds)

        except Exception as e:
            print(f"Error fetching batch list attempt {attempt}: {e}")
            time.sleep(wait_seconds)

    print("No valid batch found after all retries")
    return None



def update_batch(headers, batch_no, recharge_config):
    with open("config_setting.json", "r", encoding="utf-8-sig") as f:
        cfg = json.load(f)

    jiabei = int(cfg.get("jiabei", 2))
    recharge_config = [
        {
            "rechargeDoubleMultiplier": item["rechargeDoubleMultiplier"] * 100,
            "rechargeAmount": item["rechargeAmount"] * 100
        } for item in cfg.get("rc_jiabei", [])
    ]
        
    
    multiple_code = jiabei * 100
    extime = int(cfg.get("exp_time", 1))
    url = f"{BASE_URL}/batch.update"
    

    # Payload cơ bản

    payload = {
        "json": {
            "batchNo": batch_no,
            "doubleAuditMultiple": 1,
            "doubleMultiplier": multiple_code,
            "doubleType": "FIXED",
            "expireTime": extime,
            "isOpenDouble": True,
            "receiveType": "manual",
            "status": "running",
            "tenantId": TENANT_ID
        }
    }


    print(f"--- Updating batch {batch_no} ---")
    print("Request URL:", url)
    print("Payload being sent:")
    print(json.dumps(payload, indent=4, ensure_ascii=True))
    print("-------------------------------")

    try:
        resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        print(f"Batch {batch_no} updated to running.")
        return True
    except Exception as e:
        print(f"Error updating batch {batch_no}: {e}")
        return False


def send_mail_to_users_sync(headers, df_send):
    with open("config_setting.json", "r", encoding="utf-8-sig") as f:
        cfg = json.load(f)

    mail_content_url = cfg["mail_seting"].get("content", "")
    mail_signature   = cfg["mail_seting"].get("signature")
    mail_title       = cfg["mail_seting"].get("title")

    if df_send.empty:
        print("No users to send mail")
        return

    user_ids = df_send["会员id"].astype(int).tolist()
    url = f"{BASE_URL}/mail.send"

    payload = {
        "json": {
            "content":       mail_content_url,
            "operationType": "users",
            "regionId":      1,
            "signature":     mail_signature,
            "tenantId":      TENANT_ID,
            "title":         mail_title,
            "userIds":       user_ids
        }
    }

    try:
        with httpx.Client(timeout=30) as client_local:
            resp = client_local.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            print(f"Mail sent to {len(user_ids)} users, status code: {resp.status_code}")
            try:
                print("Response JSON:", resp.json())
            except Exception:
                print("Response Text:", resp.text)
    except Exception as e:
        print(f"Error sending mail: {e}")


def run_fetch():
    info = {}
    update_times()

    # First export: today's WZ1 records, used for the daily count.
    df_wz1 = export_and_download(mode="wz1")
    print(f"Today's WZ1 reward rows: {len(df_wz1)}")

    # Second export: all currently unclaimed records, used to block members.
    df_sent = export_and_download(mode="unclaimed")
    print(f"Current 未领取 reward rows: {len(df_sent)}")

    df_main = export_all_pages_main(HEADERS)
    #df_main.to_csv("userDay_main.csv", index=False)


    df_raw = export_all_pages_3day_rc(HEADERS)
    #df_raw.to_csv("userDay_3day_rc.csv", index=False)
    process_file(df_main, df_raw, df_sent, info, HEADERS, df_wz1=df_wz1)


# ---------------- Telegram Bot Commands ----------------
running_event = threading.Event()
running_event.set()


def is_authorized(update: Update) -> bool:
    try:
        with open("config_setting.json", "r", encoding="utf-8-sig") as f:
            authorized_ids = json.load(f).get("bot_stt", {}).get("AUTHORIZED_IDS", [])
    except (OSError, json.JSONDecodeError):
        authorized_ids = cfg.get("bot_stt", {}).get("AUTHORIZED_IDS", [])
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    return (user_id in authorized_ids) or (chat_id in authorized_ids)


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("🚫 You have no permission.")
        return
    running_event.set()
    await update.message.reply_text("✅ bot starting.")


async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("🚫 You have no permission.")
        return
    running_event.clear()
    await update.message.reply_text("⛔ Program paused.")


async def settime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("🚫 you have no permision.")
        return
    global interval_minutes
    try:
        minutes = int(context.args[0])
        interval_minutes = max(1, minutes)
        await update.message.reply_text(f"⏰ set time: {interval_minutes} minutes.")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ wrong command. Use: /settime <minutes>")


async def content_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("🚫 you have no permision.")
        return
    if not context.args:
        await update.message.reply_text("❌ use: /content <link>")
        return
    new_link = context.args[0]
    try:
        with open("config_setting.json", "r", encoding="utf-8-sig") as f:
            cfg_local = json.load(f)
        cfg_local["mail_seting"]["content"] = new_link
        with open("config_setting.json", "w", encoding="utf-8-sig") as f:
            json.dump(cfg_local, f, ensure_ascii=False, indent=4)
        await update.message.reply_text(f"📩 updated link content:\n{new_link}")
    except Exception as e:
        await update.message.reply_text(f"update link error: {e}")


async def key_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global HEADERS
    if not is_authorized(update):
        await update.message.reply_text("🚫 you have no permision.")
        return
    if not context.args:
        await update.message.reply_text("❌ use: /key <token>")
        return
    new_token = context.args[0]
    try:
        with open("config_setting.json", "r", encoding="utf-8-sig") as f:
            cfg_local = json.load(f)
        cfg_local["headers"]["authorization"] = new_token
        with open("config_setting.json", "w", encoding="utf-8-sig") as f:
            json.dump(cfg_local, f, ensure_ascii=False, indent=4)
        HEADERS = cfg_local["headers"].copy()
        await update.message.reply_text("🔑 updated Authorization Token successfully.")
    except Exception as e:
        await update.message.reply_text(f"error update token: {e}")


async def bonus_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("🚫 you have no permision.")
        return
    if not context.args:
        await update.message.reply_text("❌ use: /bonus <bonus>")
        return
    try:
        new_bonus = float(context.args[0])
        with open("config_setting.json", "r", encoding="utf-8-sig") as f:
            cfg_local = json.load(f)
        cfg_local["bonus"] = new_bonus
        with open("config_setting.json", "w", encoding="utf-8-sig") as f:
            json.dump(cfg_local, f, ensure_ascii=False, indent=4)
        await update.message.reply_text("updated bonus successfully.")
    except Exception as e:
        await update.message.reply_text(f"error update bonus: {e}")


async def title_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("🚫 you have no permision.")
        return
    if not context.args:
        await update.message.reply_text("❌ use: /title <title>")
        return
    new_title = " ".join(context.args)
    try:
        with open("config_setting.json", "r", encoding="utf-8-sig") as f:
            cfg_local = json.load(f)
        cfg_local["mail_seting"]["title"] = new_title
        with open("config_setting.json", "w", encoding="utf-8-sig") as f:
            json.dump(cfg_local, f, ensure_ascii=False, indent=4)
        await update.message.reply_text("updated title successfully.")
    except Exception as e:
        await update.message.reply_text(f"error update title: {e}")


async def jiabei_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("🚫 you have no permision.")
        return
    if not context.args:
        await update.message.reply_text("❌ use: /jiabei <jiabei>")
        return
    try:
        new_jiabei = int(context.args[0])
        with open("config_setting.json", "r", encoding="utf-8-sig") as f:
            cfg_local = json.load(f)
        cfg_local["jiabei"] = new_jiabei
        with open("config_setting.json", "w", encoding="utf-8-sig") as f:
            json.dump(cfg_local, f, ensure_ascii=False, indent=4)
        await update.message.reply_text("updated jiabei successfully.")
    except Exception as e:
        await update.message.reply_text(f"error update jiabei: {e}")


async def app_title_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("🚫 you have no permision.")
        return
    if not context.args:
        await update.message.reply_text("❌ use: /app_title <title>")
        return
    new_app_title = " ".join(context.args)
    try:
        with open("config_setting.json", "r", encoding="utf-8-sig") as f:
            cfg_local = json.load(f)
        cfg_local["app_title"] = new_app_title
        with open("config_setting.json", "w", encoding="utf-8-sig") as f:
            json.dump(cfg_local, f, ensure_ascii=False, indent=4)
        await update.message.reply_text("updated app_title successfully.")
    except Exception as e:
        await update.message.reply_text(f"error update app_title: {e}")


async def add_admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        await update.message.reply_text("🚫 You have no permission.")
        return
    if not context.args:
        await update.message.reply_text("❌ Use: /add_admin <admin_id>")
        return
    try:
        new_admin_id = int(context.args[0])
        with open("config_setting.json", "r", encoding="utf-8-sig") as f:
            cfg_local = json.load(f)
        if new_admin_id not in cfg_local["bot_stt"]["AUTHORIZED_IDS"]:
            cfg_local["bot_stt"]["AUTHORIZED_IDS"].append(new_admin_id)
            with open("config_setting.json", "w", encoding="utf-8-sig") as f:
                json.dump(cfg_local, f, ensure_ascii=False, indent=4)
            await update.message.reply_text(f"✅ Added new admin: {new_admin_id}")
        else:
            await update.message.reply_text(f"ℹ️ Admin {new_admin_id} already exists.")
    except ValueError:
        await update.message.reply_text("❌ Invalid ID format, must be a number.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error adding admin: {e}")


async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"👤 user_id = {user_id}\n💬 chat_id = {chat_id}")


def register_bot_commands(application):
    application.add_handler(CommandHandler("start",     start_cmd))
    application.add_handler(CommandHandler("stop",      stop_cmd))
    application.add_handler(CommandHandler("settime",   settime_cmd))
    application.add_handler(CommandHandler("content",   content_cmd))
    application.add_handler(CommandHandler("key",       key_cmd))
    application.add_handler(CommandHandler("bonus",     bonus_cmd))
    application.add_handler(CommandHandler("title",     title_cmd))
    application.add_handler(CommandHandler("jiabei",    jiabei_cmd))
    application.add_handler(CommandHandler("app_title", app_title_cmd))
    application.add_handler(CommandHandler("id",        id_cmd))
    application.add_handler(CommandHandler("add_admin", add_admin_cmd))


running_event = threading.Event()
running_event.set()
interval_minutes = 25

def schedule_daily_file_deletion():

    file_to_delete = os.path.join(send_folder, "old_list_data.xlsx")
    
    while True:
        try:
            # Get current time in brazil timezone
            now_brazil = datetime.now(BRAZIL_TZ)  # 
            
            # Calculate next midnight + 5 minutes in brazil time
            next_midnight = now_brazil.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            next_deletion_time = next_midnight + timedelta(minutes=5)
            
            # Calculate seconds to wait
            time_diff = next_deletion_time - now_brazil
            seconds_to_wait = time_diff.total_seconds()
            
            print(f"[FILE_DELETION] Next file deletion scheduled for: {next_deletion_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print(f"[FILE_DELETION] Waiting {seconds_to_wait:.0f} seconds (~{seconds_to_wait/3600:.2f} hours)")
            
            # Sleep until deletion time
            time.sleep(seconds_to_wait)
            
            # Try to delete the file
            if os.path.exists(file_to_delete):
                try:
                    os.remove(file_to_delete)
                    print(f"[FILE_DELETION] ✅ Successfully deleted: {file_to_delete}")
                except Exception as e:
                    print(f"[FILE_DELETION] ❌ Error deleting {file_to_delete}: {e}")
            else:
                print(f"[FILE_DELETION] ℹ️ File does not exist: {file_to_delete}")
                
        except Exception as e:
            print(f"[FILE_DELETION] ⚠️ Error in schedule_daily_file_deletion: {e}")
            time.sleep(60)  # Wait 1 minute before retrying

RUN_HOURS_BRAZIL = set(range(12, 22))


def get_scheduled_target_hour(current_brazil):
    """Return the target hour, opening each run window 5 minutes early."""
    target_hour = current_brazil.hour + (1 if current_brazil.minute >= 55 else 0)
    return target_hour if target_hour in RUN_HOURS_BRAZIL else None


def delete_old_list_after_final_run():
    history_path = Path(send_folder) / "old_list_data.xlsx"
    try:
        if history_path.exists():
            history_path.unlink()
            print(f"[HISTORY] Deleted after 21:00 run: {history_path}")
        else:
            print(f"[HISTORY] Nothing to delete after 21:00 run: {history_path}")
    except OSError as exc:
        print(f"[HISTORY] Failed to delete {history_path}: {exc}")


def main_loop():
    last_run_key = None
    stopped_message_shown = False

    try:
        with open("config_setting.json", "r", encoding="utf-8-sig") as f:
            startup_cfg = json.load(f)
        test_local_enabled = (
            str(startup_cfg.get("test_local", "off")).strip().lower() == "on"
        )
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[SCHEDULE] Could not read test_local setting: {exc}")
        test_local_enabled = False

    if test_local_enabled and running_event.is_set():
        test_start = datetime.now(BRAZIL_TZ)
        print(
            f"[TEST_LOCAL] Running immediately at "
            f"{test_start.strftime('%Y-%m-%d %H:%M:%S')} Brazil"
        )
        try:
            run_fetch()
        except Exception as exc:
            print(f"[TEST_LOCAL] Immediate run failed: {exc}")

        # Do not run the same scheduled hour again immediately after this test.

        test_target_hour = get_scheduled_target_hour(test_start)
        if test_target_hour is not None:
            last_run_key = (test_start.date(), test_target_hour)

    while True:
        if not running_event.is_set():
            if not stopped_message_shown:
                print("Bot stopped...")
                stopped_message_shown = True
            time.sleep(5)
            continue

        stopped_message_shown = False
        current_brazil = datetime.now(BRAZIL_TZ)
        target_hour = get_scheduled_target_hour(current_brazil)
        run_key = (current_brazil.date(), target_hour)

        if target_hour is None or run_key == last_run_key:
            time.sleep(15)
            continue

        # Mark before running so an exception cannot cause repeated API calls
        # every 15 seconds within the same hour.
        last_run_key = run_key
        print(
            f"[SCHEDULE] Starting target {target_hour:02d}:00 at "
            f"{current_brazil.strftime('%H:%M:%S')} Brazil "
            f"for {current_brazil.date()}"
        )

        run_completed = False
        try:
            run_fetch()
            run_completed = True
        except Exception as e:
            print(f"Error in run_fetch: {e}")

        if target_hour == 21 and run_completed:
            delete_old_list_after_final_run()


if __name__ == "__main__":
    test_local_mode = False
    if test_local_mode:
        print("Test local mode started...")
        main_loop()
    else:
        threading.Thread(target=main_loop, daemon=True).start()
        print("Main loop started in background thread...")
        run_telegram_bot()
