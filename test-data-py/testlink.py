import requests
import json
import gspread
import time


from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


from google.oauth2.service_account import Credentials





# ==================================================
# CONFIG
# ==================================================

TENANT_ID = 2654039

REGION_ID = 1


ACCOUNT = "xiaoruan16021"


TOKEN = "40c2mcwk81wlcw6vs7unbh66f8qv98xa4pn2bhlv"


FINGERPRINT_ID = "6hUecf0K0ity09A0YcED"



HOST = (
    "admin-16021-9fab47.c-9-m-1.com"
)


ORIGIN = (
    "https://admin-16021-9fab47.c-9-m-1.com"
)





# ==================================================
# API
# ==================================================

DAY_REPORT_URL = (

    "https://api6.o-9-d-4.com/api/backend/trpc/channel.dayReportList"

)



RETENTION_URL = (

    "https://api6.o-9-d-4.com/api/backend/trpc/channel.dayRetention"

)



# 每次 batch
BATCH_SIZE = 50






# ==================================================
# GOOGLE SHEET
# ==================================================

CREDENTIALS_FILE = (

    "/Users/xiaoruan/Documents/data_get/credentials.json"

)



SHEET_ID = (

    "1gfsTt_nL0wK2mepUAXkBgRqZHLYRY3xqWmbAxkzp0ao"

)



SHEET_NAME = "留存1"







# ==================================================
# DATE
# ==================================================

BRAZIL_TZ = ZoneInfo(
    "America/Sao_Paulo"
)



now_brazil = datetime.now(
    BRAZIL_TZ
)



OPEN_DAY = datetime(
    2026,
    7,
    7
).date()



END_DAY = (

    now_brazil.date()

    -

    timedelta(days=1)

)



print(
    "🇧🇷 Brazil:",
    now_brazil
)


print(
    "数据范围:",
    OPEN_DAY,
    "→",
    END_DAY
)






# ==================================================
# HEADERS
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
        HOST,


    "origin":
        ORIGIN,


    "referer":
        ORIGIN + "/",


    "user-agent":
        "Mozilla/5.0"

}
# ==================================================
# 获取渠道列表
# ==================================================

def get_channels(day):


    result = []

    page = 1



    while True:


        payload = {


            "json":{


                "time": str(day),


                "tenantId": TENANT_ID,


                "regionId": REGION_ID,


                "channelId": [],


                "page": page,


                "pageSize": 500,



                "order":[


                    {

                        "key":"channelId",

                        "type":"desc"

                    },


                    {

                        "key":"isOfficial",

                        "type":"desc"

                    }


                ]

            }

        }




        print(
            "\n请求 PAGE:",
            page
        )



        try:


            r = requests.get(


                DAY_REPORT_URL,


                params={


                    "input":

                    json.dumps(

                        payload,

                        separators=(',',':')

                    )

                },


                headers=HEADERS,


                timeout=60

            )


            data = r.json()



        except Exception as e:


            print(
                "API错误:",
                e
            )

            break






        js = (

            data

            .get("result",{})

            .get("data",{})

            .get("json",{})

        )



        rows = js.get(
            "reportList",
            []
        )



        total = js.get(
            "total",
            0
        )





        if not rows:

            break





        print(

            "数量:",

            len(rows),

            "| FIRST:",

            rows[0].get("channelId"),

            "| LAST:",

            rows[-1].get("channelId")

        )




        result.extend(rows)



        if len(result) >= total:

            break



        page += 1





    # 去重

    unique = {}



    for item in result:


        cid = item.get(
            "channelId"
        )


        if cid:

            unique[cid] = item





    channels = list(
        unique.values()
    )



    print(
        "唯一channel数量:",
        len(channels)
    )



    return channels







# ==================================================
# Batch 获取 retention
# ==================================================

def get_retention_batch(

        channel_ids,

        start_day,

        end_day,

        parent_type

):



    payload = {


        "json":{


            "tenantId": TENANT_ID,


            "regionId": REGION_ID,


            "channelIds": channel_ids,


            "startTime": str(start_day),


            "endTime": str(end_day),


            "type":"recharge",


            "parentType":parent_type,


            "page":1,


            "pageSize":5000,


            "order":[


                {

                    "key":"time",

                    "type":"desc"

                }

            ],


            "timeType":"days_90",


            "retentionDays":[


                0,

                1,

                2,

                3,

                4,

                5,

                6,

                9,

                13,

                29,

                59

            ]

        }

    }




    for retry in range(3):


        try:


            time.sleep(0.5)



            r = requests.get(


                RETENTION_URL,


                params={


                    "input":

                    json.dumps(

                        payload,

                        separators=(',',':')

                    )

                },


                headers=HEADERS,


                timeout=180

            )




            data = r.json()



            result = (

                data

                .get("result",{})

                .get("data",{})

                .get("json",{})

                .get("data",{})

                .get("retentionList",[])

            )




            if result:


                return result





            print(

                "返回为空 retry",

                retry+1

            )


            time.sleep(3)



        except Exception as e:


            print(

                "batch错误",

                retry+1,

                e

            )


            time.sleep(3)




    return []
