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

TENANT_ID = 4687099
REGION_ID = 1

# 登录账号
USERNAME = "qzry14011"
PASSWORD = "qzry14011"

OTP_SECRET = "MR3VA72VIR7QKNKR"

TOTP = pyotp.TOTP(OTP_SECRET).now()

print("当前OTP:", TOTP)

ACCOUNT = USERNAME


LOGIN_URL = "https://api4.i-j-k-8.com/api/backend/trpc/auth.login"

URL = "https://api4.i-j-k-8.com/api/backend/trpc/withdrawal.allReviewedList"


# ==========================
# 获取 TOKEN
# ==========================

def get_token():

    login_headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "client-language": "zh-CN",
        "account": USERNAME,
        'origin': 'https://admin-14011-19ecc3.m-9-y-j.com',
        "referer": "https://admin-14011-19ecc3.m-9-y-j.com/",
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
    "origin": "https://admin-14011-19ecc3.m-9-y-j.com",
    "pragma": "no-cache",
    "referer": "https://admin-14011-19ecc3.m-9-y-j.com/",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/149.0.0.0 Safari/537.36",
    "x-admin-host": "admin-14011-19ecc3.m-9-y-j.com",
}



# ==========================
# 获取用户列表 returnVisit.list
# 测试100条
# ==========================

PAGE_SIZE = 100
PAGE = 1


payload = {

    "json": {

        "queryType": "table",

        "regionId": REGION_ID,

        "tenantId": TENANT_ID,

        "page": PAGE,

        "pageSize": PAGE_SIZE,

        "order": [

            {
                "key": "",
                "type": "desc"
            }

        ]

    }

}


print(
    "请求 Page:",
    PAGE
)


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


print(
    "HTTP:",
    r.status_code
)


data = r.json()


# ==========================
# API ERROR
# ==========================

if "result" not in data:

    print("API ERROR:")

    print(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False
        )
    )

    exit()



# ==========================
# 获取 JSON 数据
# ==========================

json_data = (

    data["result"]
    ["data"]
    ["json"]

)


print(
    json.dumps(
        json_data,
        indent=2,
        ensure_ascii=False
    )
)



# ==========================
# 解析 queryData
# ==========================

if isinstance(json_data, dict):

    rows = (

        json_data
        .get("queryData", [])

    )


elif isinstance(json_data, list):

    rows = json_data


else:

    rows = []



print(
    "数量:",
    len(rows)
)


# 总数量

if isinstance(json_data, dict):

    print(
        "总用户:",
        json_data.get("userSum", 0)
    )



if rows:

    print(
        json.dumps(
            rows[0],
            indent=2,
            ensure_ascii=False
        )
    )



# ==========================
# DataFrame
# ==========================

df = pd.DataFrame(rows)



# 手机号保持文本

for col in [
    "phoneNumber",
    "account",
    "userId"
]:

    if col in df.columns:

        df[col] = (
            df[col]
            .astype(str)
        )



print(df.head())



# ==========================
# Excel
# ==========================

df.to_excel(

    "returnVisit_test100.xlsx",

    index=False

)


print(
    "✅ 保存完成 returnVisit_test100.xlsx"
)



# ==========================
# Google Sheet
# ==========================

upload_google_sheet(df)


print(
    "✅ Google Sheet 上传完成"
)