# ==========================================================
# # JS 团队每日全局报表
# Multi Website Version
# Author: ChatGPT
# ==========================================================
import warnings
warnings.filterwarnings("ignore")
import json
import requests
import gspread
import pandas as pd
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials
from concurrent.futures import ThreadPoolExecutor, as_completed


# ==========================================================
# GOOGLE SHEET
# ==========================================================

CREDENTIALS_FILE =  "/Users/xiaoruan/Documents/service_account.json"

SHEET_ID = "1gfsTt_nL0wK2mepUAXkBgRqZHLYRY3xqWmbAxkzp0ao"

SHEET_NAME = "j88后台汇总"

scope = [

    "https://www.googleapis.com/auth/spreadsheets",

    "https://www.googleapis.com/auth/drive"

]

creds = Credentials.from_service_account_file(

    CREDENTIALS_FILE,

    scopes=scope

)

client = gspread.authorize(creds)

worksheet = client.open_by_key(

    SHEET_ID

).worksheet(

    SHEET_NAME

)

# ==========================================================
# THÊM WEB MỚI CHỈ CẦN THÊM THÔNG TIN ĐÀI 
# Chỉ sửa phần này
# ==========================================================

WEBS = [
    {
        "name":"15016-73J",
        "api":"https://api5.v-n-r-1.com",
        "tenantId":1634560,
        "token":"z5hwwpepikzhyao7ahiyxz0b3t5aa0vihsmi1irl",
        "account":"jqr73j",
        "adminHost":"admin-15016-e3adb6.y-7-l-x.com"
    },

   {
        "name":"16028-23E",
        "api":"https://api6.o-9-d-4.com",
        "tenantId":9503839,
        "token":"90saqtoejqtziugu7771nlzn66k4febmoce4k76b",
        "account":"jiqiren23e",
        "adminHost":"admin-16028-5acf36.c-9-m-1.com"
    },

    {
        "name":"16021-23A",
        "api":"https://api6.o-9-d-4.com",
        "tenantId":2654039,
        "token":"vv3d83jp99w0n3pjl5jxd7jmmkosu32gst15l9fa",
        "account":"23aa",
        "adminHost":"admin-16021-9fab47.c-9-m-1.com"
    },

    {
        "name":"16011-NN22",
        "api":"https://api6.o-9-d-4.com",
        "tenantId":2175621,
        "token":"jp1249qg9f47jwealsc7gdnc250lgyq4zkfz3nxu",
        "account":"nn22",
        "adminHost":"admin-16011-34bc8f.c-9-m-1.com"
    },
    {
        "name":"2306-76B",
        "api":"https://api3.a-b-c-5.com",
        "tenantId":5317688,
        "token":"2saobx3un5x7kbbplypl8ej0w1b9itfnkh4r18io",
        "account":"xiaoruan2306",
        "adminHost":"admin-2306-66b1c5.m-b-d-1.com"
    },
    {
        "name":"2300-5BBB",
        "api":"https://api3.a-b-c-5.com",
        "tenantId":1530143,
        "token":"0kaonw5gfuesnsv5o8tcp7je0qfhqdg0w26ttdec",
        "account":"xiaoruan2300",
        "adminHost":"admin-2300-68f8c3.m-b-d-1.com"
    },
    {
        "name":"2527-XXX7",
        "api":"https://api5.v-n-r-1.com",
        "tenantId":2730566,
        "token":"x1a0fecyl3arx2e20ub3jh4xbp54ef8nwuv7bnxd",
        "account":"xiaoruan2527",
        "adminHost":"admin-2527-351324.y-7-l-x.com"
    } ,
    {
        "name":"15008-WW33",
        "api":"https://api5.v-n-r-1.com",
        "tenantId":9930159,
        "token":"c6zmciqrqs963q0myotq2lhitfrvm2alzygbut9p",
        "account":"xiaoruan15008",
        "adminHost":"admin-15008-7b9c73.y-7-l-x.com"
    },
    {
        "name":"2502-55UU",
        "api":"https://api5.v-n-r-1.com",
        "tenantId":1823786,
        "token":"0qdah3s68h49gr21ik4kc74aoja6syb1y5pksgey",
        "account":"xiaoruan2502",
        "adminHost":"admin-2502-29b1ef.y-7-l-x.com"
    },
    {
        "name":"2515-EE44",
        "api":"https://api5.v-n-r-1.com",
        "tenantId":7113392,
        "token":"u70ohpl8uxhi0vyjif51z37c98mpjot2292xlvgr",
        "account":"xiaoruan2515",
        "adminHost":"admin5-2515-67db94.y-7-l-x.com"
    },
    {
        "name":"720-BB22",
        "api":"https://api4.i-j-k-8.com",
        "tenantId":6247284,
        "token":"dtb9uff6er7bjzcia4zn5nj6lq9b5xs4stfsubpg",
        "account":"xiaoruan720",
        "adminHost":"admin4-720-05ec73.m-9-y-j.com"
    },
    {
        "name":"2409-7JJJ",
        "api":"https://api4.i-j-k-8.com",
        "tenantId":5416567,
        "token":"txl9o3kit0m70883znb3ijib4n6fvcbz4js75poe",
        "account":"xiaoruan2409",
        "adminHost":"admin-2409-56df41.m-9-y-j.com"
    },
    {
        "name":"2501-XX11",
        "api":"https://api5.v-n-r-1.com",
        "tenantId":9933402,
        "token":"je4v9kssehuel8oofuxk0fen99lqstxhzg63oos0",
        "account":"xiaoruan2501",
        "adminHost":"admin-2501-a5aaf3.y-7-l-x.com"
    },
    {
        "name":"928-44WW",
        "api":"https://api5.v-n-r-1.com",
        "tenantId":4552161,
        "token":"0mntlei1x27w62236mm9nh3hssw1mrhe9dt6iits",
        "account":"xiaoruan928",
        "adminHost":"admin5-928-mdywmz.y-7-l-x.com"
    },
    {
        "name":"923-33NN",
        "api":"https://api5.v-n-r-1.com",
        "tenantId":4077356,
        "token":"j88x07eqbtdmg28z3sj04abuvu0sj0ygnuwi3qpe",
        "account":"xiaoruan923",
        "adminHost":"admin5-923-nevem0.y-7-l-x.com"
    },
    {
        "name":"913-RR66",
        "api":"https://api5.v-n-r-1.com",
        "tenantId":1803215,
        "token":"e86szunet2emq2x37nc63htqsgtwta3pod8893d2",
        "account":"xiaoruan913",
        "adminHost":"admin5-913-67b575.y-7-l-x.com"
    },
    {
        "name":"915-KK44",
        "api":"https://api5.v-n-r-1.com",
        "tenantId":4379055,
        "token":"qnpbnr4n82xar36iw6c6yklaecyo5p30d6x9plh9",
        "account":"xiaoruan915",
        "adminHost":"admin5-915-9b50d1.y-7-l-x.com"
    },
    {
        "name":"907-33CC",
        "api":"https://api5.v-n-r-1.com",
        "tenantId":8416670,
        "token":"rxaecel8k943n1reqeo1gffmz6y4vwwvxzxx9il9",
        "account":"xiaoruan907",
        "adminHost":"admin5-907-4c06b8.y-7-l-x.com"
    },
    {
        "name":"517-22CC",
        "api":"https://api3.a-b-c-5.com",
        "tenantId":3731525,
        "token":"5pk90mcdvnr6rnln7p61e4xo6dno9gg417j4lz3c",
        "account":"xiaoruan517",
        "adminHost":"admin3-517-47ea8f.m-b-d-1.com"
    },
    {
        "name":"713-77SS",
        "api":"https://api4.i-j-k-8.com",
        "tenantId":7597753,
        "token":"x4ozdz1da51av7tgoncrs74kdqvrmwxgp6estv2k",
        "account":"7sxiaoruan",
        "adminHost":"admin4-713-d801e1.m-9-y-j.com"
    },
    {
        "name":"707-11CC",
        "api":"https://api4.i-j-k-8.com",
        "tenantId":8109130,
        "token":"6m5kiop4qlkitrbweugxixn6mzbyo3nhehdo7ysw",
        "account":"1cxiaoruan",
        "adminHost":"admin4-707-fc85eb.m-9-y-j.com"
    },
    {
        "name":"706-99SS",
        "api":"https://api4.i-j-k-8.com",
        "tenantId":4932219,
        "token":"234itrays7gwgpbk1lkgia9hnv2hw38p2n7ftake",
        "account":"9sxiaoruan",
        "adminHost":"admin4-706-c31640.m-9-y-j.com"
    },
    {
        "name":"704-66AA",
        "api":"https://api4.i-j-k-8.com",
        "tenantId":5772945,
        "token":"s69ry2abb5kqavybzsiumdie80l6xhubz6rstg4a",
        "account":"6axiaoruan",
        "adminHost":"admin4-704-81d77a.m-9-y-j.com"
    },
    {
        "name":"650-77GG",
        "api":"https://api3.a-b-c-5.com",
        "tenantId":5031033,
        "token":"uupodaxme1dd11c8r9knz55z7nfhreu96w9xtv44",
        "account":"7gxiaoruan",
        "adminHost":"admin3-650-1361e9.m-b-d-1.com"
    },
    {
        "name":"619-77BB",
        "api":"https://api3.a-b-c-5.com",
        "tenantId":4040571,
        "token":"1m1p8xdcxp0en2cosml9gha9g680szpi2io95og7",
        "account":"77xiaoruan",
        "adminHost":"admin3-619-2ac217.m-b-d-1.com"
    }

    # WEB...

]


