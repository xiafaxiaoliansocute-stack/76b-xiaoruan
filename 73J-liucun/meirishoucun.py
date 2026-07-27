import warnings
warnings.filterwarnings("ignore")
import requests
import json
import pandas as pd
import time
import numpy as np
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import sqlite3

from io import BytesIO



# =============================
# CONFIG
# =============================

TOKEN = "o921nizs805o4tcxzk80rd1les6uzf6dt27av6k1"

ACCOUNT = "xiaoruan15016"

TENANT_ID = 1634560

REGION_ID = 1



# 第一次同步日期

FIRST_DATE = "2026-07-24"

# =============================
# API地址
# =============================

USERDAY_API = (

    "https://api5.v-n-r-1.com/api/backend/trpc/userDay.list"

)


EXPORT_LIST_API = (

    "https://api5.v-n-r-1.com/api/backend/trpc/exportData.list"

)


DOWNLOAD_API = (

    "https://api5.v-n-r-1.com/api/backend/trpc/exportData.download"

)

# =============================
# HEADERS
# =============================

headers = {


    "account":

        ACCOUNT,


    "authorization":

        f"Bearer {TOKEN}",


    "fingerprint-id":

        "dAuuHs0kUqzUjz3Dnv1i",


    "client-language":

        "zh-CN",


    "content-type":

        "application/json",


    "origin":

        "https://admin-15016-e3adb6.y-7-l-x.com",


    "referer":

        "https://admin-15016-e3adb6.y-7-l-x.com/",


    "x-admin-host":

        "admin-15016-e3adb6.y-7-l-x.com",


    "user-agent":

        "Mozilla/5.0"

}


# =============================
# TRPC GET
# =============================

def get_api(url, payload):


    params = {


        "input":

            json.dumps(

                {

                    "json": payload

                },

                separators=(",", ":")

            )

    }



    r = requests.get(

        url,

        params=params,

        headers=headers,

        timeout=60

    )


    r.raise_for_status()


    return r.json()

# =============================
# 获取SQLite最后日期
# =============================

