import requests
import json
import gspread

from google.oauth2.service_account import Credentials


# ==================================================
# GOOGLE SHEET CONFIG
# ==================================================

CREDENTIALS_FILE = (
    "/Users/xiaoruan/Documents/data_get/credentials.json"
)

SHEET_ID = (
    "1bge9xtuFgTKkyZBFkqlGbvokhgwuEXs2Vyd0-vt53q4"
)


# ==================================================
# API PATH
# ==================================================

API_PATH = (
    "/api/backend/trpc/"
    "withdrawal.queryBatchBalance"
)


# ==================================================
# WEBS CONFIG
# 每个网站可以有不同的：
# tenant_id
# channel_ids
# channel_names
# display_order
# token
# account
# admin_host
# sheet_row
# ==================================================

WEBS = [

    # ==================================================
    # 23A
    # ==================================================

    {
        "name": "23A",

        "api_domain":
            "https://api6.o-9-d-4.com",

        "tenant_id":
            2654039,

        "channel_ids": [
            3960,
            3961,
            3962,
            3963,
            3964,
            3965,
            3966,
            3968
        ],

        "channel_names": {

            3962: "QQPAY",
            3968: "betcatpay",
            3966: "Globalpay",
            3961: "kubaopay",
            3965: "DonePay",
            3963: "univepay",
            3964: "PAY4Z",
            3960: "Bestpay"
        },

        "display_order": [
            3962,
            3968,
            3966,
            3961,
            3965,
            3963,
            3964,
            3960
        ],

        "token":
            "ajgnfuepdrbjhle6orecg93ed4yf6nds0url8cru",

        "account":
            "xiaoruan16021",

        "admin_host":
            "admin-16021-9fab47.c-9-m-1.com",

        # 标题写第2行
        # 余额写第3行
        "sheet_row":
            2
    },


    # ==================================================
    # NN22
    # 修改成 NN22 的真实信息
    # ==================================================

    {
        
        "name": "NN22",

        "api_domain":
            "https://api6.o-9-d-4.com",

        "tenant_id":
            2175621,

        "channel_ids": [
            3823,
            3824,
            3825,
            3826,
            3827,
            3828,
            3829,
            3830,
            3831
        ],

        "channel_names": {

            3823: "UNIVEPAY",
            3824: "Donepay",
            3825: "Bestpay",
            3826: "PAY4Z",
            3827: "U2C",
            3828: "Globalpay",
            3829: "QQPAY",
            3830: "KUBAO",
            3831: "betcatpay"
        },

        "display_order": [
            3823,
            3824,
            3825,
            3826,
            3827,
            3828,
            3829,
            3830,
            3831
        ],

        "token":
            "smblr04tjn6lnv6pebt82m1c3pv06bzs42vd2uaj",

        "account":
            "xiaoruan16011",

        "admin_host":
            "admin-16011-34bc8f.c-9-m-1.com",

        # 标题写第5行
        # 余额写第6行
        "sheet_row":
            4
# ==================================================
    # 76B
    # 修改成 76B 的真实信息
    # ==================================================
    },
    {
        "name": "76B",

        "api_domain":
            "https://api3.a-b-c-5.com",

        "tenant_id":
            5317688,

        "channel_ids": [
            3926,
            3927,
            3928,
            3929,
            3930,
            3931,
            3933,
            3934,
            3942
        ],

        "channel_names": {

            3926: "QQPAY",
            3927: "univepay",
            3928: "globalpay",
            3929: "PAY4Z",
            3930: "donepay",
            3931: "u2cpay",
            3933: "bestpay",
            3934: "酷宝代付",
            3942: "betcatpay"
        },

        "display_order": [
            3926,
            3927,
            3928,
            3929,
            3930,
            3931,
            3933,
            3934,
            3942
        ],

        "token":
            "svf0rhx0tomstyvp3fv78p4s35zgyimpw64r6nk6",

        "account":
            "xiaoruan2306",

        "admin_host":
            "admin-2306-66b1c5.m-b-d-1.com",

        # 标题写第5行
        # 余额写第6行
        "sheet_row":
            6
    
# ==================================================
    # 5bbb
    # 修改成 5bbb 的真实信息
    # ==================================================
    },
    {
        "name": "5BBB",

        "api_domain":
            "https://api3.a-b-c-5.com",

        "tenant_id":
            1530143,

        "channel_ids": [
            3634,
            3638,
            3639,
            3640,
            3641,
            3642,
            3643,
            3644,
            3646
        ],

        "channel_names": {

            3634: "PAY4Z",
            3638: "globalpay",
            3639: "u2cpay",
            3640: "univepay",
            3641: "酷宝",
            3642: "bestpay",
            3643: "donepay",
            3644: "QQPAY",
            3646: "betcatpay"
        },

        "display_order": [
            3634,
            3638,
            3639,
            3640,
            3641,
            3642,
            3643,
            3644,
            3646
        ],

        "token":
            "i3q5vqtlumphi5cgteqddg5do8ydtr07ls07cn1r",

        "account":
            "xiaoruan2300",

        "admin_host":
            "admin-2300-68f8c3.m-b-d-1.com",

        # 标题写第5行
        # 余额写第6行
        "sheet_row":
            8
    
    # ==================================================
    # XXX7
    # 修改成 XXX7 的真实信息
    # ==================================================
    },
    {
        "name": "XXX7",

        "api_domain":
            "https://api5.v-n-r-1.com",

        "tenant_id":
            2730566,

        "channel_ids": [
            2769,
            2770,
            2771,
            2772,
            2773,
            2774,
            2775,
            2776,
            2777,
            2778
        ],

        "channel_names": {

            2769: "UNIVEPAY",
            2770: "Bestpay",
            2771: "globalpay",
            2772: "Donepay",
            2773: "QQPAY",
            2774: "酷宝代付",
            2775: "PAY4Z",
            2776: "88pay",
            2777: "U2C代付",
            2778: "betcatpay"
        },

        "display_order": [
            2769,
            2770,
            2771,
            2772,
            2773,
            2774,
            2775,
            2776,
            2777,
            2778
        ],

        "token":
            "semd1nchirgzhdyg220hh2jxzfttm03i2dbk5n69",

        "account":
            "xiaoruan2527",

        "admin_host":
            "admin-2527-351324.y-7-l-x.com",

        # 标题写第5行
        # 余额写第6行
        "sheet_row":
            10
    
# ==================================================
    # 7JJJ
    # 修改成 7JJJ 的真实信息
    # ==================================================
    },
    {
        "name": "7JJJ",

        "api_domain":
            "https://api4.i-j-k-8.com",

        "tenant_id":
            5416567,

        "channel_ids": [
            2124,
            2125,
            2126,
            2129,
            2136,
            2137,
            2140,
            2142,
            2143,
            2243
        
        ],

        "channel_names": {

            2124: "univepay",
            2125: "PAY4Z",
            2126: "donepay",
            2129: "globalpay",
            2136: "88pay",
            2137: "qqpay",
            2140: "Bestpay",
            2142: "kppay",
            2143: "酷宝",
            2243: "betcatpay"
        },

        "display_order": [
            2124,
            2125,
            2126,
            2129,
            2136,
            2140,
            2142,
            2143,
            2243
        ],

        "token":
            "qaa960zraxw8ug732vh50iafcj4js9j1z3ffxcpw",

        "account":
            "xiaoruan2409",

        "admin_host":
            "admin-2409-56df41.m-9-y-j.com",

        # 标题写第5行
        # 余额写第6行
        "sheet_row":
            12
    }
]