# ==========================================================
# chạy theo giờ lấy theo giờ brazil 
# ==========================================================

BRAZIL_TZ = ZoneInfo("America/Sao_Paulo")


def get_time():

    now = datetime.now(BRAZIL_TZ)

    query_date = (

        now - timedelta(days=1)

    ).strftime("%Y-%m-%d")


    query_day = (

        now - timedelta(days=1)

    ).date()


    start_local = datetime.combine(

        query_day,

        datetime.min.time(),

        tzinfo=BRAZIL_TZ

    )


    end_local = datetime.combine(

        query_day,

        datetime.max.time(),

        tzinfo=BRAZIL_TZ

    )


    start_time = (

        start_local

        .astimezone(ZoneInfo("UTC"))

        .strftime("%Y-%m-%dT%H:%M:%S.000Z")

    )


    end_time = (

        end_local

        .astimezone(ZoneInfo("UTC"))

        .strftime("%Y-%m-%dT%H:%M:%S.999Z")

    )


    return {

        "query_date":query_date,

        "start_time":start_time,

        "end_time":end_time

    }


TIME = get_time()

QUERY_DATE = TIME["query_date"]

START_TIME = TIME["start_time"]

END_TIME = TIME["end_time"]


print("🇧🇷 Brazil Time :",datetime.now(BRAZIL_TZ))

