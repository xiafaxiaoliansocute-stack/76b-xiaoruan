import requests
import json
import time
import pandas as pd
import gspread


from io import StringIO
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from google.oauth2.service_account import Credentials



# ==================================================
# API CONFIG
# ==================================================

TOKEN = "40c2mcwk81wlcw6vs7unbh66f8qv98xa4pn2bhlv"

ACCOUNT = "xiaoruan16021"

TENANT_ID = 2654039

REGION_ID = 1



BASE_URL = (
    "https://api6.o-9-d-4.com/api/backend/trpc"
)



HEADERS = {


    "authorization":
        f"Bearer {TOKEN}",


    "account":
        ACCOUNT,


    "x-admin-host":
        "admin-16021-9fab47.c-9-m-1.com",


    "client-language":
        "zh-CN",


    "content-type":
        "application/json"

}





# ==================================================
# GOOGLE SHEET
# ==================================================

GOOGLE_JSON = (
    "/Users/xiaoruan/Documents/data_get/credentials.json"
)



SHEET_ID = (
    "1gfsTt_nL0wK2mepUAXkBgRqZHLYRY3xqWmbAxkzp0ao"
)



# 输出
WORKSHEET_NAME = "三方充值"


# 输入
FIRST_SHEET_NAME = "每日首充"






# ==================================================
# Brazil 昨天
# ==================================================

def get_brazil_yesterday():


    tz = ZoneInfo(
        "America/Sao_Paulo"
    )


    now = datetime.now(tz)


    return (

        now.date()

        -

        timedelta(days=1)

    )







# ==================================================
# 创建充值导出
# ==================================================

def create_export(day):


    create_time = datetime.now(
        timezone.utc
    )



    payload = {


        "json":{


            "queryType":

                "export",



            "changeAmountStatus":

                "HAVE_ARRIVED",



            "timeType":

                "updateTime",



            "regionId":

                REGION_ID,



            "tenantId":

                TENANT_ID,



            "startTime":

                f"{day}T03:00:00.000Z",



            "endTime":

                f"{day + timedelta(days=1)}T02:59:59.999Z",



            "tableType":

                "success"

        }

    }





    r=requests.get(


        BASE_URL +

        "/payRecord.exportList",


        headers=HEADERS,


        params={

            "input":

            json.dumps(

                payload,

                separators=(",",":")

            )

        },


        timeout=60

    )



    print(

        "创建导出:",

        r.status_code

    )



    return create_time







# ==================================================
# 查找导出任务
# ==================================================

def find_new_export(create_time):


    payload={


        "json":{


            "page":1,


            "pageSize":50,


            "regionId":REGION_ID,


            "tenantId":TENANT_ID

        }

    }



    r=requests.get(


        BASE_URL +

        "/exportData.list",


        headers=HEADERS,


        params={

            "input":

            json.dumps(

                payload,

                separators=(",",":")

            )

        }

    )



    items=(

        r.json()

        ["result"]

        ["data"]

        ["json"]

        ["exportDataList"]

    )



    for item in items:



        if item["moduleType"] != "SuccessPayRecord":

            continue




        api_time=datetime.fromisoformat(

            item["createTime"]

            .replace(

                "Z",

                "+00:00"

            )

        )



        if api_time >= create_time:


            print(

                "找到任务:",

                item["id"]

            )


            return item



    return None
# ==================================================
# 等待导出完成
# ==================================================

def wait_export(create_time):


    while True:


        task = find_new_export(

            create_time

        )



        if task:


            if task["status"] == "ExportSuccess":


                print(

                    "导出完成:",

                    task["id"]

                )


                return task["id"]



            else:


                print(

                    "生成中:",

                    task["id"]

                )



        else:


            print(

                "等待任务..."

            )



        time.sleep(5)







# ==================================================
# 获取CSV地址
# ==================================================

def get_csv_url(export_id):


    payload = {


        "json":{


            "tenantId":

                TENANT_ID,


            "id":

                export_id

        }

    }



    r=requests.post(


        BASE_URL +

        "/exportData.download",


        headers=HEADERS,


        json=payload,


        timeout=60

    )



    data=r.json()



    url=(

        data

        ["result"]

        ["data"]

        ["json"]

        ["filePath"]

    )



    print(

        "CSV地址获取成功"

    )


    return url








# ==================================================
# 获取每日首充 类型
# ==================================================

def get_first_type_map(client):


    ws = client.open_by_key(
        SHEET_ID
    ).worksheet(
        FIRST_SHEET_NAME
    )


    rows = ws.get_all_values()



    result = {}



    # bỏ dòng标题
    for row in rows[1:]:



        if len(row) < 5:
            continue



        uid = str(
            row[1]
        ).strip()
        # B列 会员id



        channel_type = str(
            row[4]
        ).strip()
        # E列 渠道





        if uid:


            if channel_type == "直推":


                result[uid] = "直推"



            elif channel_type == "裂变":


                result[uid] = "裂变"






    print(

        "每日首充匹配ID:",

        len(result)

    )


    return result

# ==================================================
# 处理充值数据
# ==================================================

