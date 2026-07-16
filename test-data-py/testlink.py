import asyncio
import gspread
import pandas as pd

from datetime import datetime
from google.oauth2.service_account import Credentials
from playwright.async_api import async_playwright


# ==========================================================
# GOOGLE SHEET
# ==========================================================

CREDENTIALS_FILE = "/Users/xiaoruan/Documents/data_get/credentials.json"

SHEET_ID = "1gfsTt_nL0wK2mepUAXkBgRqZHLYRY3xqWmbAxkzp0ao"

SHEET_NAME = "测试链接"


scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


# ==========================================================
# CONFIG
# ==========================================================

MAX_CONCURRENT = 15


# ==========================================================
# CONNECT GOOGLE SHEET
# ==========================================================

def get_sheet():

    creds = Credentials.from_service_account_file(
        CREDENTIALS_FILE,
        scopes=scope
    )

    client = gspread.authorize(creds)

    sh = client.open_by_key(SHEET_ID)

    ws = sh.worksheet(SHEET_NAME)

    return ws



# ==========================================================
# CHECK LINK
# ==========================================================

async def check_link(browser, row, semaphore):

    async with semaphore:

        site = row.get("站点", "")
        media = str(row.get("媒体", "")).lower()
        url = row.get("链接", "")


        result = {

            "状态": "⚪ 没检测连接",
            "HTTP": "",
            "最终链接": "",
            "检测时间": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "原因": ""

        }


        if not url:

            return result



        page = await browser.new_page(
            user_agent=
            "Mozilla/5.0 (Macintosh; Intel Mac OS X)"
        )


        try:

            response = await page.goto(
                url,
                timeout=20000,
                wait_until="domcontentloaded"
            )


            html = (
                await page.content()
            ).lower()


            status = response.status if response else 0


            final_url = page.url


            result["HTTP"] = status
            result["最终链接"] = final_url



            # =============================
            # TELEGRAM
            # =============================

            if media == "telegram":


                bad = [

                    "this channel cannot be displayed",
                    "this group cannot be displayed",
                    "username is invalid",
                    "not found"

                ]


                if any(x in html for x in bad):

                    result["状态"] = "🔴 失败"
                    result["原因"] = "Telegram not found"

                else:

                    result["状态"] = "🟢 正常"



            # =============================
            # FACEBOOK
            # =============================

            elif media == "facebook":


                bad = [

                    "content isn't available",
                    "page isn't available",
                    "this page isn't available"

                ]


                if any(x in html for x in bad):

                    result["状态"] = "🔴 失败"
                    result["原因"] = "Facebook page unavailable"

                else:

                    result["状态"] = "🟢 正常"



            # =============================
            # INSTAGRAM
            # =============================

            elif media == "instagram":


                bad = [

                    "sorry, this page isn't available",
                    "page isn't available"

                ]


                if any(x in html for x in bad):

                    result["状态"] = "🔴 失败"
                    result["原因"] = "Instagram not found"

                else:

                    result["状态"] = "🟢 正常"



            # =============================
            # WHATSAPP
            # =============================

            elif media == "whatsapp":


                bad = [

                    "invalid invite",
                    "invite link is invalid",
                    "link has been reset"

                ]


                if any(x in html for x in bad):

                    result["状态"] = "🔴 失败"
                    result["原因"] = "WhatsApp expired"

                else:

                    result["状态"] = "🟢 正常"



            # =============================
            # WEBSITE / CS-BOS
            # =============================

            else:


                if status >= 400:

                    result["状态"] = "🔴 失败"
                    result["原因"] = "链接无法访问"

                else:

                    result["状态"] = "🟢 正常"



        except Exception as e:


            result["状态"] = "🔴 失败"
            result["原因"] = "链接无法访问"



        finally:

            await page.close()



        return result




# ==========================================================
# MAIN
# ==========================================================

async def main():


    ws = get_sheet()


    print("\n读取 Google Sheet...")


    records = ws.get_all_records()


    print(
        f"发现 {len(records)} 条数据\n"
    )



    semaphore = asyncio.Semaphore(
        MAX_CONCURRENT
    )


    async with async_playwright() as p:


        browser = await p.chromium.launch(
            headless=True
        )


        tasks = []


        for row in records:

            tasks.append(
                check_link(
                    browser,
                    row,
                    semaphore
                )
            )



        results = await asyncio.gather(
            *tasks
        )


        await browser.close()



    # ======================================================
    # MERGE RESULT
    # ======================================================

    output = []


    for row, result in zip(
        records,
        results
    ):

        output.append([

            row.get("站点",""),
            row.get("媒体",""),
            row.get("链接",""),
            row.get("备注",""),

            result["状态"],
            result["HTTP"],
            result["最终链接"],
            result["检测时间"],
            result["原因"]

        ])




    headers = [

        "站点",
        "媒体",
        "链接",
        "备注",

        "状态",
        "HTTP",
        "最终链接",
        "检测时间",
        "原因"

    ]



    ws.clear()


    ws.update(
        "A1",
        [headers] + output
    )



    print("\n============================")

    print("检测完成")

    print(
        "Alive:",
        sum(
            1 for x in results
            if x["状态"]=="🟢 正常"
        )
    )

    print(
        "失败:",
        sum(
            1 for x in results
            if x["状态"]=="🔴 失败"
        )
    )


    print(
        "Google Sheet 已更新"
    )

    print("============================")




if __name__ == "__main__":

    asyncio.run(main())