print("📅 Query Date :",QUERY_DATE)

# ==========================================================
# tiêu đề trình xử lý và lấy số liệu 
# ==========================================================

def make_headers(web):

    return {

        "authorization": f'Bearer {web["token"]}',

        "account": web["account"],

        "client-language": "zh-CN",

        "fingerprint-id": "6hUecf0K0ity09A0YcED",

        "x-admin-host": web["adminHost"],

        "origin": f'https://{web["adminHost"]}',

        "user-agent": "Mozilla/5.0"

    }


# ==========================================================
# THÀNH VIÊN ĐĂNG NHẬP TRONG NGÀY (PHÂN CÁC LOẠI ĐĂNG NHÂP)
# ==========================================================
APP_TYPES = {
    "全部": None,
    "安卓H5": "AndroidH5",
    "苹果H5": "iOSH5",
    "PWA": "PWA",
    "APK": "APK",
    "苹果APP": "iOSApp",
    "电脑系统": "DesktopOS",
}

def get_web_data(web):

    headers = make_headers(web)
    tenant_id = web["tenantId"]
    
    session = requests.Session()
    session.headers.update(headers)

    # ============================================
    # dashboard.tenantDaily(MỤC QUANJU-BAOBIAO)
    # ============================================

    params = {

        "input": json.dumps({

            "json": {

                "queryType":"table",

                "page":1,

                "pageSize":50,

                "tenantId":tenant_id,

                "startTime":QUERY_DATE,

                "endTime":QUERY_DATE

            }
        })
    }

    # ============================================
    # MỤC LẤY TỔNG TIỀN TOUZHU
    # ============================================

    effect_params = {

    "input": json.dumps({

        "json": {

            "minAndMaxType": "profitAmount",

            "startTime": START_TIME,

            "endTime": END_TIME,

            "startTimeByUpdate": START_TIME,

            "endTimeByUpdate": END_TIME,

            "regionId": 1,

            "tenantId": tenant_id,

            "queryType": "statistics"

        }

    })

}


    # ============================================
    # assetsChange
    # ============================================

    assets_params = {

        "input": json.dumps({

            "json":{

                "page":1,

                "pageSize":50,

                "changeTypes":[

                    "commission"

                ],

                "changeTwoTypes":[

                    "commission:receive"

                ],

                "tenantId":tenant_id,

                "regionId":1,

                "startTime":START_TIME,

                "endTime":END_TIME

            }
        })
    }

    # ============================================
    # dashboard request
    # ============================================

    print()

    print("="*60)

    print("开始获取：",web["name"])

    print("="*60)


    dashboard = requests.get(
    f'{web["api"]}/api/backend/trpc/dashboard.tenantDaily',
    params=params,
    headers=headers,
    timeout=30
)


    print(

        "dashboard:",

        dashboard.status_code

    )


    if dashboard.status_code != 200:

        print("dashboard失败")

        return None


    dashboard_json = dashboard.json()


    # ============================================
    # gameRecord
    # ============================================

    effect = requests.get(
    f'{web["api"]}/api/backend/trpc/gameRecord.list',
    params=effect_params,
    headers=headers,
    timeout=30
)


    print(

        "gameRecord:",

        effect.status_code

    )


    effect_json = effect.json()


    # ============================================
    # assetsChange
    # ============================================

    assets = requests.get(
    f'{web["api"]}/api/backend/trpc/assetsChange.list',
    params=assets_params,
    headers=headers,
    timeout=30
)


    print(

        "assetsChange:",

        assets.status_code

    )


    assets_json = assets.json()

        # ============================================
    # Login Total By AppType
    # ============================================

    login_total = {}

    for name, app_type in APP_TYPES.items():

        payload = {
            "json": {
                "queryType": "userId",
                "regionId": 1,
                "tenantId": tenant_id,
                "loginStartTime": START_TIME,
                "loginEndTime": END_TIME,
                "page": 1,
                "pageSize": 1,
                "order": [
                    {
                        "key": "",
                        "type": "desc"
                    }
                ]
            }
        }

        if app_type:
            payload["json"]["appType"] = app_type

        print(f"\n➡️ Website={web['name']} | AppType={name}")

        while True:

            try:

                r = session.get(
                    f'{web["api"]}/api/backend/trpc/user.list',
                    params={
                        "input": json.dumps(payload, separators=(",", ":"))
                    },
                    timeout=30
                )

                print(f"HTTP Status = {r.status_code}")

                # ==========================
                # Thành công
                # ==========================
                if r.status_code == 200:

                    j = r.json()

                    # Có trường hợp HTTP=200 nhưng API vẫn báo thao tác quá nhanh
                    msg = (
                        j.get("error", {})
                         .get("json", {})
                         .get("message", "")
                    )

                    if "操作太频繁" in msg:
                        print("⚠️ 操作太频繁，1 giây sau thử lại...")
                        time.sleep(1)
                        continue

                    total = (
                        j.get("result", {})
                         .get("data", {})
                         .get("json", {})
                         .get("userList", {})
                         .get("total", 0)
                    )

                    login_total[name] = total

                    print(f"✅ Total = {total}")

                    if total == 0:
                        print("⚠️ TOTAL = 0")
                        print(json.dumps(j, ensure_ascii=False, indent=2))

                    break

                # ==========================
                # HTTP 429
                # ==========================
                elif r.status_code == 429:

                    print("⚠️ 操作太频繁，3 giây sau thử lại...")

                    time.sleep(3)

                    continue

                # ==========================
                # Lỗi khác
                # ==========================
                else:

                    print(f"❌ HTTP ERROR {r.status_code}")
                    print(r.text)

                    login_total[name] = 0

                    break

            except Exception as e:

                print("💥 EXCEPTION")
                print(type(e).__name__)
                print(e)

                time.sleep(1)

    return {
        "dashboard": dashboard_json,
        "effect": effect_json,
        "assets": assets_json,
        "login_total": login_total
    }