def process_recharge(csv_url):


    print(

        "读取充值CSV..."

    )



    r=requests.get(

        csv_url,

        timeout=120

    )



    raw=pd.read_csv(


        StringIO(

            r.content.decode(

                "utf-8-sig"

            )

        )

    )



    raw=raw.fillna("")



    print(

        "原始充值数量:",

        len(raw)

    )



    print(

        "CSV字段:",

        raw.columns.tolist()

    )






    # ==============================
    # 自动寻找字段
    # ==============================


    user_col=None

    amount_col=None

    channel_col=None

    time_col=None



    for c in raw.columns:


        name=str(c).lower()



        if name in [

            "会员id",

            "userid",

            "user_id"

        ]:


            user_col=c




        elif name in [

            "支付金额",

            "充值金额",

            "amount"

        ]:


            amount_col=c




        elif name in [

            "会员渠道",

            "渠道",

            "channel"

        ]:


            channel_col=c




        elif (

            "完成时间" in str(c)

            or

            "time" in name

        ):


            time_col=c







    print(

        "识别字段:",

        user_col,

        amount_col,

        channel_col,

        time_col

    )





    if not all([

        user_col,

        amount_col,

        channel_col,

        time_col

    ]):


        raise Exception(

            "CSV字段错误"

        )







    df = raw[

        [

            user_col,

            amount_col,

            channel_col,

            time_col

        ]

    ].copy()



    df.columns=[


        "会员id",

        "支付金额",

        "会员渠道",

        "完成时间"


    ]






    # ID统一

    df["会员id"]=(

        df["会员id"]

        .astype(str)

    )






    # 日期

    df["完成时间"]=pd.to_datetime(

        df["完成时间"]

    ).dt.strftime(

        "%Y-%m-%d"

    )






    # 金额转数字

    df["支付金额"]=pd.to_numeric(

        df["支付金额"],

        errors="coerce"

    ).fillna(0)







    # ==============================
    # 计算支付次数
    # ==============================


    pay_count=(


        df

        .groupby(

            [

                "会员id",

                "完成时间"

            ]

        )

        .size()

        .reset_index(

            name="支付次数"

        )

    )








    # ==============================
    # 合并金额
    # ==============================


    df=(


        df

        .groupby(

            [

                "会员id",

                "完成时间"

            ],

            as_index=False

        )

        .agg(

            {

                "支付金额":"sum",

                "会员渠道":"first"

            }

        )

    )





    df=df.merge(

        pay_count,

        on=[

            "会员id",

            "完成时间"

        ],

        how="left"

    )





    print(

        "合并后:",

        len(df)

    )



    return df
# ==================================================
# 加入直推/裂变
# 上传Google Sheet
# ==================================================

def upload_google(df):


    scopes=[


        "https://www.googleapis.com/auth/spreadsheets",


        "https://www.googleapis.com/auth/drive"


    ]



    creds=Credentials.from_service_account_file(


        GOOGLE_JSON,


        scopes=scopes


    )



    client=gspread.authorize(

        creds

    )





    # ==============================
    # 匹配每日首充
    # ==============================


    first_map=get_first_type_map(

        client

    )



    df["直推/裂变"]=(


        df["会员id"]

        .map(first_map)

        .fillna("")

    )





    # ==============================
    # 最终字段
    # ==============================


    df=df[


        [

            "会员id",

            "支付金额",

            "支付次数",

            "会员渠道",

            "完成时间",

            "直推/裂变"

        ]


    ]





    print(

        "最终数据:",

        len(df)

    )





    sh=client.open_by_key(

        SHEET_ID

    )



    ws=sh.worksheet(

        WORKSHEET_NAME

    )





    print(

        "清空旧Sheet"

    )


    ws.clear()





    values=[


        df.columns.tolist()


    ] + df.astype(str).values.tolist()






    # 自动调整大小

    ws.resize(

        rows=len(values),

        cols=len(values[0])

    )






    print(

        "开始上传..."

    )



    batch_size=50000




    for i in range(

        0,

        len(values),

        batch_size

    ):



        part=values[

            i:i+batch_size

        ]



        start=i+1



        end=start+len(part)-1




        print(

            f"上传 {start}-{end}"

        )



        ws.update(

            range_name=f"A{start}",

            values=part,

            value_input_option="USER_ENTERED"

        )






    print(

        "✅ 三方充值上传完成"

    )








# ==================================================
# MAIN
# ==================================================

if __name__ == "__main__":



    print(

        "\n🚀 三方充值开始"

    )



    start=time.time()






    # 巴西昨天

    day=get_brazil_yesterday()



    print(

        "🇧🇷 日期:",

        day

    )







    # 创建导出

    create_time=create_export(

        day

    )






    print(

        "等待导出..."

    )



    export_id=wait_export(

        create_time

    )



    print(

        "Export ID:",

        export_id

    )






    # CSV

    csv_url=get_csv_url(

        export_id

    )



    print(

        csv_url

    )






    # 处理数据

    df=process_recharge(

        csv_url

    )






    # 上传

    upload_google(

        df

    )






    cost=round(

        time.time()-start,

        2

    )



    print(

        "\n🎉 全部完成"

    )


    print(

        "耗时:",

        cost,

        "秒"

    )
