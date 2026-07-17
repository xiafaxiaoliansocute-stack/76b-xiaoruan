import requests
import json
import gspread


from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google.oauth2.service_account import Credentials



# ==================================================
# CONFIG
# ==================================================

TENANT_ID = 2175621


TOKEN = "0vkpu7olptxu5eak9ewzv5f4yq75t998wcsxcoan"


ACCOUNT = "xiaoruan16011"


FINGERPRINT_ID = "6hUecf0K0ity09A0YcED"



API_URL = (
"https://api6.o-9-d-4.com/api/backend/trpc/realTimeData.list"
)



# Google Sheet

CREDENTIALS_FILE = (
"/Users/xiaoruan/Documents/data_get/credentials.json"
)


SHEET_ID = (
"1gfsTt_nL0wK2mepUAXkBgRqZHLYRY3xqWmbAxkzp0ao"
)


SHEET_NAME = "66aa"





# ==================================================
# HEADER
# ==================================================


HEADERS = {

"authorization":
f"Bearer {TOKEN}",

"account":
ACCOUNT,

"client-language":
"zh-CN",

"fingerprint-id":
FINGERPRINT_ID,

"x-admin-host":
"admin-16011-34bc8f.c-9-m-1.com",

"origin":
"https://admin-16011-34bc8f.c-9-m-1.com",

"user-agent":
"Mozilla/5.0"

}




# ==================================================
# 获取最近4天时间
# ==================================================


def get_target_time():


    brazil = ZoneInfo(
        "America/Sao_Paulo"
    )


    now = datetime.now(
        brazil
    )


    # 21:03 -> 21:00

    target = now.replace(

        minute=0,

        second=0,

        microsecond=0

    )



    result=[]


    for i in range(4):


        t = target - timedelta(
            days=i
        )


        result.append({

            "date":
            t.strftime("%Y-%m-%d"),


            "time":
            t.strftime("%H:%M")

        })


    return result





# ==================================================
# API
# ==================================================


def get_api(date):


    params={


        "input":json.dumps({

            "json":{

                "tenantId":
                TENANT_ID,


                "dateTime":
                date

            }

        })

    }



    r=requests.get(

        API_URL,

        params=params,

        headers=HEADERS,

        timeout=30

    )


    print(
        "API",
        date,
        r.status_code
    )


    return r.json()






# ==================================================
# 查找对应时间
# ==================================================


def get_rows():


    result={}



    targets=get_target_time()



    for target in targets:


        date=target["date"]

        need_time=target["time"]



        api=get_api(
            date
        )



        rows=(

            api["result"]
            ["data"]
            ["json"]

        )



        for row in rows:


            utc=datetime.fromisoformat(

                row["createTime"].replace(
                    "Z",
                    "+00:00"
                )

            )


            brazil=utc.astimezone(

                ZoneInfo(
                    "America/Sao_Paulo"
                )

            )


            show_time=brazil.strftime(
                "%H:%M"
            )



            if show_time==need_time:



                result[date]=row



                break



    return result





# ==================================================
# 生成网页样式
# ==================================================


def make_sheet_data(data):


    dates = list(data.keys())

    dates.sort(
        reverse=True
    )


    result = []


    # header

    result.append(
        ["指标"] + dates
    )


    fields = [

        ("登录用户","loginCount"),

        ("新增注册","registerCount"),

        ("投注用户","betCount"),

        ("同时在线","onlineCount"),

        ("首充用户","firstRechargeCount"),

        ("裂变首充","subFirstRechargeCount"),

        ("充值用户","rechargeCount"),

        ("平台盈利","tenantProfitAmount"),

        ("充值金额","rechargeAmount"),

        ("充值订单","rechargeTimes"),

        ("提现金额","withdrawAmount"),

        ("提现订单","withdrawTimes"),

        ("赠送金额","discountAmount")

    ]



    for name,key in fields:


        row=[name]


        for d in dates:


            value=data[d][key]


            # 金额除100

            if key in [

                "tenantProfitAmount",

                "rechargeAmount",

                "withdrawAmount",

                "discountAmount"

            ]:

                value=value/100



            row.append(
                value
            )


        result.append(
            row
        )



    # 充提差

    row=["充提差"]


    for d in dates:


        r=data[d]


        diff=(

            r["rechargeAmount"]

            -

            r["withdrawAmount"]

        )/100


        row.append(
            diff
        )


    result.append(
        row
    )



    # 人工充值/订单数

    row=["人工充值/订单数"]


    for d in dates:

        r=data[d]

        row.append(

            f'{r["manualRechargeAmount"]/100:.2f} / {r["manualRechargeTimes"]}'

        )


    result.append(row)



    # 订单充值/订单数

    row=["订单充值/订单数"]


    for d in dates:

        r=data[d]

        row.append(

            f'{r["orderRechargeAmount"]/100:.2f} / {r["orderRechargeTimes"]}'

        )


    result.append(row)



    # 人工提现/订单数

    row=["人工提现/订单数"]


    for d in dates:

        r=data[d]

        row.append(

            f'{r["manualWithdrawAmount"]/100:.2f} / {r["manualWithdrawTimes"]}'

        )


    result.append(row)



    # 订单提现/订单数

    row=["订单提现/订单数"]


    for d in dates:

        r=data[d]

        row.append(

            f'{r["orderWithdrawAmount"]/100:.2f} / {r["orderWithdrawTimes"]}'

        )


    result.append(row)



    return result

# ==================================================
# 上传 Google Sheet
# ==================================================


def upload(rows):


    scope=[

        "https://www.googleapis.com/auth/spreadsheets",

        "https://www.googleapis.com/auth/drive"

    ]



    creds=Credentials.from_service_account_file(

        CREDENTIALS_FILE,

        scopes=scope

    )



    client=gspread.authorize(
        creds
    )



    sh=client.open_by_key(
        SHEET_ID
    )


    ws=sh.worksheet(
        SHEET_NAME
    )


    ws.clear()



    ws.update(
        rows
    )



    # 自动换行

    ws.format(

        "A1:E20",

        {

        "wrapStrategy":"WRAP",

        "verticalAlignment":"TOP"

        }

    )



    # 调整列宽

    ws.columns_auto_resize(
        0,
        5
    )



    print(
        "✅ 上传66aa完成"
    )






# ==================================================
# MAIN
# ==================================================


if __name__=="__main__":


    print(
        "开始运行"
    )


    data=get_rows()



    print(
        "获取日期:",
        list(data.keys())
    )



    rows=make_sheet_data(
        data
    )


    upload(
        rows
    )


    print(
        "全部完成"
    )