# ==========================================================
# PHÂN TÍCH SỐ CHIA CHO 100
# ==========================================================

NEED_COLUMNS = [

    "site",
    "time",
    "registerCount",
    "betCount",
    "firstRechargeCount",
    "subFirstRechargeCount",
    "rechargeCount",
    "firstRechargeAmount",
    "subFirstRechargeAmount",
    "rechargeAmount",
    "withdrawAmount",
    "circulationAmount",
    "validBetAmount",
    "profitAmount",
    "discountAmount",
    "commission",
    "receiveCommission",
    "total",
    "redeemCode",
    "redPacket",
    "dailyAssistance",
    "weeklyAssistance",
    "firstRecharge",
    "assistanceCash",
    "sumRecharge",
    "agency",
    "manualGift",
    "rebate",
    "memberReward",
    "mysteryReward",
    "vip",
    "newbieTaskReward",
    "inviteReward",
    "registerReward",
    "signInVolumeReward",
    "firstRechargeRebate",
    "firstWithdrawRebate",
    "rechargeBonus",
    "全部登录",
    "安卓H5",
    "苹果H5",
    "PWA",
    "APK",
    "苹果APP",
    "电脑系统"

]

# ==========================================================
# PHÂN TÍCH KHÔNG CHIA CHO 100
# ==========================================================

