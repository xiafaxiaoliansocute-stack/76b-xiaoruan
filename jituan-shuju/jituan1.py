import json
import requests
import pandas as pd
import pyotp
import gspread
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials

# ==========================
# BRAZIL TIME CUSTOM
# ==========================

BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")


def get_brazil_time_range(
        date_str,
        start_hour,
        end_hour
):

    """
    date_str:
        日期
        例如:
        2026-07-20

    start_hour:
        开始小时
        例如 0

    end_hour:
        结束小时
        例如 17
    """

    def utc_format(dt):

        return dt.astimezone(
            timezone.utc
        ).strftime(
            "%Y-%m-%dT%H:%M:%S.000Z"
        )


    year, month, day = map(
        int,
        date_str.split("-")
    )


    start_time = datetime(
        year,
        month,
        day,
        start_hour,
        0,
        0,
        tzinfo=BRAZIL_TZ
    )


    end_time = datetime(
        year,
        month,
        day,
        end_hour,
        59,
        59,
        tzinfo=BRAZIL_TZ
    )


    return {

        "自定义": {

            "start":
                utc_format(start_time),

            "end":
                utc_format(end_time)

        }

    }
# ==========================
# GOOGLE SHEET CONFIG
# ==========================

GOOGLE_SHEET_ID = (
    "1qw3l5FVfEnHN1JsA-KWwo7cIpgXfy4vVUHcI5Reh_ww"
)

CREDENTIAL_FILE = (
    "/Users/xiaoruan/Documents/data_get/credentials.json"
)

# ==========================
# LOGIN CONFIG
# ==========================

TENANT_ID = 4505213
REGION_ID = 1
USERNAME = "16027tg01"
PASSWORD = "16027tg01"
OTP_SECRET = "EZ3GIXA7C5DEA6ZP"
LOGIN_URL = (
    "https://api6.o-9-d-4.com/api/backend/trpc/auth.login"
)

URL = (
    "https://api6.o-9-d-4.com/api/backend/trpc/channel.hourReportList"
)

# ==========================
# LOGIN GET TOKEN
# ==========================

TOTP = pyotp.TOTP(
    OTP_SECRET
).now()

print(
    "当前OTP:",
    TOTP
)

def get_token():
    login_headers = {
        "accept": "*/*",
        "content-type":
            "application/json",
        "client-language":
            "zh-CN",
        "account":
            USERNAME,
        "origin":
            "https://admin6-000-kd083bq.c-9-m-1.com",

        "referer":
            "https://admin6-000-kd083bq.c-9-m-1.com/",

        "user-agent":
            "Mozilla/5.0"

    }

    payload = {


        "json": {


            "username":
                USERNAME,


            "password":
                PASSWORD,


            "totp":
                TOTP,


            "hToken":
                ""

        }

    }




    r = requests.post(

        LOGIN_URL,

        headers=login_headers,

        json=payload,

        timeout=30

    )

    if r.status_code != 200:
        print(
            "❌ 登录失败"
        )

        print(
            r.text
        )
        exit()
    data = r.json()
    token = (

        data["result"]
        ["data"]
        ["json"]
        ["token"]

    )

    print(
        "✅ 登录成功"
    )
    return token
TOKEN = get_token()

# ==========================
# API HEADERS
# ==========================

headers = {
    "accept":
        "*/*",

    "authorization":
        f"Bearer {TOKEN}",
    "account":
        USERNAME,
    "cache-control":
        "no-cache",
    "client-language":
        "zh-CN",
    "content-type":
        "application/json",
    "fingerprint-id":
        "3w08hakZFjz23WJBjwjx",
    "origin":
        "https://admin6-000-kd083bq.c-9-m-1.com",
    "referer":
        "https://admin6-000-kd083bq.c-9-m-1.com/",
    "user-agent":
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
}

# ==========================
# GET 今日 + 昨日
# ==========================

all_data = []

# ==========================
# 自定义查询时间
# ==========================

TIME_RANGES = get_brazil_time_range(

    date_str="2026-07-9",

    start_hour=0,

    end_hour=19

)

