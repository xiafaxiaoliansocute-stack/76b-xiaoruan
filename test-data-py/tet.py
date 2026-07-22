import requests
import json
import time


from datetime import datetime, timedelta
from zoneinfo import ZoneInfo





# ==================================================
# CONFIG
# ==================================================

TENANT_ID = 2654039

REGION_ID = 1


ACCOUNT = "xiaoruan16021"


TOKEN = "40c2mcwk81wlcw6vs7unbh66f8qv98xa4pn2bhlv"


FINGERPRINT_ID = "6hUecf0K0ity09A0YcED"



RETENTION_URL = (
    "https://api6.o-9-d-4.com/api/backend/trpc/channel.dayRetention"
)



HOST = (
    "admin-16021-9fab47.c-9-m-1.com"
)


ORIGIN = (
    "https://admin-16021-9fab47.c-9-m-1.com"
)





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
        HOST,


    "origin":
        ORIGIN,


    "referer":
        ORIGIN + "/",


    "user-agent":
        "Mozilla/5.0"

}







# ==================================================
# DATE
# ==================================================

BRAZIL_TZ = ZoneInfo(
    "America/Sao_Paulo"
)



now = datetime.now(
    BRAZIL_TZ
)



START_DAY = (
    now.date()
    -
    timedelta(days=90)
)



END_DAY = (
    now.date()
    -
    timedelta(days=1)
)





print(
    "🇧🇷 Brazil:",
    now
)


print(
    "日期:",
    START_DAY,
    "→",
    END_DAY
)









# ==================================================
# 测试 batch retention
# ==================================================

def get_retention_batch(
        channel_ids,
        parent_type
):


    payload = {


        "json":{


            "tenantId":TENANT_ID,


            "regionId":REGION_ID,



            # ⭐ 关键
            "channelIds":channel_ids,



            "startTime":
                str(START_DAY),



            "endTime":
                str(END_DAY),




            "type":
                "recharge",




            "parentType":
                parent_type,



            "page":
                1,



            "pageSize":
                500,



            "order":[


                {

                    "key":"time",

                    "type":"desc"

                }

            ],




            "timeType":
                "days_90",





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





    print(
        "\n请求channel数量:",
        len(channel_ids)
    )


    print(
        "channelIds:",
        channel_ids
    )





    try:


        r=requests.get(


            RETENTION_URL,


            params={


                "input":
                json.dumps(

                    payload,

                    separators=(',',':')

                )

            },


            headers=HEADERS,


            timeout=120


        )



        print(
            "HTTP:",
            r.status_code
        )



        data=r.json()



        print(
            json.dumps(
                data,
                ensure_ascii=False
            )[:1000]
        )




        result=(

            data
            .get("result",{})
            .get("data",{})
            .get("json",{})
            .get("data",{})
        )



        print(
            "\n返回key:"
        )


        print(
            result.keys()
            if isinstance(result,dict)
            else result
        )




        retention=result.get(
            "retentionList",
            []
        )



        print(
            "\nretention数量:",
            len(retention)
        )



        return retention





    except Exception as e:


        print(
            "错误:",
            e
        )


        return []









# ==================================================
# RUN TEST
# ==================================================

if __name__=="__main__":



    # 测试50个channel

    test_channels=[


        7301,

        7302,

        7303,

        7304,

        7305,

        7306,

        7307,

        7308,

        7309,

        7310,


        7311,

        7312,

        7313,

        7314,

        7315,

        7316,

        7317,

        7318,

        7319,

        7320,


        7321,

        7322,

        7323,

        7324,

        7325,

        7326,

        7327,

        7328,

        7329,

        7330,


        7331,

        7332,

        7333,

        7334,

        7335,

        7336,

        7337,

        7338,

        7339,

        7340,


        7341,

        7342,

        7343,

        7344,

        7345,

        7346,

        7347,

        7348,

        7349,

        7350

    ]




    data=get_retention_batch(

        test_channels,

        "none"

    )



    print(

        "\n测试完成"

    )


    print(

        "返回数据长度:",
        len(data)

    )