# ==================================================
# GET BALANCE FUNCTION
# ==================================================

def get_web_balance(web):

    print("\n")
    print("=" * 70)

    print(
        f"正在获取 {web['name']} 三方余额..."
    )

    print("=" * 70)


    # ==================================================
    # URL
    # ==================================================

    url = (
        web["api_domain"]
        + API_PATH
    )


    # ==================================================
    # PARAMS
    # ==================================================

    params = {

        "input": json.dumps({

            "json": {

                "tenantId":
                    web["tenant_id"],

                "channelIds":
                    web["channel_ids"]

            }

        })

    }


    # ==================================================
    # HEADERS
    # ==================================================

    headers = {

        "authorization":
            f"Bearer {web['token']}",

        "account":
            web["account"],

        "client-language":
            "zh-CN",

        "content-type":
            "application/json",

        "x-admin-host":
            web["admin_host"]

    }


    # ==================================================
    # REQUEST
    # ==================================================

    try:

        response = requests.get(

            url,

            params=params,

            headers=headers,

            timeout=30

        )


        print(
            f"{web['name']} HTTP:",
            response.status_code
        )


        if response.status_code != 200:

            print(
                f"❌ {web['name']} API请求失败"
            )

            print(response.text)

            return None


        data = response.json()


    except requests.exceptions.RequestException as e:

        print(
            f"❌ {web['name']} 网络请求失败:"
        )

        print(e)

        return None


    except json.JSONDecodeError:

        print(
            f"❌ {web['name']} 返回数据不是JSON"
        )

        print(response.text)

        return None


    # ==================================================
    # READ API DATA
    # ==================================================

    try:

        groups = (
            data["result"]
            ["data"]
            ["json"]
        )


        if not isinstance(groups, list):

            print(
                f"❌ {web['name']} 返回数据不是列表"
            )

            return None


    except (KeyError, TypeError) as e:

        print(
            f"❌ {web['name']} JSON结构错误:"
        )

        print(e)

        print(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2
            )
        )

        return None


    # ==================================================
    # CREATE BALANCE DICTIONARY
    # ==================================================

    balance_data = {}


    for item in groups:

        channel_id = item.get(
            "channelId"
        )


        raw_balance = item.get(
            "balance",
            0
        )


        # 金额除100
        balance = (
            raw_balance / 100
        )


        balance_data[
            channel_id
        ] = balance


    # ==================================================
    # CREATE HEADER ROW
    # ==================================================

    header_row = [
    web["name"]
]


    # ==================================================
    # CREATE BALANCE ROW
    # ==================================================

    balance_row = [
        "余额"
    ]


    total_balance = 0


    # ==================================================
    # DISPLAY ORDER
    # ==================================================

    for channel_id in web["display_order"]:


        # 渠道名称
        channel_name = (
            web["channel_names"].get(
                channel_id,
                f"未知-{channel_id}"
            )
        )


        # 渠道余额
        channel_balance = (
            balance_data.get(
                channel_id,
                0
            )
        )


        # 添加标题
        header_row.append(
            channel_name
        )


        # 添加余额
        balance_row.append(

            round(
                channel_balance,
                2
            )

        )


        # 计算总余额
        total_balance += (
            channel_balance
        )


        print(

            f"{channel_name:<20}"

            f"{channel_balance:>20,.2f}"

        )


    # ==================================================
    # ADD TOTAL
    # ==================================================

    header_row.append(
        "总余额"
    )


    balance_row.append(

        round(
            total_balance,
            2
        )

    )


    print("-" * 70)


    print(

        f"{'总余额':<20}"

        f"{total_balance:>20,.2f}"

    )


    print("=" * 70)


    return {

        "header_row":
            header_row,

        "balance_row":
            balance_row,

        "total_balance":
            total_balance

    }


