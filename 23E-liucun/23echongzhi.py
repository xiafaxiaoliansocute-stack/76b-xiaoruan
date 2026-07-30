import warnings
warnings.filterwarnings("ignore")
import requests
import json
import time
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
import sqlite3



# ==================================================
# API CONFIG
# ==================================================

TOKEN = "756gxn1uyot52rydkfovc4bw63w38p5ykqtak13z"
ACCOUNT = "xiaoruan16028"
TENANT_ID = 9503839
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
        "admin-16028-5acf36.c-9-m-1.com",


    "client-language":
        "zh-CN",


    "content-type":
        "application/json"

}


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

    create_time=create_export(day)

    # 等待系统写入exportData.list
    
    print("⏳ 等待5秒，让导出任务写入列表...")

    time.sleep(5)

    print("等待导出...")

    export_id=wait_export(create_time)



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
    print(
    "保存日期:",
    df["完成时间"].unique()
)

    # 保存CSV
    db = Path(__file__).parent / "23E.db"
    conn = sqlite3.connect(db)
    conn.execute("""CREATE TABLE IF NOT EXISTS recharge (
    完成时间 TEXT,
    会员id TEXT,
    支付金额 INTEGER,
    会员渠道 TEXT,
    支付次数 INTEGER,
    PRIMARY KEY (完成时间, 会员id)
)
""")
    conn.execute("DELETE FROM recharge"
)
    df["支付金额"] = df["支付金额"].astype(int)

    rows = df[
    [
        "完成时间",
        "会员id",
        "支付金额",
        "会员渠道",
        "支付次数"
    ]].values.tolist()
    conn.executemany("""
INSERT INTO recharge
(
    完成时间,
    会员id,
    支付金额,
    会员渠道,
    支付次数
)
VALUES (?, ?, ?, ?, ?)
""", rows)
    
    
    added = len(rows)

    conn.commit()
    conn.close()
    print(f"✅ 保存 SQLite，新增 {added} 条")

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