def get_last_db_date():

    db = Path(__file__).parent / "73j.db"

    # Chưa có database
    if not db.exists():
        return None

    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT MAX(统计时间)
            FROM shouchong
        """)

        last = cursor.fetchone()[0]

    except sqlite3.OperationalError:
        # Chưa có bảng shouchong
        last = None

    conn.close()

    return last
# =============================
# 获取需要同步日期
# =============================

def get_need_days():

    brazil_today = datetime.now(
        ZoneInfo("America/Sao_Paulo")
    ).date()

    end_date = (
        brazil_today - timedelta(days=1)
    ).strftime("%Y-%m-%d")

    last = get_last_db_date()

    if last:
        start_date = (
            datetime.strptime(last, "%Y-%m-%d")
            + timedelta(days=1)
        ).strftime("%Y-%m-%d")
    else:
        start_date = FIRST_DATE

    print("CSV最后日期:", last)
    print("开始:", start_date)
    print("结束:", end_date)

    days = []

    current = datetime.strptime(
        start_date,
        "%Y-%m-%d"
    )

    end = datetime.strptime(
        end_date,
        "%Y-%m-%d"
    )

    while current <= end:

        days.append(
            current.strftime("%Y-%m-%d")
        )

        current += timedelta(days=1)

    return days

# =============================
# 创建导出任务
# =============================

def create_export(day):


    print(
        "🚀 创建:",
        day
    )


    tomorrow = (

        datetime.strptime(

            day,

            "%Y-%m-%d"

        )

        +

        timedelta(days=1)

    ).strftime(

        "%Y-%m-%d"

    )



    payload = {


        "valueType":

            "phone",


        "isRecharge":

            True,


        "queryTime":

            day,


        "type":

            "normal",


        "regionId":

            REGION_ID,


        "tenantId":

            TENANT_ID,


        "firstRechargeStartTime":

            f"{day}T03:00:00.000Z",


        "firstRechargeEndTime":

            f"{tomorrow}T02:59:59.999Z",


        "queryData": [],


        "queryType":

            "export"

    }



    get_api(

        USERDAY_API,

        payload

    )


    print(

        "✅ 创建成功"

    )





# =============================
# 获取导出ID
# =============================

def get_export_id(day):


    data = get_api(

        EXPORT_LIST_API,

        {

            "page":1,

            "pageSize":200,

            "regionId":REGION_ID,

            "tenantId":TENANT_ID

        }

    )



    items = (

        data["result"]

        ["data"]

        ["json"]

        ["exportDataList"]

    )



    items = sorted(

        items,

        key=lambda x:x["id"],

        reverse=True

    )



    for item in items:


        if (

            item.get("moduleType")

            ==

            "UserDayData"


            and


            f"查询时间:{day}"

            in item.get(

                "remark",

                ""

            )

        ):


            print(

                "找到任务:",

                item["id"],

                item["status"]

            )


            return item["id"]



    return None





# =============================
# 查询状态
# =============================

def check_status(export_id):


    data = get_api(

        EXPORT_LIST_API,

        {

            "page":1,

            "pageSize":200,

            "regionId":REGION_ID,

            "tenantId":TENANT_ID

        }

    )


    items = (

        data["result"]

        ["data"]

        ["json"]

        ["exportDataList"]

    )



    for item in items:


        if item["id"] == export_id:


            return item["status"]



    return None





# =============================
# 等待导出完成
# =============================

def wait_finish(day):


    for i in range(60):


        export_id = get_export_id(day)



        if export_id:


            status = check_status(

                export_id

            )


            print(

                "状态:",

                status

            )



            if status == "ExportSuccess":


                return export_id



        print(

            "等待:",

            i+1,

            "/60"

        )


        time.sleep(10)



    return None





# =============================
# 下载CSV到内存
# 不写入电脑
# =============================

def download_csv(export_id, day):


    print(

        "⬇️ 下载:",

        day

    )



    r = requests.post(

        DOWNLOAD_API,

        headers=headers,

        json={


            "json":{


                "tenantId":

                    TENANT_ID,


                "id":

                    export_id

            }

        },

        timeout=60

    )



    data = r.json()



    url = (

        data["result"]

        ["data"]

        ["json"]

        ["filePath"]

    )



    print(

        "下载地址:",

        url

    )



    # 直接内存读取

    content = requests.get(

        url,

        timeout=180

    ).content



    return content

# =============================
# 写入 Google Sheet
# 从 A2 开始
# 不写标题
# 每天间隔1行
# =============================

def save_db(csv_content, day):

    print(
        "📥 写入Sheet:",
        day
    )


    df = pd.read_csv(
        BytesIO(csv_content),
        encoding="utf-8"
    )


    print("CSV字段:")
    print(df.columns.tolist())


    user_col = None
    invite_col = None
    channel_col = None


    # 自动识别字段

    for c in df.columns:

        name = str(c).lower()


        if name in [
            "userid",
            "user_id",
            "会员id",
            "用户id"
        ]:
            user_col = c


        elif name in [
            "inviteid",
            "invite_id",
            "邀请id"
        ]:
            invite_col = c


        elif name in [
            "channelname",
            "channel",
            "渠道"
        ]:
            channel_col = c



    print(
        "识别:",
        user_col,
        invite_col,
        channel_col
    )



    # =============================
    # 生成字段
    # =============================

    df["会员id"] = (
        df[user_col]
        if user_col
        else ""
    )


    df["邀请id"] = (
        df[invite_col]
        if invite_col
        else ""
    )


    df["渠道"] = (
        df[channel_col]
        if channel_col
        else ""
    )



    # 判断类型

    def check_type(row):

        invite = str(
            row["邀请id"]
        ).strip()


        if invite in [
            "",
            "nan",
            "None"
        ]:

            return "直推"


        return "裂变"



    df["类型"] = df.apply(
        check_type,
        axis=1
    )



    # 添加日期

    if "统计时间" in df.columns:
        df["统计时间"] = day
    else:
     df.insert(
        0,
        "统计时间",
        day
    )
        
    # 最终5列

    df = df[
        [
            "统计时间",
            "会员id",
            "邀请id",
            "渠道",
            "类型"
        ]
    ]
    df = df.replace(    
        [np.inf, -np.inf],
    ""
)
    df = df.fillna("")
    db = Path(__file__).parent / "73j.db"

    conn = sqlite3.connect(db)
    conn.execute("""
CREATE TABLE IF NOT EXISTS shouchong (
    统计时间 TEXT,
    会员id TEXT,
    邀请id TEXT,
    渠道 TEXT,
    类型 TEXT,
    PRIMARY KEY (统计时间, 会员id)
)
""")
    rows = df.values.tolist()
    conn.executemany("""INSERT OR IGNORE INTO shouchong
(
    统计时间,
    会员id,
    邀请id,
    渠道,
    类型
)
VALUES (?, ?, ?, ?, ?)
""", rows)
    added = conn.total_changes
    conn.commit()
    conn.close()
    print(f"✅ 保存 SQLite，新增 {added} 条")
   

    del df
    del csv_content

# =============================
# MAIN
# =============================

if __name__ == "__main__":



    days = get_need_days()



    if not days:


        print(

            "✅ 数据已经最新"

        )


        exit()



    print(

        "需要更新:",

        days

    )



    for day in days:



        try:



            # 创建导出

            create_export(day)



            # 等待完成

            export_id = wait_finish(day)



            if export_id:



                # 下载到内存

                csv_content = download_csv(
                    export_id,
                    day
                )
                save_db(
                    csv_content,
                    day
                )


            else:


                print(

                    "❌ 导出失败:",

                    day

                )



        except Exception as e:


            print(

                "❌ 错误:",

                e

            )



    print(

        "\n🎉 全部更新完成"

    )