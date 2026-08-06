import warnings
warnings.filterwarnings("ignore")

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import json
import os
import traceback
import requests
import pandas as pd
import pyotp
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

# ==================================================
# GOOGLE SHEET CONFIG
# ==================================================
GOOGLE_SHEET_ID = "1qw3l5FVfEnHN1JsA-KWwo7cIpgXfy4vVUHcI5Reh_ww"
GOOGLE_JSON = "/Users/xiaoruan/Documents/service_account.json"

# ==================================================
# API CONFIG (Điền thông tin của bạn vào đây)
# ==================================================
TENANT_ID = 5195954  # Tenant ID cố định chạy chuẩn như code cũ
REGION_ID = 1
USERNAME = "16025tg1"
PASSWORD = "16025tg1"
OTP_SECRET = "CV5V6VJSORSGSGK7"  # Điền mã OTP secret nếu tài khoản bật 2FA

LOGIN_URL = "https://api6.o-9-d-4.com/api/backend/trpc/auth.login"
DATA_URL = "https://api6.o-9-d-4.com/api/backend/trpc/channel.hourReportList"

# ==================================================
# 🤖 TELEGRAM BOT CONFIG
# ==================================================
TELEGRAM_BOT_TOKEN = "8971726965:AAHG2LHxb2z97Rv2BUdzTRWPJCxrTHRqSI4"
TARGET_CHAT_ID = -5386037443

# ==================================================
# 时间处理 (巴西时间)
# ==================================================
BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")

def get_brazil_custom_time_range(start_dt_str, end_dt_str):
    def utc_format(dt):
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    start = datetime.strptime(start_dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=BRAZIL_TZ)
    end = datetime.strptime(end_dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=BRAZIL_TZ)

    return {
        "查询": {
            "start": utc_format(start),
            "end": utc_format(end)
        }
    }

# ==================================================
# LOGIN TOKEN
# ==================================================
def get_token():
    if OTP_SECRET:
        otp = pyotp.TOTP(OTP_SECRET).now()
    else:
        otp = ""

    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "client-language": "zh-CN",
        "account": USERNAME,
        "origin": "https://api6.o-9-d-4.com",
        "referer": "https://api6.o-9-d-4.com/",
        "user-agent": "Mozilla/5.0",
    }

    payload = {
        "json": {
            "username": USERNAME,
            "password": PASSWORD,
            "totp": otp,
            "hToken": ""
        }
    }

    r = requests.post(LOGIN_URL, headers=headers, json=payload, timeout=30)
    data = r.json()

    if "result" not in data or "data" not in data["result"]:
        raise Exception(f"登录 API 失败 (响应: {data})")

    token = data["result"]["data"]["json"]["token"]
    print("✅ 登录成功")
    return token

# ==================================================
# 获取渠道数据
# ==================================================
def get_channel_data_custom(tenant_id, start_str, end_str):
    TOKEN = get_token()
    HEADERS = {
        "accept": "*/*",
        "authorization": f"Bearer {TOKEN}",
        "account": USERNAME,
        "client-language": "zh-CN",
        "content-type": "application/json",
        "user-agent": "Mozilla/5.0",
    }

    ranges = get_brazil_custom_time_range(start_str, end_str)
    all_rows = []
    page = 1

    while True:
        payload = {
            "json": {
                "tenantId": tenant_id,
                "regionId": REGION_ID,
                "channelId": [],
                "page": page,
                "pageSize": 100,
                "startTime": ranges["查询"]["start"],
                "endTime": ranges["查询"]["end"],
            }
        }

        r = requests.get(
            DATA_URL,
            headers=HEADERS,
            params={"input": json.dumps(payload, separators=(",", ":"))},
            timeout=60,
        )

        data = r.json()

        if "result" not in data or "data" not in data["result"]:
            raise Exception(f"获取数据 API 失败 (响应: {data})")

        rows = data["result"]["data"]["json"].get("list", [])
        print("page", page, "数量", len(rows))

        if not rows:
            break

        all_rows.extend(rows)

        if len(rows) < 100:
            break

        page += 1

    return all_rows

# ==================================================
# 金额处理
# ==================================================
def format_money(df):
    MONEY_FIELDS = [
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
        "splitReward",
    ]

    for col in MONEY_FIELDS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0) / 100

    print("✅ 金额字段处理完成")
    return df

# ==================================================
# 字段重命名映射 (英文转中文)
# ==================================================
COLUMN_MAPPING = {
    "tenantId": "商户ID",
    "tenantName": "商户名称",
    "regionId": "地区ID",
    "regionName": "地区名称",
    "channelId": "渠道ID",
    "channelName": "渠道名称",
    "isOfficial": "是否官方",
    "channelPromoterId": "推广人ID",
    "channelPromoterName": "推广人名称",
    "registerCount": "注册人数",
    "loginCount": "登录人数",
    "firstRechargeCount": "首充人数",
    "firstRechargeAmount": "首充金额",
    "rechargeCount": "充值人数",
    "rechargeAmount": "充值金额",
    "withdrawCount": "提现人数",
    "withdrawAmount": "提现金额",
    "betCount": "投注人数",
    "betAmount": "投注金额",
    "validBetAmount": "有效投注金额",
    "reward": "奖励金额",
    "rechargeTimes": "充值次数",
    "withdrawTimes": "提现次数",
    "rechargeWithdrawDiff": "存提差",
    "splitRegisterCount": "分润注册人数",
    "splitLoginCount": "分润登录人数",
    "splitFirstRechargeCount": "分润首充人数",
    "splitFirstRechargeAmount": "分润首充金额",
    "splitRechargeCount": "分润充值人数",
    "splitRechargeAmount": "分润充值金额",
    "splitWithdrawCount": "分润提现人数",
    "splitWithdrawAmount": "分润提现金额",
    "splitBetCount": "分润投注人数",
    "splitBetAmount": "分润投注金额",
    "splitValidBetAmount": "分润有效投注金额",
    "splitReward": "分润奖励金额",
    "splitRechargeTimes": "分润充值次数",
    "splitWithdrawTimes": "分润提现次数",
    "data_type": "数据类型"
}

