import warnings
warnings.filterwarnings("ignore")


import json
import requests
import pandas as pd
import pyotp
import gspread


from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials



# ==================================================
# GOOGLE SHEET CONFIG
# ==================================================

GOOGLE_SHEET_ID = (
    "1qw3l5FVfEnHN1JsA-KWwo7cIpgXfy4vVUHcI5Reh_ww"
)


GOOGLE_JSON = "/Users/xiaoruan/Documents/service_account.json"



# ==================================================
# API CONFIG
# ==================================================

TENANT_ID = 2285733

REGION_ID = 1


USERNAME = "qzry16013"

PASSWORD = "qzry16013"


OTP_SECRET = "PJWB6BJ4JFYHKHZT"


LOGIN_URL = (
    "https://api6.o-9-d-4.com/api/backend/trpc/auth.login"
)


DATA_URL = (
    "https://api6.o-9-d-4.com/api/backend/trpc/channel.hourReportList"
)



# ==================================================
# BRAZIL TIME
# ==================================================

BRAZIL_TZ = ZoneInfo(
    "Etc/GMT+3"
)

def get_brazil_time_range(date_str):
    def utc_format(dt):
        return dt.astimezone(
            timezone.utc
        ).strftime(
            "%Y-%m-%dT%H:%M:%S.000Z"
        )
    y,m,d = map(
        int,
        date_str.split("-")
    )
    now = datetime.now(BRAZIL_TZ)
    start = datetime(
        y,
        m,
        d,
        0,
        0,
        0,
        tzinfo=BRAZIL_TZ
    )

    # hôm nay lấy tới thời gian hiện tại

    end = now
    return {

        "查询":{

            "start": utc_format(start),

            "end": utc_format(end)

        }

    }





# ==================================================
# LOGIN TOKEN
# ==================================================


def get_token():


    if OTP_SECRET:

        otp = pyotp.TOTP(
            OTP_SECRET
        ).now()

    else:

        otp = ""



    headers = {


        "accept":
            "*/*",

        "content-type":
            "application/json",

        "client-language":
            "zh-CN",

        "account":
            USERNAME,


        "origin":
            "https://admin-16013-97deff.c-9-m-1.com",


        "referer":
            "https://admin-16013-97deff.c-9-m-1.com/",


        "user-agent":
            "Mozilla/5.0"

    }



    payload = {


        "json":{


            "username":
                USERNAME,


            "password":
                PASSWORD,


            "totp":
                otp,


            "hToken":
                ""

        }

    }



    r=requests.post(

        LOGIN_URL,

        headers=headers,

        json=payload,

        timeout=30

    )



    data=r.json()



    token=(

        data["result"]

        ["data"]

        ["json"]

        ["token"]

    )



    print(
        "✅ 登录成功"
    )


    return token





TOKEN=get_token()



# ==================================================
# API HEADER
# ==================================================


HEADERS={


    "accept":
        "*/*",


    "authorization":
        f"Bearer {TOKEN}",


    "account":
        USERNAME,


    "client-language":
        "zh-CN",


    "content-type":
        "application/json",


    "user-agent":
        "Mozilla/5.0"

}





# ==================================================
# 获取渠道数据
# ==================================================


def get_channel_data(
        date_str
):


    ranges=get_brazil_time_range(

    date_str

)


    all_rows=[]


    page=1


    while True:


        payload={


            "json":{


                "tenantId":
                    TENANT_ID,


                "regionId":
                    REGION_ID,


                "channelId":
                    [],


                "page":
                    page,


                "pageSize":
                    100,


                "startTime":
                    ranges["查询"]["start"],


                "endTime":
                    ranges["查询"]["end"]

            }

        }



        r=requests.get(


            DATA_URL,


            headers=HEADERS,


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


            timeout=60

        )



        data=r.json()


        rows=(

            data["result"]

            ["data"]

            ["json"]

            .get(

                "list",

                []

            )

        )



        print(
            "page",
            page,
            "数量",
            len(rows)
        )



        if not rows:

            break



        all_rows.extend(rows)



        if len(rows)<100:

            break



        page+=1



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

                /100

            )


    print(
        "✅ 金额字段处理完成"
    )


    return df





# ==================================================
# GOOGLE SHEET UPLOAD
# ==================================================


def upload_google_sheet(df):


    scope=[


        "https://www.googleapis.com/auth/spreadsheets",


        "https://www.googleapis.com/auth/drive"


    ]



    creds = Credentials.from_service_account_file(

        GOOGLE_JSON,

        scopes=scope

    )



    client = gspread.authorize(

        creds

    )



    sheet = client.open_by_key(

        GOOGLE_SHEET_ID

    )



    def write_sheet(
            sheet_name,
            data
    ):


        try:

            ws = sheet.worksheet(
                sheet_name
            )

        except:


            ws = sheet.add_worksheet(

                title=sheet_name,

                rows="3000",

                cols="100"

            )



        ws.batch_clear(
    ["A2:ZZ"]
)



        data=data.fillna("")

        # không lấy tiêu đề
        data = data.fillna("")
        values = data.values.tolist()
        ws.batch_clear(
    ["A2:ZZ"]
)
        if values:

         ws.update(
        range_name="A2",
        values=values
    )




        print(

            "✅ 更新成功:",

            sheet_name

        )




    # =========================
    # 今日
    # =========================


    if "data_type" in df.columns:


        today=df[

            df["data_type"]=="今日"

        ].copy()



        if len(today):

            write_sheet(

                "推广渠道报表",

                today

            )



        yesterday=df[

            df["data_type"]=="昨日"

        ].copy()



        if len(yesterday):

            write_sheet(

                "昨日推广渠道报表",

                yesterday

            )



    else:


        write_sheet(

            "推广渠道报表",

            df

        )





# ==================================================
# MAIN
# ==================================================


if __name__=="__main__":


    print(
        "🚀 开始获取渠道数据"
    )



    # ==========================
    # 日期
    # ==========================


    today=datetime.now(
    BRAZIL_TZ
).date()



    all_data=[]



    # ==========================
    # 今日
    # ==========================


    print(

        "🇧🇷 今日:",

        today

    )


    today_rows=get_channel_data(

        str(today)

    )


    for row in today_rows:


        row["data_type"]="今日"



    all_data.extend(

        today_rows

    )


    print(

        "TOTAL:",

        len(all_data)

    )



    # dataframe


    df=pd.DataFrame(

        all_data

    )



    if df.empty:


        print(

            "❌ 没有数据"

        )

        exit()



    # 金额处理


    df=format_money(

        df

    )



    print(

        df.head()

    )



    # 上传


    upload_google_sheet(

        df

    )



    print(
        "======================"
    )

    print(
        "🎉 全部完成"
    )

    print(
        "======================"
    )