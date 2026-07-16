import json
import requests
import pandas as pd
import pyotp
import gspread
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials
import gspread
# ==========================
# CONFIG
# ==========================
# ==========================
# BRAZIL TIME RANGE
# ==========================

BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")


def get_brazil_time_range():

    now = datetime.now(BRAZIL_TZ)


    # 00:00 - 00:59 lấy ngày hôm trước
    if now.hour == 0:

        target_day = now.date() - timedelta(days=1)

        start = datetime(
            target_day.year,
            target_day.month,
            target_day.day,
            0,0,0,
            tzinfo=BRAZIL_TZ
        )

        end = datetime(
            target_day.year,
            target_day.month,
            target_day.day,
            23,59,59,
            tzinfo=BRAZIL_TZ
        )


    # 01:00 trở đi lấy ngày hiện tại
    else:

        start = now.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        end = now


    start_utc = start.astimezone(timezone.utc)
    end_utc = end.astimezone(timezone.utc)


    start_str = start_utc.strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )

    end_str = end_utc.strftime(
        "%Y-%m-%dT%H:%M:%S.999Z"
    )


    print("Brazil now:", now)
    print("API START:", start_str)
    print("API END:", end_str)


    return start_str, end_str


# ==========================
# GOOGLE SHEET CONFIG
# ==========================

GOOGLE_SHEET_ID = "1qw3l5FVfEnHN1JsA-KWwo7cIpgXfy4vVUHcI5Reh_ww"

CREDENTIAL_FILE = "/Users/xiaoruan/Documents/data_get/credentials.json"


def upload_google_sheet(df):

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_file(
        CREDENTIAL_FILE,
        scopes=scope
    )

    client = gspread.authorize(creds)

    sheet = client.open_by_key(
        GOOGLE_SHEET_ID
    )

    worksheet = sheet.get_worksheet(0)


    # Không xóa sheet, giữ A1


    # xử lý NaN
    df = df.fillna("")


    values = df.fillna("").values.tolist()


    # chỉ cập nhật từ A2
    worksheet.update(
        range_name="A2",
        values=values
    )


    print("✅ Google Sheet 更新成功")

TENANT_ID = 4505213
REGION_ID = 1

# 登录账号
USERNAME = "16027tg01"
PASSWORD = "16027tg01"

OTP_SECRET = "EZ3GIXA7C5DEA6ZP"

TOTP = pyotp.TOTP(OTP_SECRET).now()

print("当前OTP:", TOTP)

ACCOUNT = USERNAME


LOGIN_URL = "https://api6.o-9-d-4.com/api/backend/trpc/auth.login"

URL = "https://api6.o-9-d-4.com/api/backend/trpc/userDay.listMultiDay"


# ==========================
# 获取 TOKEN
# ==========================

def get_token():

    login_headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "client-language": "zh-CN",
        "account": USERNAME,
        "origin": "https://admin6-000-kd083bq.c-9-m-1.com",
        "referer": "https://admin6-000-kd083bq.c-9-m-1.com/",
        "user-agent": "Mozilla/5.0"
    }


    payload = {
        "json": {
            "username": USERNAME,
            "password": PASSWORD,
            "totp": TOTP,
            "hToken": ""
        }
    }


    r = requests.post(
        LOGIN_URL,
        headers=login_headers,
        json=payload,
        timeout=30
    )


    if r.status_code != 200:
        print("登录失败:")
        print(r.text)
        exit()


    data = r.json()

    print(data)


    token = data["result"]["data"]["json"]["token"]


    print("✅ 登录成功")
    print("TOKEN:", token)


    return token



# ==========================
# 获取 TOKEN
# ==========================

TOKEN = get_token()



# ==========================
# API HEADERS
# ==========================

headers = {
    "accept": "*/*",
    "authorization": f"Bearer {TOKEN}",
    "account": ACCOUNT,
    "cache-control": "no-cache",
    "client-language": "zh-CN",
    "content-type": "application/json",
    "fingerprint-id": "3w08hakZFjz23WJBjwjx",
    "origin": "https://admin6-000-kd083bq.c-9-m-1.com",
    "pragma": "no-cache",
    "referer": "https://admin6-000-kd083bq.c-9-m-1.com/",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/149.0.0.0 Safari/537.36",
    "x-admin-host": "admin6-000-kd083bq.c-9-m-1.com",
}



# ==========================
# 测试：只获取100条
# ==========================

PAGE_SIZE = 100
page = 1

payload = {

    "json": {

        "page": page,

        "pageSize": PAGE_SIZE,

        "valueType": "phone",

        "isRecharge": True,

        "queryTime": datetime.now(
            BRAZIL_TZ
        ).strftime(
            "%Y-%m-%d"
        ),

        "type": "normal",

        "regionId": REGION_ID,

        "tenantId": TENANT_ID,

        "queryData": [],

        "order": [
            {
                "key": "",
                "type": "desc"
            }
        ],

        "queryType": "table"

    }

}


print("请求 Page:", page)


r = requests.get(

    URL,

    headers=headers,

    params={
        "input": json.dumps(
            payload,
            separators=(",", ":")
        )
    },

    timeout=30

)


print("HTTP:", r.status_code)


data = r.json()


json_data = (
    data["result"]
    ["data"]
    ["json"]
)


print(
    "JSON TYPE:",
    type(json_data)
)


# userDay.list 返回直接list

if isinstance(json_data, list):

    rows = json_data

else:

    rows = (
        json_data
        .get("pageList", {})
        .get("pageData", [])
    )


print(
    "数量:",
    len(rows)
)


# 保存100条

df = pd.DataFrame(rows)


print(df.head())


df.to_excel(
    "userDay_test100.xlsx",
    index=False
)


print(
    "✅ 保存完成 userDay_test100.xlsx"
)