# ==================================================
# 批量获取 retention
# ==================================================

def batch_get_retention(

        channels,

        parent_type

):


    result = {}



    channel_ids = [

        x["channelId"]

        for x in channels

    ]



    print(

        "\n开始获取:",

        parent_type,

        "channel:",

        len(channel_ids)

    )




    batches = [

        channel_ids[i:i+BATCH_SIZE]

        for i in range(

            0,

            len(channel_ids),

            BATCH_SIZE

        )

    ]




    for index, batch in enumerate(batches):


        print(

            parent_type,

            "batch",

            index + 1,

            "/",

            len(batches),

            "数量:",

            len(batch)

        )




        rows = get_retention_batch(

            batch,

            OPEN_DAY,

            END_DAY,

            parent_type

        )



        print(

            "返回数量:",

            len(rows)

        )



        # ==============================
        # 单channel API 才 có channelId
        # ==============================

        for item in rows:


            cid = item.get(

                "channelId"

            )



            if cid:


                result[cid] = item






    print(

        parent_type,

        "完成:",

        len(result)

    )



    return result








# ==================================================
# 找某一天数据
# ==================================================

def find_day_data(

        data,

        day

):


    if not data:

        return {}



    target = str(day)



    for item in data:


        if item.get("time") == target:


            return item



    return {}








# ==================================================
# 百分比
# ==================================================

def percent(

        a,

        b

):


    if not b:

        return 0



    return round(

        a / b,

        4

    )
# ==================================================
# 生成全部数据
# ==================================================

def get_all_data():


    print(
        "🚀 开始获取渠道"
    )



    channels = get_channels(

        END_DAY

    )



    print(

        "最终渠道数量:",

        len(channels)

    )





    # ===============================
    # 获取三种类型
    # ===============================


    none_data = batch_get_retention(

        channels,

        "none"

    )



    direct_data = batch_get_retention(

        channels,

        "direct"

    )



    split_data = batch_get_retention(

        channels,

        "split"

    )





    print(

        "开始生成数据"

    )



    rows=[]



    day = OPEN_DAY




    while day <= END_DAY:



        for channel in channels:



            cid = channel["channelId"]





            total = find_day_data(

                none_data.get(cid),

                day

            )



            direct = find_day_data(

                direct_data.get(cid),

                day

            )



            split = find_day_data(

                split_data.get(cid),

                day

            )





            total_count = total.get(

                "count",

                0

            )



            direct_count = direct.get(

                "count",

                0

            )



            split_count = split.get(

                "count",

                0

            )




            recharge = round(

                total.get(

                    "recharge",

                    0

                )

                /

                100,

                2

            )






            row=[


                str(day),


                channel.get(

                    "channelName",

                    ""

                ),


                total_count,


                direct_count,


                split_count,


                recharge,



                # 复充率

                percent(

                    total.get(

                        "repeatCount",

                        0

                    ),

                    total_count

                ),



                # 2日

                percent(

                    total.get(

                        "count1",

                        0

                    ),

                    total_count

                ),



                # 3日

                percent(

                    total.get(

                        "count2",

                        0

                    ),

                    total_count

                ),



                # 7日

                percent(

                    total.get(

                        "count6",

                        0

                    ),

                    total_count

                ),



                # 30日

                percent(

                    total.get(

                        "count29",

                        0

                    ),

                    total_count

                )

            ]




            rows.append(row)






        day += timedelta(days=1)





    print(

        "生成数据行:",

        len(rows)

    )



    return rows







# ==================================================
# 上传 Google Sheet
# ==================================================

def upload_sheet(rows):


    print(

        "开始连接 Google Sheet"

    )



    scope=[


        "https://www.googleapis.com/auth/spreadsheets",


        "https://www.googleapis.com/auth/drive"

    ]





    creds = Credentials.from_service_account_file(

        CREDENTIALS_FILE,

        scopes=scope

    )




    client = gspread.authorize(

        creds

    )




    ws = client.open_by_key(

        SHEET_ID

    ).worksheet(

        SHEET_NAME

    )





    ws.update(

        range_name="A3",

        values=rows,

        value_input_option="USER_ENTERED"

    )





    print(

        "✅ Google Sheet更新完成"

    )









# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":



    print(

        "\n🚀 程序开始运行"

    )



    start=time.time()





    rows=get_all_data()




    print(

        "\n准备上传行数:",

        len(rows)

    )





    print(

        "\n========== 数据预览 =========="

    )



    for r in rows[:5]:


        print(r)




    print(

        "=============================="

    )






    upload_sheet(

        rows

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