NO_DIVIDE = [

    "time",
    "total",
    "registerCount",
    "betCount",
    "validBetAmount",
    "firstRechargeCount",
    "subFirstRechargeCount",
    "rechargeCount",
    "全部登录",
    "安卓H5",
    "苹果H5",
    "PWA",
    "APK",
    "苹果APP",
    "电脑系统"

]
# ==========================================================
# ĐIỀU CHỈNH Ô CẦN LẤY TỪ Ô NÀO ĐẾN Ô NÀO 
# ==========================================================

GROUPS = [

    {
        "start": "A",
        "columns": [
            "site",
            "time",
            "registerCount",
            "betCount",
            "firstRechargeCount",
            "subFirstRechargeCount",
            "rechargeCount"
        ]
    },

    {
        "start": "I",
        "columns": [
            "firstRechargeAmount",
            "subFirstRechargeAmount",
            "rechargeAmount",
            "withdrawAmount",
            "circulationAmount"
        ]
    },

    {
        "start": "T",
        "columns": [
            "validBetAmount",
            "profitAmount"
        ]
    },

    {
    "start": "AD",
    "columns": [
    "discountAmount",
    "commission",
    "receiveCommission",
    "total",
    "redeemCode",
    "redPacket",
    "dailyAssistance",
    "weeklyAssistance",
    "firstRecharge",
    "assistanceCash",
    "sumRecharge",
    "agency",
    "manualGift",
    "rebate",
    "memberReward",
    "mysteryReward",
    "vip",
    "newbieTaskReward",
    "inviteReward",
    "registerReward",
    "signInVolumeReward",
    "firstRechargeRebate",
    "firstWithdrawRebate",
    "rechargeBonus",
    "全部登录",
    "安卓H5",
    "苹果H5",
    "PWA",
    "APK",
    "苹果APP",
    "电脑系统"
        ]
    }

]

# ==========================================================
# JSON -> DATAFRAME
# ==========================================================