for data_type, time_range in TIME_RANGES.items():


    print("======================")
    print(
        "正在获取:",
        data_type
    )
    print("======================")
    page = 1
    PAGE_SIZE = 100
    while True:
        payload = {
            "json": {
                "tenantId":
                    TENANT_ID,
                "regionId":
                    REGION_ID,
                "channelId": [],
                "page":
                    page,
                "pageSize":
                    PAGE_SIZE,



                "order": [


                    {

                        "key":
                            "channelId",
                        "type":
                            "desc"

                    },

                    {
                        "key":
                            "isOfficial",

                        "type":
                            "desc"
                    }
                ],
                "startTime":
                    time_range["start"],
                "endTime":
                    time_range["end"]
            }
        }
        r = requests.get(
            URL,
            headers=headers,
            params={

                "input":
                    json.dumps(
                        payload,
                        separators=(
                            ",",
                            ":"
                        )
                    )
            },

            timeout=30
        )
        print(
            data_type,
            "page",
            page,
            "HTTP",
            r.status_code
        )

        if r.status_code != 200:
            print(
                r.text
            )
            break
        result = r.json()
        json_data = (
            result["result"]
            ["data"]
            ["json"]
        )
        rows = json_data.get(
            "list",
            []
        )
        print(
            data_type,
            "数量:",
            len(rows)
        )
        if not rows:

            break
        for row in rows:
            row["data_type"] = data_type
        all_data.extend(rows)
        if len(rows) < PAGE_SIZE:

            break

        page += 1
# ==========================
# SAVE EXCEL
# ==========================


print("======================")

print(
    "TOTAL DATA:",
    len(all_data)
)

df = pd.DataFrame(
    all_data
)

# ==========================
# 金额字段 / Amount divide 100
# ==========================
MONEY_FIELDS = [

    "firstRechargeAmount",
    "rechargeAmount",
    "withdrawAmount",
    "betAmount",
    "validBetAmount",
    "reward",
    "rechargeWithdrawDiff",

    # 裂变

    "splitFirstRechargeAmount",
    "splitRechargeAmount",
    "splitWithdrawAmount",
    "splitBetAmount",
    "splitValidBetAmount",
    "splitReward"

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

print("✅ 金额字段已除100")


print(
    df.head()
)

df.to_excel(
    "channel_hourReportList.xlsx",
    index=False
)

print(
    "✅ Excel 保存成功"
)

# ==========================
# GOOGLE SHEET UPLOAD
# 今日 -> 推广渠道报表
# 昨日 -> 昨日推广渠道报表
# ==========================

def upload_google_sheet(df):
    scope = [

        "https://www.googleapis.com/auth/spreadsheets",

        "https://www.googleapis.com/auth/drive"

    ]

    creds = Credentials.from_service_account_file(
        CREDENTIAL_FILE,
        scopes=scope

    )
    client = gspread.authorize(
        creds
    )
    sheet = client.open_by_key(

        GOOGLE_SHEET_ID

    )

    def update_sheet(sheet_name, data):

        try:
            worksheet = sheet.worksheet(
                sheet_name
            )
        except:
            worksheet = sheet.add_worksheet(
                title=sheet_name,
                rows="2000",
                cols="100"

            )

        data = data.fillna("")

        values = data.values.tolist()

        # 清除旧数据 A2以后
        worksheet.batch_clear(

            ["A2:ZZ"]

        )

        if values:
            worksheet.update(
                range_name="A2",
                values=values

            )
        print(
            "✅",
            sheet_name,

            "更新成功"

        )
    # ======================
    # 今日
    # ======================

    today_df = df[

        df["data_type"] == "今日"

    ].copy()
    update_sheet(
        "推广渠道报表",
        today_df

    )

    # ======================
    # 昨日
    # ======================
    yesterday_df = df[

        df["data_type"] == "昨日"
    ].copy()
    update_sheet(
        "昨日推广渠道报表",
        yesterday_df
    )

# 执行上传

upload_google_sheet(df)
print("======================")
print(
    "🎉 全部完成"
)
print("======================")