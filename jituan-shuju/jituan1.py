import warnings
warnings.filterwarnings("ignore")

import json
import os
import time
import traceback
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import requests
import pyotp
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
RETENTION_URL = ( "https://api6.o-9-d-4.com/api/backend/trpc/channel.dayRetention")

# ==================================================
# 🤖 TELEGRAM BOT CONFIG
# ==================================================
TELEGRAM_BOT_TOKEN = "8971726965:AAHG2LHxb2z97Rv2BUdzTRWPJCxrTHRqSI4"
TARGET_CHAT_ID = -5386037443

# ==================================================
# 时间处理
#
# QUY ƯỚC:
# Telegram nhập giờ = giờ WEB / Brazil
#
# Ví dụ:
# 发数据 2026-08-07 00:00:00 到 2026-08-07 23:59:59
#
# => API:
# startTime = 2026-08-07T03:00:00.000Z
# endTime   = 2026-08-08T02:59:59.999Z
# ==================================================

BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")


def get_brazil_custom_time_range(start_dt_str, end_dt_str):

    # --------------------------------------------------
    # 1. Telegram nhập thời gian nào
    #    thì coi trực tiếp là giờ WEB Brazil
    # --------------------------------------------------

    start_web = datetime.strptime(
        start_dt_str,
        "%Y-%m-%d %H:%M:%S"
    ).replace(tzinfo=BRAZIL_TZ)

    end_web = datetime.strptime(
        end_dt_str,
        "%Y-%m-%d %H:%M:%S"
    ).replace(tzinfo=BRAZIL_TZ)

    # --------------------------------------------------
    # 2. WEB Brazil -> UTC
    # --------------------------------------------------

    start_utc = start_web.astimezone(timezone.utc)
    end_utc = end_web.astimezone(timezone.utc)

    # --------------------------------------------------
    # 3. API format
    #
    # start: .000Z
    # end:   .999Z
    # --------------------------------------------------

    start_api = start_utc.strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )

    end_api = end_utc.strftime(
        "%Y-%m-%dT%H:%M:%S.999Z"
    )

    print("========================================")
    print("🕐 WEB / Brazil:")
    print("START:", start_web.strftime("%Y-%m-%d %H:%M:%S"))
    print("END  :", end_web.strftime("%Y-%m-%d %H:%M:%S"))
    print("----------------------------------------")
    print("🌐 API / UTC:")
    print("START:", start_api)
    print("END  :", end_api)
    print("========================================")

    return {
        "查询": {
            "start": start_api,
            "end": end_api
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
        "origin": "https://admin-16025-abcab3.c-9-m-1.com",
        "referer": "https://admin-16025-abcab3.c-9-m-1.com/",
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

    r = requests.post(
        LOGIN_URL,
        headers=headers,
        json=payload,
        timeout=30
    )

    r.raise_for_status()

    data = r.json()

    if "result" not in data or "data" not in data["result"]:
        raise Exception(
            f"登录 API 失败 (响应: {data})"
        )

    token = data["result"]["data"]["json"]["token"]

    print("✅ 登录成功")

    return token


# ==================================================
# 获取渠道数据
# ==================================================

def get_channel_data_custom(
    tenant_id,
    start_str,
    end_str,
    TOKEN
):


    HEADERS = {
        "accept": "*/*",
        "authorization": f"Bearer {TOKEN}",
        "account": USERNAME,
        "client-language": "zh-CN",
        "content-type": "application/json",
        "user-agent": "Mozilla/5.0",
    }

    # ==================================================
    # 生成 API 时间
    # ==================================================

    ranges = get_brazil_custom_time_range(
        start_str,
        end_str
    )

    api_start = ranges["查询"]["start"]
    api_end = ranges["查询"]["end"]

    all_rows = []

    page = 1

    while True:

        payload = {
            "json": {
                "tenantId": tenant_id,
                "regionId": REGION_ID,
                "channelId": [],
                "page": page,

                # Web 是 50
                # 这里可以使用 100 分页读取
                "pageSize": 100,

                "order": [
                    {
                        "key": "channelId",
                        "type": "desc"
                    },
                    {
                        "key": "isOfficial",
                        "type": "desc"
                    }
                ],

                "startTime": api_start,
                "endTime": api_end,
            }
        }

        print()
        print("🚀 请求 API")
        print("page:", page)
        print("startTime:", api_start)
        print("endTime:", api_end)

        r = requests.get(
            DATA_URL,
            headers=HEADERS,
            params={
                "input": json.dumps(
                    payload,
                    separators=(",", ":")
                )
            },
            timeout=60,
        )

        r.raise_for_status()

        data = r.json()

        if (
            "result" not in data
            or "data" not in data["result"]
        ):
            raise Exception(
                f"获取数据 API 失败 (响应: {data})"
            )

        rows = (
            data["result"]["data"]["json"]
            .get("list", [])
        )

        print(
            f"📄 page {page} → {len(rows)} 条"
        )

        if not rows:
            break

        all_rows.extend(rows)

        if len(rows) < 100:
            break

        page += 1

        # 防止 API 请求过快
        time.sleep(3)

    print()
    print(
        f"✅ API 总共获取 {len(all_rows)} 条数据"
    )

    return all_rows
def get_retention_data(
    tenant_id,
    date_str,
    TOKEN
):

    headers = {
        "accept": "*/*",
        "authorization": f"Bearer {TOKEN}",
        "account": USERNAME,
        "client-language": "zh-CN",
        "content-type": "application/json",
        "user-agent": "Mozilla/5.0",
    }


    # ==================================================
    # 留存查询范围
    #
    # 例如输入:
    # 2026-08-07
    #
    # 自动查询:
    # 2026-08-03 ~ 2026-08-07
    # ==================================================

    end_date = datetime.strptime(
        date_str,
        "%Y-%m-%d"
    )

    start_date = (
        end_date - timedelta(days=4)
    )


    start_time = start_date.strftime(
        "%Y-%m-%d"
    )

    end_time = end_date.strftime(
        "%Y-%m-%d"
    )


    payload = {
        "json": {

            "tenantId": tenant_id,

            "regionId": REGION_ID,

            "channelIds": [],


            # 自动5天范围
            "startTime": start_time,

            "endTime": end_time,


            "type": "recharge",

            "parentType": "none",

            "page": 1,

            "pageSize": 50,


            "order": [
                {
                    "key": "time",
                    "type": "desc"
                }
            ],


            "timeType": "days_90",


            "retentionDays": [
                0,
                1,
                2,
                3,
                4
            ]
        }
    }


    print("========================")
    print("📈 留存查询:")
    print("START:", start_time)
    print("END  :", end_time)
    print("========================")


    r = requests.get(
        RETENTION_URL,
        headers=headers,
        params={
            "input": json.dumps(
                payload,
                separators=(",", ":")
            )
        },
        timeout=60
    )


    r.raise_for_status()


    data = r.json()


    print("========================")
    print(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False
        )
    )
    print("========================")


    retention_list = (
        data["result"]
        ["data"]
        ["json"]
        ["data"]
        .get("retentionList", [])
    )


    print(
        "✅ 留存数据:",
        len(retention_list),
        "条"
    )


    return retention_list




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

            df[col] = (
                pd.to_numeric(
                    df[col],
                    errors="coerce"
                )
                .fillna(0)
                / 100
            )

    print("✅ 金额字段处理完成")

    return df


# ==================================================
# 字段重命名
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

    creds = Credentials.from_service_account_file(
        GOOGLE_JSON,
        scopes=scope
    )

    client = gspread.authorize(creds)

    sheet = client.open_by_key(
        GOOGLE_SHEET_ID
    )

    def write_sheet(sheet_name, data):

        try:
            ws = sheet.worksheet(sheet_name)

        except Exception:
            ws = sheet.add_worksheet(
                title=sheet_name,
                rows="3000",
                cols="100"
            )

        ws.batch_clear(["A2:ZZ"])

        data = data.fillna("")

        values = data.values.tolist()

        if values:

            ws.update(
                range_name="A2",
                values=values
            )

        print(
            "✅ 更新 Google Sheet 成功:",
            sheet_name
        )

    if "数据类型" in df.columns:

        custom_data = df[
            df["数据类型"] == "自定义数据"
        ].copy()

        if len(custom_data):

            write_sheet(
                "推广渠道报表",
                custom_data
            )

    else:

        write_sheet(
            "推广渠道报表",
            df
        )


# ==================================================
# TELEGRAM
# ==================================================

async def get_id_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    chat = update.message.chat

    msg = (
        f"📌 **Chat ID 信息:**\n"
        f"- 名称: `{chat.title or chat.username}`\n"
        f"- **Chat ID:** `{chat.id}`"
    )

    await update.message.reply_text(
        msg,
        parse_mode="Markdown"
    )


# ==================================================
# HANDLE 发数据
# ==================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if (
        not update.message
        or not update.message.text
    ):
        return

    # 只处理指定群
    if update.effective_chat.id != TARGET_CHAT_ID:
        return

    text = update.message.text.strip()

    if not text.startswith("发数据"):
        return

    try:

        import re

        # ==================================================
        # 提取两个完整时间
        # ==================================================

        time_matches = re.findall(
            r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}",
            text
        )

        if len(time_matches) < 2:

            await update.message.reply_text(
                "⚠️ 格式错误！\n\n"
                "正确格式：\n"
                "`发数据 2026-08-07 00:00:00 到 2026-08-07 23:59:59`",
                parse_mode="Markdown"
            )

            return

        tenant_id = TENANT_ID
        TOKEN = get_token()

        start_str = time_matches[0]
        end_str = time_matches[1]

        # ==================================================
        # 先显示用户输入的时间
        # ==================================================

        await update.message.reply_text(
            f"⏳ 正在获取数据\n\n"
            f"商户: `{tenant_id}`\n"
            f"WEB时间:\n"
            f"`{start_str}`\n"
            f"→\n"
            f"`{end_str}`\n\n"
            f"正在转换 API UTC 时间，请稍候...",
            parse_mode="Markdown"
        )

        # ==================================================
        # 获取 API 数据
        # ==================================================

        rows = get_channel_data_custom(
            tenant_id,
            start_str,
            end_str,
            TOKEN
        )

        # ==================================================
        # 无数据
        # ==================================================

        if not rows:

            await update.message.reply_text(
                "❌ 该时间段内没有数据。"
            )

            return

        # ==================================================
        # 标记数据类型
        # ==================================================

        for row in rows:
            row["data_type"] = "自定义数据"

        # ==================================================
        # DataFrame
        # ==================================================

        df = pd.DataFrame(rows)

        # ==================================================
        # 金额 /100
        # ==================================================

        df = format_money(df)

        # ==================================================
        # 中文表头
        # ==================================================

        df = df.rename(
            columns=COLUMN_MAPPING
        )

        # ==================================================
        # 数据类型处理
        # ==================================================

        df["首充人数"] = pd.to_numeric(
            df["首充人数"],
            errors="coerce"
        ).fillna(0)

        df["分润首充人数"] = pd.to_numeric(
            df["分润首充人数"],
            errors="coerce"
        ).fillna(0)

        # ==================================================
        # 总首存
        # ==================================================

        total_first_recharge = int(
            (
                df["首充人数"]
                + df["分润首充人数"]
            ).sum()
        )
        

        # ==================================================
        # 拉量线
        # ==================================================

        la_liang_line = int(
            (
                df["首充人数"] >= 100
            ).sum()
        )
        total_recharge_amount = (
    df["充值金额"].sum()
    +
    df["分润充值金额"].sum()
)
        total_recharge_count = (
    df["充值人数"].sum()
    +
    df["分润充值人数"].sum()
)
        if total_recharge_count > 0:
            recharge_avg = round(
        total_recharge_amount
        /
        total_recharge_count,
        2
    )
        else:
            recharge_avg = 0


        # ==================================================
        # 潜力线
        # ==================================================

        qian_li_line = int(
            (
                (df["首充人数"] >= 50)
                &
                (df["首充人数"] < 100)
            ).sum()
        )

        # ==================================================
        # 未测线
        # ==================================================

        wei_ce_line = int(
            (
                (df["首充人数"] >= 0)
                &
                (df["首充人数"] < 50)
            ).sum()
        )

        total_bus_count = (
            la_liang_line
            + qian_li_line
            + wei_ce_line
        )

        # ==================================================
        # 上传 Google Sheet
        # ==================================================

        upload_google_sheet(df)

        # ==================================================
        # Excel
        # ==================================================

        file_name = (
            f"16025 推广报表_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )

        df.to_excel(
            file_name,
            index=False
        )

        # ==================================================
        # 发送 Excel
        # ==================================================

        caption_text = (
            f"✅ 商户 {tenant_id} 推广渠道报表\n"
            f"WEB时间: {start_str} → {end_str}"
        )

        with open(
            file_name,
            "rb"
        ) as f:

            await update.message.reply_document(
                document=f,
                filename=file_name,
                caption=caption_text,
                read_timeout=180,
                write_timeout=180,
                connect_timeout=60
            )

        # ==================================================
        # 统计
        # ==================================================
        retention_rows = get_retention_data(
    tenant_id,
    start_str[:10],
    TOKEN
)
        ret_map = {}
        for item in retention_rows:
            ret_map[item["time"]] = item

        today = datetime.strptime(start_str[:10],
    "%Y-%m-%d"
)
        d0 = today.strftime("%Y-%m-%d")
        d1 = (
    today - timedelta(days=1)
).strftime("%Y-%m-%d")
        d2 = (
    today - timedelta(days=2)
).strftime("%Y-%m-%d")
        d3 = (
    today - timedelta(days=3)
).strftime("%Y-%m-%d")
        d4 = (
    today - timedelta(days=4)
).strftime("%Y-%m-%d")
        def calc_rate(data, field):
             count = data.get("count",0)
             if count == 0:
                 return 0
             return round(
        data.get(field,0)
        /
        count
        *
        100,
        2
    )
        repeat_rate = calc_rate(
            ret_map.get(d0,{}),
    "repeatCount"
)
        day2_rate = calc_rate(
    ret_map.get(d1,{}),
    "count1"
)
        day3_rate = calc_rate(
    ret_map.get(d2,{}),
    "count2"
)
        day4_rate = calc_rate(
    ret_map.get(d3,{}),
    "count3"
)
        day5_rate = calc_rate(
    ret_map.get(d4,{}),
    "count4"
)


        stat_message = (
            f"📊 数据统计\n\n"

    f"总首存 {total_first_recharge}\n"
    f"充值人均 {recharge_avg}\n"
    f"总线数 {total_bus_count}\n"
    f"拉量线 {la_liang_line}\n"
    f"潜力线 {qian_li_line}\n"
    f"未测线 {wei_ce_line}\n\n"

            f"📈 留存数据\n\n"

    f"复充率 {repeat_rate}%\n"
    f"2日留存 {day2_rate}%\n"
    f"3日留存 {day3_rate}%\n"
    f"4日留存 {day4_rate}%\n"
    f"5日留存 {day5_rate}%"
)

        await update.message.reply_text(
            stat_message
        )

        # ==================================================
        # 删除临时 Excel
        # ==================================================

        if os.path.exists(file_name):
            os.remove(file_name)

    except Exception as e:

        print(
            "--- ❌ 发生错误详情 ---"
        )

        traceback.print_exc()

        print(
            "------------------------"
        )

        await update.message.reply_text(
            f"❌ 发生错误:\n`{str(e)}`",
            parse_mode="Markdown"
        )


# ==================================================
# MAIN
# ==================================================

if __name__ == "__main__":

    print(
        "🤖 Telegram 机器人正在运行并监听群组消息..."
    )
    from telegram.request import HTTPXRequest
    request = HTTPXRequest(connect_timeout=60,
    read_timeout=180,
    write_timeout=180,
    pool_timeout=60
)
    

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .request(request)
        .build()
    )

    app.add_handler(
        CommandHandler(
            "id",
            get_id_command
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & (~filters.COMMAND),
            handle_message
        )
    )

    app.run_polling()