# ==================================================
# CONNECT GOOGLE SHEET
# ==================================================

print("\n正在连接 Google Sheet...")


SCOPES = [

    "https://www.googleapis.com/auth/spreadsheets",

    "https://www.googleapis.com/auth/drive"

]


try:

    credentials = (
        Credentials.from_service_account_file(

            CREDENTIALS_FILE,

            scopes=SCOPES

        )
    )


    gc = gspread.authorize(
        credentials
    )


    spreadsheet = gc.open_by_key(
        SHEET_ID
    )


    worksheet = (
        spreadsheet.get_worksheet(0)
    )


    print(
        "✅ Google Sheet 连接成功"
    )


except Exception as e:

    print(
        "❌ Google Sheet 连接失败:"
    )

    print(e)

    exit()


# ==================================================
# RUN ALL WEBS
# ==================================================

success_count = 0

fail_count = 0


for web in WEBS:


    result = get_web_balance(
        web
    )


    # API失败不修改原数据
    if result is None:

        fail_count += 1


        print(

            f"⚠️ {web['name']} 获取失败，"

            "保留Google Sheet原数据"

        )


        continue


    # ==================================================
    # GET DATA
    # ==================================================

    header_row = result[
        "header_row"
    ]


    balance_row = result[
        "balance_row"
    ]


    row = web[
        "sheet_row"
    ]


    # ==================================================
    # WRITE TWO ROWS
    # ==================================================

    try:

        worksheet.update(

            range_name=f"A{row}",

            values=[

                header_row,

                balance_row

            ]

        )


        success_count += 1


        print(

            f"✅ {web['name']} 更新成功"

        )


        print(

            f"标题行: {row}"

        )


        print(

            f"余额行: {row + 1}"

        )


    except Exception as e:

        fail_count += 1


        print(

            f"❌ {web['name']} "
            "写入Google Sheet失败:"

        )

        print(e)


# ==================================================
# FINISH
# ==================================================

print("\n")
print("=" * 70)

print("全部网站处理完成")

print(
    f"成功: {success_count}"
)

print(
    f"失败: {fail_count}"
)

print("=" * 70)