def build_dataframe(data, web):

    dashboard = data["dashboard"]
    effect = data["effect"]
    assets = data["assets"]
    login_total = data["login_total"]

    rows = dashboard["result"]["data"]["json"]

    df = pd.DataFrame(rows)


# ==========================
# Tách tên站点 và 日期
# ==========================

    df.insert(
    0,
    "site",
    "【" + str(web["name"]).replace("-", "】")
)


    df["time"] = df["time"].astype(str)

    # ==========================
    # assets total
    # ==========================
    try:
        assets_total = assets["result"]["data"]["json"]["total"]
    except (KeyError, TypeError):
        print(f"⚠️ {web['name']} không có total")
        assets_total = ""

    # ==========================
    # validBetAmount
    # ==========================
    try:
        validBetAmount = (
    effect["result"]["data"]["json"]["totalFlowAmountFix"] / 100
)
    except (KeyError, TypeError):
        print(f"⚠️ {web['name']} không có totalFlowAmountFix")
        validBetAmount = ""

    df["validBetAmount"] = validBetAmount

    df.insert(
        1,
        "total",
        assets_total
    )
    df["全部登录"] = login_total.get("全部", 0)
    df["安卓H5"] = login_total.get("安卓H5", 0)
    df["苹果H5"] = login_total.get("苹果H5", 0)
    df["PWA"] = login_total.get("PWA", 0)
    df["APK"] = login_total.get("APK", 0)
    df["苹果APP"] = login_total.get("苹果APP", 0)
    df["电脑系统"] = login_total.get("电脑系统", 0)


    df = df[NEED_COLUMNS]


    # Chia 100 cho các cột tiền
    
    for col in df.columns:
        if col in NO_DIVIDE:
            continue
        df[col] = df[col].apply(
            lambda x: x / 100 if isinstance(x, (int, float)) else x
        )
    return df

# ==========================================================
# GOOGLE SHEET 
# ==========================================================
def upload(df, start_row):
    for group in GROUPS:
        temp = df[group["columns"]]
        values = temp.values.tolist()
        worksheet.update(
            range_name=f'{group["start"]}{start_row}',
            values=values

        )
def fetch_one_web(web):

    try:

        data = get_web_data(web)

        if data is None:
            return {
                "web": web,
                "data": None
            }

        return {
            "web": web,
            "data": data
        }

    except Exception as e:

        print(
            f"❌ {web['name']} API错误:",
            e
        )

        return {
            "web": web,
            "data": None
        }        
# ==========================================================
# MAIN
# ==========================================================
def main():

    print()
    print("=" * 80)
    print("JS-团队-每日全局报表")
    print("=" * 80)


    # ==========================
    # 第一阶段
    # 并发获取API
    # ==========================

    results = []

    print("🚀 开始并发获取数据...")


    with ThreadPoolExecutor(max_workers=3) as executor:

        futures = [
            executor.submit(
                fetch_one_web,
                web
            )
            for web in WEBS
        ]


        for future in as_completed(futures):

            result = future.result()

            results.append(result)



    print()
    print("✅ API全部获取完成")


    # ==========================
    # 第二阶段
    # 顺序写Google Sheet
    # ==========================

    print()
    print("📤 开始写入Google Sheet...")


    start_row = 2
    success = 0


    # 保持WEBS原顺序
    for web in WEBS:


        item = next(
            (
                x for x in results
                if x["web"]["name"] == web["name"]
            ),
            None
        )


        if not item or item["data"] is None:

            print(
                "❌ 跳过:",
                web["name"]
            )

            start_row += 1
            continue



        try:

            df = build_dataframe(
                item["data"],
                web
            )

            upload(
                df,
                start_row
            )


            print(
                f"✅ {web['name']} 上传成功"
            )


            success += 1


        except Exception as e:

            print(
                f"❌ {web['name']} 写入失败",
                e
            )


        start_row += 1

        time.sleep(3)



    print()
    print("=" * 80)
    print("全部完成")
    print(
        "成功:",
        success,
        "/",
        len(WEBS)
    )
    print("=" * 80)
# ==========================================================
# START
# ==========================================================

if __name__ == "__main__":

    main()