# ==================================================
# UPLOAD GOOGLE SHEET
# ==================================================
def upload_google_sheet(df):
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = Credentials.from_service_account_file(GOOGLE_JSON, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(GOOGLE_SHEET_ID)

    def write_sheet(sheet_name, data):
        try:
            ws = sheet.worksheet(sheet_name)
        except:
            ws = sheet.add_worksheet(title=sheet_name, rows="3000", cols="100")

        ws.batch_clear(["A2:ZZ"])
        data = data.fillna("")
        values = data.values.tolist()

        if values:
            ws.update(range_name="A2", values=values)

        print("✅ 更新 Google Sheet 成功:", sheet_name)

    if "数据类型" in df.columns:
        today = df[df["数据类型"] == "自定义数据"].copy()
        if len(today):
            write_sheet("推广渠道报表", today)
    else:
        write_sheet("推广渠道报表", df)

# ==================================================
# TELEGRAM HANDLERS
# ==================================================
async def get_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.message.chat
    msg = (
        f"📌 **Chat ID 信息:**\n"
        f"- 名称: `{chat.title or chat.username}`\n"
        f"- **Chat ID:** `{chat.id}`"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    if update.effective_chat.id != TARGET_CHAT_ID:
        return

    text = update.message.text.strip()

    if text.startswith("发数据"):
        try:
            import re
            time_matches = re.findall(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', text)

            if len(time_matches) >= 2:
                tenant_id = TENANT_ID
                start_str = time_matches[0]
                end_str = time_matches[1]
            else:
                await update.message.reply_text(
                    "⚠️ 格式错误！请按照以下格式发送：\n"
                    "`发数据 2026-08-06 00:00:00 到 2026-08-06 05:59:59`",
                    parse_mode="Markdown",
                )
                return

            await update.message.reply_text(
                f"⏳ 正在获取商户 `{tenant_id}` 从 `{start_str}` 到 `{end_str}` 的数据 (巴西时间)... 请稍候！",
                parse_mode="Markdown",
            )

            # 1. 获取数据
            rows = get_channel_data_custom(tenant_id, start_str, end_str)

            for row in rows:
                row["data_type"] = "自定义数据"

            if not rows:
                await update.message.reply_text("❌ 该时间段内没有数据。")
                return

            df = pd.DataFrame(rows)
            df = format_money(df)
            
            # 2. 替换表头为中文
            df = df.rename(columns=COLUMN_MAPPING)

            # 3. 基于首充人数计算指标
            df["首充人数"] = pd.to_numeric(df["首充人数"], errors="coerce").fillna(0)
            
            total_first_recharge = int(df["首充人数"].sum())           # 总首存
            la_liang_line = int((df["首充人数"] >= 100).sum())           # 拉量线 (≥100)
            qian_li_line = int(((df["首充人数"] >= 50) & (df["首充人数"] < 100)).sum())  # 潜力线 (50-100)
            wei_ce_line = int(((df["首充人数"] >= 0) & (df["首充人数"] < 50)).sum())    # 未测线 (0-50)
            total_bus_count = la_liang_line + qian_li_line + wei_ce_line   # 总线数 = 拉量线 + 潜力线 + 未测线

            # 4. 上传 Google Sheet
            upload_google_sheet(df)

            # 5. 导出临时 Excel 文件 (文件名：16025 推广报表_时间.xlsx)
            file_name = f"16025 推广报表_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(file_name, index=False)

            # 6. 先发送 Excel 文件
            caption_text = f"✅ 商户 {tenant_id} 推广渠道报表 ({start_str} 至 {end_str})"
            with open(file_name, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    filename=file_name,
                    caption=caption_text
                )

            # 7. 接着发送按您要求格式的统计指标文本（含总首存及按公式计算的总线数）
            stat_message = (
                f"总首存 {total_first_recharge}\n"
                f"总线数 {total_bus_count}\n"
                f"拉量线 {la_liang_line}\n"
                f"潜力线 {qian_li_line}\n"
                f"未测线 {wei_ce_line}"
            )
            await update.message.reply_text(stat_message)

            # 8. 清理临时文件
            if os.path.exists(file_name):
                os.remove(file_name)

        except Exception as e:
            print("--- ❌ 发生错误详情 ---")
            traceback.print_exc()
            print("------------------------")
            await update.message.reply_text(f"❌ 发生错误: `{str(e)}`", parse_mode="Markdown")

# ==================================================
# MAIN
# ==================================================
if __name__ == "__main__":
    print("🤖 Telegram 机器人正在运行并监听群组消息...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("id", get_id_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    app.run_polling()