import warnings
warnings.filterwarnings("ignore")

import asyncio
from datetime import datetime, timedelta
import json
import os
from zoneinfo import ZoneInfo
import requests
from playwright.async_api import async_playwright
from telegram import InputMediaPhoto, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# ==================================================
# CONFIGURATION
# ==================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TZ_BRAZIL = ZoneInfo("America/Sao_Paulo")

TELEGRAM_BOT_TOKEN = "8619560804:AAGmAFnJus-S2Rwr8QZZAiCQlvt_KmVBtmE"
ALLOWED_CHAT_ID = "-4902613163"  # ID nhóm/chat cho phép gọi lệnh

SITES = [
    {
        "name": "Site 73J",
        "site_title": "【15016】73J",
        "api_url": "https://api5.v-n-r-1.com/api/backend/trpc/realTimeData.list",
        "tenant_id": 1634560,
        "token": "z5hwwpepikzhyao7ahiyxz0b3t5aa0vihsmi1irl",
        "account": "jqr73j",
        "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
        "host": "admin-15016-e3adb6.y-7-l-x.com",
    },
    {
        "name": "Site 23E",
        "site_title": "【16028】23E",
        "api_url": "https://api6.o-9-d-4.com/api/backend/trpc/realTimeData.list",
        "tenant_id": 9503839,
        "token": "90saqtoejqtziugu7771nlzn66k4febmoce4k76b",
        "account": "jiqiren23e",
        "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
        "host": "admin-16028-5acf36.c-9-m-1.com",
    },
    {
        "name": "Site 23A",
        "site_title": "【16021】23A",
        "api_url": "https://api6.o-9-d-4.com/api/backend/trpc/realTimeData.list",
        "tenant_id": 2654039,
        "token": "vv3d83jp99w0n3pjl5jxd7jmmkosu32gst15l9fa",
        "account": "23aa",
        "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
        "host": "admin-16021-9fab47.c-9-m-1.com",
    },
    {
        "name": "Site NN22",
        "site_title": "【16011】NN22",
        "api_url": "https://api6.o-9-d-4.com/api/backend/trpc/realTimeData.list",
        "tenant_id": 2175621,
        "token": "jp1249qg9f47jwealsc7gdnc250lgyq4zkfz3nxu",
        "account": "nn22",
        "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
        "host": "admin-16011-34bc8f.c-9-m-1.com",
    },
    {
        "name": "Site 76B",
        "site_title": "【2306】76B",
        "api_url": "https://api3.a-b-c-5.com/api/backend/trpc/realTimeData.list",
        "tenant_id": 5317688,
        "token": "2saobx3un5x7kbbplypl8ej0w1b9itfnkh4r18io",
        "account": "xiaoruan2306",
        "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
        "host": "admin-2306-66b1c5.m-b-d-1.com",
    },
    {
        "name": "Site 5BBB",
        "site_title": "【2300】5BBB",
        "api_url": "https://api3.a-b-c-5.com/api/backend/trpc/realTimeData.list",
        "tenant_id": 1530143,
        "token": "0kaonw5gfuesnsv5o8tcp7je0qfhqdg0w26ttdec",
        "account": "xiaoruan2300",
        "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
        "host": "admin-2300-68f8c3.m-b-d-1.com",
    },
    {
        "name": "Site XXX7",
        "site_title": "【2527】XXX7",
        "api_url": "https://api5.v-n-r-1.com/api/backend/trpc/realTimeData.list",
        "tenant_id": 2730566,
        "token": "x1a0fecyl3arx2e20ub3jh4xbp54ef8nwuv7bnxd",
        "account": "xiaoruan2527",
        "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
        "host": "admin-2527-351324.y-7-l-x.com",
    },   
    {
        "name": "Site WW33",
        "site_title": "【15008】WW33",
        "api_url": "https://api5.v-n-r-1.com/api/backend/trpc/realTimeData.list",
        "tenant_id": 9930159,
        "token": "c6zmciqrqs963q0myotq2lhitfrvm2alzygbut9p",
        "account": "xiaoruan15008",
        "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
        "host": "admin-15008-7b9c73.y-7-l-x.com",
    },   
    {
        "name": "Site 55UU",
        "site_title": "【2527】55UU",
        "api_url": "https://api5.v-n-r-1.com/api/backend/trpc/realTimeData.list",
        "tenant_id": 1823786,
        "token": "0qdah3s68h49gr21ik4kc74aoja6syb1y5pksgey",
        "account": "xiaoruan2502",
        "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
        "host": "admin-2502-29b1ef.y-7-l-x.com",
    }, 
    {
        "name": "Site EE44",
        "site_title": "【2515】EE44",
        "api_url": "https://api5.v-n-r-1.com/api/backend/trpc/realTimeData.list",
        "tenant_id": 7113392,
        "token": "u70ohpl8uxhi0vyjif51z37c98mpjot2292xlvgr",
        "account": "xiaoruan2515",
        "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
        "host": "admin5-2515-67db94.y-7-l-x.com",
    }, 
    {
        "name": "Site BB22",
        "site_title": "【720】BB22",
        "api_url": "https://api4.i-j-k-8.com/api/backend/trpc/realTimeData.list",
        "tenant_id": 6247284,
        "token": "dtb9uff6er7bjzcia4zn5nj6lq9b5xs4stfsubpg",
        "account": "xiaoruan720",
        "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
        "host": "admin4-720-05ec73.m-9-y-j.com",
    },  
    {
        "name": "Site 7JJJ",
        "site_title": "【2409】7JJJ",
        "api_url": "https://api4.i-j-k-8.com/api/backend/trpc/realTimeData.list",
        "tenant_id": 5416567,
        "token": "txl9o3kit0m70883znb3ijib4n6fvcbz4js75poe",
        "account": "xiaoruan2409",
        "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
        "host": "admin-2409-56df41.m-9-y-j.com",
    },      
     {
        "name": "Site XXX1",
        "site_title": "【2501】XXX1",
        "api_url": "https://api5.v-n-r-1.com/api/backend/trpc/realTimeData.list",
        "tenant_id": 9933402,
        "token": "je4v9kssehuel8oofuxk0fen99lqstxhzg63oos0",
        "account": "xiaoruan2501",
        "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
        "host": "admin-2501-a5aaf3.y-7-l-x.com",
    },      
    {
        "name": "Site 44WW",
        "site_title": "【928】44WW",
        "api_url": "https://api5.v-n-r-1.com/api/backend/trpc/realTimeData.list",
        "tenant_id": 4552161,
        "token": "0mntlei1x27w62236mm9nh3hssw1mrhe9dt6iits",
        "account": "xiaoruan928",
        "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
        "host": "admin5-928-mdywmz.y-7-l-x.com",
    },      
    {
        "name": "Site 33NN",
        "site_title": "【923】33NN",
        "api_url": "https://api5.v-n-r-1.com/api/backend/trpc/realTimeData.list",
        "tenant_id": 4077356,
        "token": "j88x07eqbtdmg28z3sj04abuvu0sj0ygnuwi3qpe",
        "account": "xiaoruan923",
        "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
        "host": "admin5-923-nevem0.y-7-l-x.com",
    },    
     {
        "name": "Site RR66",
        "site_title": "【913】RR66",
        "api_url": "https://api5.v-n-r-1.com/api/backend/trpc/realTimeData.list",
        "tenant_id": 1803215,
        "token": "e86szunet2emq2x37nc63htqsgtwta3pod8893d2",
        "account": "xiaoruan913",
        "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
        "host": "admin5-913-67b575.y-7-l-x.com",
   },   
  {
         "name": "Site KK44",
         "site_title": "【915】KK44",
         "api_url": "https://api5.v-n-r-1.com/api/backend/trpc/realTimeData.list",
         "tenant_id": 4379055,
         "token": "qnpbnr4n82xar36iw6c6yklaecyo5p30d6x9plh9",
         "account": "xiaoruan915",
         "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
         "host": "admin5-915-9b50d1.y-7-l-x.com",
    },
   {
         "name": "Site 33CC",
         "site_title": "【907】33CC",
         "api_url": "https://api5.v-n-r-1.com/api/backend/trpc/realTimeData.list",
         "tenant_id": 8416670,
         "token": "rxaecel8k943n1reqeo1gffmz6y4vwwvxzxx9il9",
         "account": "xiaoruan907",
         "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
         "host": "admin5-907-4c06b8.y-7-l-x.com",
    },
    {
         "name": "Site 22CC",
         "site_title": "【517】22CC",
         "api_url": "https://api3.a-b-c-5.com/api/backend/trpc/realTimeData.list",
         "tenant_id": 3731525,
         "token": "5pk90mcdvnr6rnln7p61e4xo6dno9gg417j4lz3c",
         "account": "xiaoruan517",
         "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
         "host": "admin3-517-47ea8f.m-b-d-1.com",
    },
    {
         "name": "Site 77SS",
         "site_title": "【713】77SS",
         "api_url": "https://api4.i-j-k-8.com/api/backend/trpc/realTimeData.list",
         "tenant_id": 7597753,
         "token": "x4ozdz1da51av7tgoncrs74kdqvrmwxgp6estv2k",
         "account": "7sxiaoruan",
         "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
         "host": "admin4-713-d801e1.m-9-y-j.com",
    },
    {
         "name": "Site 11CC",
         "site_title": "【707】11CC",
         "api_url": "https://api4.i-j-k-8.com/api/backend/trpc/realTimeData.list",
         "tenant_id": 8109130,
         "token": "6m5kiop4qlkitrbweugxixn6mzbyo3nhehdo7ysw",
         "account": "1cxiaoruan",
         "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
         "host": "admin4-707-fc85eb.m-9-y-j.com",
    },
    {
         "name": "Site 99SS",
         "site_title": "【706】99SS",
         "api_url": "https://api4.i-j-k-8.com/api/backend/trpc/realTimeData.list",
         "tenant_id": 4932219,
         "token": "234itrays7gwgpbk1lkgia9hnv2hw38p2n7ftake",
         "account": "9sxiaoruan",
         "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
         "host": "admin4-706-c31640.m-9-y-j.com",
    },
    {
         "name": "Site 66AA",
         "site_title": "【704】66AA",
         "api_url": "https://api4.i-j-k-8.com/api/backend/trpc/realTimeData.list",
         "tenant_id": 5772945,
         "token": "s69ry2abb5kqavybzsiumdie80l6xhubz6rstg4a",
         "account": "6axiaoruan",
         "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
         "host": "admin4-704-81d77a.m-9-y-j.com",
    },
    {
         "name": "Site 77GG",
         "site_title": "【650】77GG",
         "api_url": "https://api3.a-b-c-5.com/api/backend/trpc/realTimeData.list",
         "tenant_id": 5031033,
         "token": "uupodaxme1dd11c8r9knz55z7nfhreu96w9xtv44",
         "account": "7gxiaoruan",
         "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
         "host": "admin3-650-1361e9.m-b-d-1.com",
    },
    {
         "name": "Site 77BB",
         "site_title": "【619】77BB",
         "api_url": "https://api3.a-b-c-5.com/api/backend/trpc/realTimeData.list",
         "tenant_id": 4040571,
         "token": "1m1p8xdcxp0en2cosml9gha9g680szpi2io95og7",
         "account": "77xiaoruan",
         "fingerprint": "dAuuHs0kUqzUjz3Dnv1i",
         "host": "admin3-619-2ac217.m-b-d-1.com",
    },
                                                       
]


# ==================================================
# HELPER & DATA PROCESSING
# ==================================================
def get_rounded_brazil_time():
    """获取向下取整到 5 分钟的巴西时间"""
    now = datetime.now(TZ_BRAZIL)
    target_minute = (now.minute // 5) * 5
    return now.replace(minute=target_minute, second=0, microsecond=0)


def get_target_times(num_days=4):
    now = get_rounded_brazil_time()
    return [
        {
            "date": (now - timedelta(days=i)).strftime("%Y-%m-%d"),
            "time": (now - timedelta(days=i)).strftime("%H:%M"),
        }
        for i in range(num_days)
    ]


def fetch_api_data(site, date):
    headers = {
        "authorization": f"Bearer {site['token']}",
        "account": site["account"],
        "client-language": "zh-CN",
        "fingerprint-id": site["fingerprint"],
        "x-admin-host": site["host"],
        "origin": f"https://{site['host']}",
        "user-agent": "Mozilla/5.0",
    }
    params = {"input": json.dumps({"json": {"tenantId": site["tenant_id"], "dateTime": date}})}

    try:
        res = requests.get(site["api_url"], params=params, headers=headers, timeout=20)
        res.raise_for_status()
        return res.json().get("result", {}).get("data", {}).get("json", [])
    except Exception as e:
        print(f"  [API Error] Site: {site['name']} | Date: {date} | Error: {e}")
        return []


def process_site_data(site):
    results = {}
    targets = get_target_times(4)

    for target in targets:
        date, target_time = target["date"], target["time"]
        rows = fetch_api_data(site, date)

        for row in rows:
            if "createTime" not in row:
                continue
            utc_dt = datetime.fromisoformat(row["createTime"].replace("Z", "+00:00"))
            brazil_dt = utc_dt.astimezone(TZ_BRAZIL)

            if brazil_dt.strftime("%H:%M") == target_time:
                results[date] = row
                break

    return results


def calculate_metrics(data, date):
    r = data.get(date, {})
    if not r:
        return {}

    recharge_amount = r.get("rechargeAmount", 0) / 100
    withdraw_amount = r.get("withdrawAmount", 0) / 100
    recharge_count = r.get("rechargeCount", 0)

    avg_recharge = round(recharge_amount / recharge_count, 2) if recharge_count > 0 else 0

    return {
        "登录用户": r.get("loginCount", 0),
        "新增注册": r.get("registerCount", 0),
        "投注用户": r.get("betCount", 0),
        "同时在线": r.get("onlineCount", 0),
        "首充用户": r.get("firstRechargeCount", 0),
        "裂变首充": r.get("subFirstRechargeCount", 0),
        "充值用户": recharge_count,
        "平台盈利": round(r.get("tenantProfitAmount", 0) / 100, 2),
        "人工充值/订单数": int(r.get("manualRechargeAmount", 0) / 100),
        "订单充值/订单数": int(r.get("orderRechargeAmount", 0) / 100),
        "人工提现/订单数": round(r.get("manualWithdrawAmount", 0) / 100, 2),
        "订单提现/订单数": int(r.get("orderWithdrawAmount", 0) / 100),
        "充提差": round(recharge_amount - withdraw_amount, 2),
        "赠送金额": round(r.get("discountAmount", 0) / 100, 2),
        "人均充值": avg_recharge,
    }


def get_comparison_status(val_today, val_past, metric_name):
    if metric_name in ["人工充值/订单数", "人工提现/订单数"]:
        if val_today == val_past:
            return "正常", "status-normal"
        else:
            return "检查", "status-warning"

    if val_past == 0:
        if val_today == 0:
            return "正常", "status-normal"
        ratio = 2.0
    else:
        ratio = val_today / val_past

    if metric_name == "登录用户":
        if ratio < 0.75 or ratio > 1.25:
            return "检查", "status-warning"
        return "正常", "status-normal"

    elif metric_name == "新增注册":
        if ratio < 0.60 or ratio > 1.40:
            return "异常", "status-abnormal"
        return "正常", "status-normal"

    elif metric_name in ["投注用户", "同时在线", "赠送金额", "人均充值"]:
        if ratio < 0.75 or ratio > 1.25:
            return "异常", "status-abnormal"
        return "正常", "status-normal"

    else:
        if ratio < 0.50 or ratio > 1.50:
            return "异常", "status-abnormal"
        return "正常", "status-normal"


def analyze_change(val_today, val_past):
    if val_past == 0:
        return "大幅增加" if val_today > 0 else None
    
    diff_pct = (val_today - val_past) / val_past
    
    if diff_pct >= 0.50:
        return "大幅增加"
    elif 0.20 <= diff_pct < 0.50:
        return "明显增加"
    elif 0.05 <= diff_pct < 0.20:
        return "略微增加"
    elif -0.20 < diff_pct <= -0.05:
        return "略微减少"
    elif -0.50 < diff_pct <= -0.20:
        return "明显下降"
    elif diff_pct <= -0.50:
        return "大幅下降"
    else:
        return "异常波动"


def generate_text_analysis(site_title, data):
    dates = sorted(data.keys(), reverse=True)
    if len(dates) < 2:
        return ""

    today_date = dates[0]
    past_dates = dates[1:]
    
    today_metrics = calculate_metrics(data, today_date)
    current_time_str = get_rounded_brazil_time().strftime("%H:%M")

    metric_names = [
        "登录用户", "新增注册", "投注用户", "同时在线", "首充用户", 
        "裂变首充", "充值用户", "平台盈利", "人工充值/订单数", 
        "订单充值/订单数", "人工提现/订单数", "订单提现/订单数", 
        "充提差", "赠送金额", "人均充值"
    ]

    has_any_warning = False
    text_output = f"{site_title} 每个小时数据分析报道\n更新时间（巴西）{current_time_str}\n\n"

    for i, p_date in enumerate(past_dates, 1):
        p_metrics = calculate_metrics(data, p_date)
        warning_groups = {}

        for m in metric_names:
            val_today = today_metrics.get(m, 0)
            val_past = p_metrics.get(m, 0)
            status_text, _ = get_comparison_status(val_today, val_past, m)

            if status_text in ["检查", "异常"]:
                has_any_warning = True
                change_type = analyze_change(val_today, val_past)
                if change_type:
                    if change_type not in warning_groups:
                        warning_groups[change_type] = []
                    warning_groups[change_type].append(m)

        if warning_groups:
            text_output += f"- 与前{i}天相比：\n"
            for change_type, m_list in warning_groups.items():
                metrics_str = ", ".join(m_list)
                text_output += f"  {metrics_str} {change_type} ;\n"
            text_output += "\n"

    if not has_any_warning:
        text_output += "✅ 所有指标均在正常范围内，无异常/检查项。\n\n"

    return text_output


def get_analysis_display(val_today, val_past, metric_name):
    """根据对比状态和增减幅返回显示文字和对应的颜色样式，并对人工充提行进行特殊处理"""
    
    # Xử lý riêng cho 人工充值/订单数 và 人工提现/订单数 nếu hôm nay có số liệu (> 0) -> Màu cam đậm, chữ đen
    if metric_name in ["人工充值/订单数", "人工提现/订单数"] and val_today > 0:
        return "需要检查", "background-color: #ff8c00 !important; color: #000000 !important;"

    status_text, _ = get_comparison_status(val_today, val_past, metric_name)
    
    # Nếu trạng thái là 正常 -> Hiển thị "节奏平稳" với màu xanh đậm, chữ trắng
    if status_text == "正常":
        return "节奏平稳", "background-color: #70ad47 !important; color: #ffffff !important;"

    # Nếu là 检查 hoặc 异常 -> Dựa vào mức độ tăng/giảm để gán chữ và màu sắc
    change_type = analyze_change(val_today, val_past)
    
    if change_type == "略微减少":
        return "略微减少", "background-color: #ffcccc !important; color: #900000 !important;" # Màu đỏ nhạt, chữ đỏ sẫm
    elif change_type == "大幅下降" or change_type == "明显下降":
        return change_type, "background-color: #ff9966 !important; color: #000000 !important;" # Màu cam, chữ đen
    elif change_type == "略微增加":
        return "略微增加", "background-color: #f8bbd0 !important; color: #000000 !important;" # Màu xanh hơi nhạt, chữ đen
    elif change_type == "明显增加" or change_type == "大幅增加":
        return change_type, "background-color: #64b5f6 !important; color: #000000 !important;" # Màu xanh hơi đậm, chữ trắng
    else:
        return change_type or "异常波动", "background-color: #e0a899 !important; color: #000000 !important;"


def generate_site_html(site_title, data):
    dates = sorted(data.keys(), reverse=True)
    if not dates:
        return ""

    today_date = dates[0]
    past_dates = dates[1:]

    today_metrics = calculate_metrics(data, today_date)
    past_metrics_list = [calculate_metrics(data, d) for d in past_dates]

    current_time_str = get_rounded_brazil_time().strftime("%H:%M")

    metric_names = [
        "登录用户", "新增注册", "投注用户", "同时在线", "首充用户", 
        "裂变首充", "充值用户", "平台盈利", "人工充值/订单数", 
        "订单充值/订单数", "人工提现/订单数", "订单提现/订单数", 
        "充提差", "赠送金额", "人均充值"
    ]

    # Bảng 1: Số liệu gốc
    left_rows_html = ""
    for m in metric_names:
        val_today = today_metrics.get(m, 0)
        past_vals_td = "".join([f'<td class="num-cell">{calculate_metrics(data, d).get(m, 0)}</td>' for d in past_dates])
        left_rows_html += f"""
        <tr>
            <td class="metric-name">{m}</td>
            <td class="num-cell">{val_today}</td>
            {past_vals_td}
        </tr>
        """

    # Bảng 2: Trạng thái (正常 / 检查 / 异常)
    right_rows_html = ""
    for m in metric_names:
        val_today = today_metrics.get(m, 0)
        comp_cells = ""
        for p_metrics in past_metrics_list:
            val_past = p_metrics.get(m, 0)
            status_text, css_class = get_comparison_status(val_today, val_past, m)
            comp_cells += f'<td class="{css_class}">{status_text}</td>'

        right_rows_html += f"""
        <tr>
            <td class="metric-name">{m}</td>
            {comp_cells}
        </tr>
        """

    # Bảng 3: Phân tích chi tiết với màu sắc riêng biệt cho từng loại (大幅增加, 略微减少, 持平, v.v.)
    analysis_rows_html = ""
    for m in metric_names:
        val_today = today_metrics.get(m, 0)
        analysis_cells = ""
        for p_metrics in past_metrics_list:
            val_past = p_metrics.get(m, 0)
            
            # Lấy text hiển thị và style màu sắc tương ứng
            display_text, custom_style = get_analysis_display(val_today, val_past, m)
            
            analysis_cells += f'<td style="{custom_style} font-size: 13px; font-weight: 700; text-align: center;">{display_text}</td>'

        analysis_rows_html += f"""
        <tr>
            <td class="metric-name">{m}</td>
            {analysis_cells}
        </tr>
        """

    left_header_dates = "".join([f"<th>{d}</th>" for d in past_dates])

    html_block = f"""
    <div class="report-container">
        <!-- Bảng 1: Số liệu -->
        <table class="data-table">
            <thead>
                <tr>
                    <th class="site-header-bg">{site_title}</th>
                    <th colspan="{len(dates)}" class="time-header-bg text-left">
                        每个小时的数据报道（更新时间）：{current_time_str}
                    </th>
                </tr>
                <tr class="sub-header">
                    <th style="width: 130px;">指标</th>
                    <th style="width: 105px;">{today_date}</th>
                    {left_header_dates}
                </tr>
            </thead>
            <tbody>
                {left_rows_html}
            </tbody>
        </table>

        <!-- Bảng 2: Trạng thái chuẩn -->
        <table class="compare-table">
            <thead>
                <tr>
                    <th class="dark-header">{today_date}</th>
                    <th colspan="3" class="title-bg">同时间段数据对比</th>
                </tr>
                <tr class="sub-header">
                    <th style="width: 130px;">指标</th>
                    <th style="width: 90px;">对比前1天</th>
                    <th style="width: 90px;">对比前2天</th>
                    <th style="width: 90px;">对比前3天</th>
                </tr>
            </thead>
            <tbody>
                {right_rows_html}
            </tbody>
        </table>

        <!-- Bảng 3: Phân tích xu hướng màu sắc riêng biệt -->
        <table class="compare-table">
            <thead>
                <tr>
                    <th colspan="4" class="dark-header" style="background-color: #3d1028;">同时数据异常波动分析</th>
                </tr>
                <tr class="sub-header">
                    <th style="width: 130px;">指标</th>
                    <th style="width: 100px;">与前1天相比</th>
                    <th style="width: 100px;">与前2天相比</th>
                    <th style="width: 100px;">与前3天相比</th>
                </tr>
            </thead>
            <tbody>
                {analysis_rows_html}
            </tbody>
        </table>
    </div>
    """
    return html_block

async def render_full_html_to_image(html_content, output_path):
    full_document = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            * {{
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", Arial, sans-serif;
                background-color: #edf2f7;
                color: #000000;
                padding: 16px;
                margin: 0;
                display: inline-block;
            }}
            .report-container {{
                display: flex;
                gap: 12px;
                margin-bottom: 20px;
                background: #ffffff;
                padding: 10px;
                border-radius: 4px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            }}
            table {{
                border-collapse: collapse;
                font-size: 14px;
                text-align: center;
                color: #000000;
            }}
            th, td {{
                border: 1px solid #000000;
                padding: 5px 8px;
                height: 28px;
                white-space: nowrap;
                color: #000000 !important;
            }}
            .site-header-bg {{ background-color: #f5cf65; font-weight: 700; font-size: 16px !important; }}
            .time-header-bg {{ background-color: #fef3c7; font-weight: 700; font-size: 15px !important; }}
            .title-bg {{ background-color: #fde68a; font-weight: 700; font-size: 16px !important; }}
            .dark-header {{ background-color: #3d1028; color: #ffffff !important; font-weight: 700; font-size: 16px !important; }}
            .sub-header th {{ background-color: #fff2cc; font-weight: 700; font-size: 15px !important; }}
            .metric-name {{ background-color: #fff2cc; font-weight: 700; font-size: 15px !important; text-align: center; min-width: 130px; }}
            .num-cell {{ text-align: center !important; font-size: 14px !important; font-weight: 700 !important; background-color: #ffffff !important; }}
            .text-left {{ text-align: left; padding-left: 10px; }}
            .status-normal {{ background-color: #70ad47 !important; font-weight: 700; font-size: 14px; }}
            .status-abnormal {{ background-color: #ff0000 !important; font-weight: 700; font-size: 14px; }}
            .status-warning {{ background-color: #f5cf65 !important; font-weight: 700; font-size: 14px; }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(device_scale_factor=2)
        await page.set_content(full_document)
        element = await page.query_selector("body")
        await element.screenshot(path=output_path)
        await browser.close()


# ==================================================
# TELEGRAM BOT HANDLERS & LỆNH RUN
# ==================================================
async def handle_praise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hàm lắng nghe và phản hồi khi người dùng nhắn khen hoặc gọi báo cáo"""
    if not update.message or not update.message.text:
        return

    user_text = update.message.text.lower()

    # Bắt từ khóa báo cáo số liệu hoặc câu khen
    report_keywords = ["发数据", "发报表", "数据报告"]
    
    # 1. Nếu nhắn đúng câu kích hoạt báo cáo:
    if any(kw in user_text for kw in report_keywords):
        await update.message.reply_text("好的!数据报告马上出来!")
        
        # Gọi trực tiếp hàm xử lý của lệnh /run
        # (Thay 'handle_run' bằng tên hàm chạy báo cáo thực tế trong code của bạn)
        await run_report(update, context)
        return

    # 2. Nếu nhắn các từ khóa giao tiếp / nịnh sếp thông thường:
    praise_keywords = ["nghe lời", "anh về đây nha bót", "ngoan", "biết nghe", "bot", "xiaoruan"]
    if any(kw in user_text for kw in praise_keywords):
        await update.message.reply_text("Dạ ạ anh về cẩn thận tối nhớ đi làm đúng giờ nha, anh Xiaoruan đẹp trai! 😎")


async def send_long_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str):
    """Hàm phụ trợ: Tự động chia nhỏ tin nhắn nếu dài hơn 4000 ký tự"""
    max_length = 4000
    for i in range(0, len(text), max_length):
        await context.bot.send_message( 
            chat_id=chat_id, 
            text=text[i:i + max_length],
            read_timeout=60,
            write_timeout=60
        )


async def run_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理用户在 Telegram 输入 /report 或 /run 指令的函数"""
    status_msg = await update.message.reply_text("⏳ 正在获取数据并生成报告，请稍候...")

    opened_files = []
    temp_image_files = []

    try:
        site_analysis_results = []

        # 1. 先处理所有 Site 的 API 数据、生成图片及文字分析
        for index, site in enumerate(SITES):
            print(f"---> [{index + 1}/{len(SITES)}] 正在处理: {site['name']}")
            site_data = process_site_data(site)

            if not site_data:
                continue

            site_html = generate_site_html(site["site_title"], site_data)
            analysis_text = generate_text_analysis(site["site_title"], site_data)
            
            if analysis_text:
                site_analysis_results.append(analysis_text)

            image_file = os.path.join(BASE_DIR, f"report_site_{index}.png")
            await render_full_html_to_image(site_html, image_file)
            temp_image_files.append(image_file)

        if not temp_image_files:
            await status_msg.edit_text("❌ 未能从 API 获取到有效数据。")
            return

        # 2. Chia danh sách hình ảnh thành các nhóm tối đa 10 ảnh và gửi
        chunk_size = 10
        image_chunks = [temp_image_files[i:i + chunk_size] for i in range(0, len(temp_image_files), chunk_size)]

        for chunk in image_chunks:
            media_group = []
            for image_file in chunk:
                f = open(image_file, "rb")
                opened_files.append(f)
                media_group.append(InputMediaPhoto(media=f))

            await context.bot.send_media_group(
                chat_id=update.effective_chat.id,
                media=media_group,
                read_timeout=120,
                write_timeout=120,
                connect_timeout=60
            )

        # ==================================================
        # 3. 图片发送完成后，发送精简且高档的提示文字
        # ==================================================
        current_time_str = get_rounded_brazil_time().strftime("%H:%M")
        
        simple_report = (
            f"🇧🇷 *****【巴西全站】实时数据分析播报 *****\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🕒 **播报时间 (巴西):** `{current_time_str}`\n\n"
            f"⚠️ 请各负责人核对上方数据，是否存在异常数据！"
        )
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=simple_report,
            parse_mode="Markdown"
        )

        # 4. Xóa tin nhắn trạng thái
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=status_msg.message_id)
        print("🎉所有站点综合分析图片及文字报告已成功发送至 Telegram！")

    except Exception as e:
        print(f"❌ 运行报错: {e}")
        await status_msg.edit_text(f"❌ 生成报告时出错: {e}")

    finally:
        # 5. 清理内存流与临时图片文件
        for f in opened_files:
            f.close()
        for img_path in temp_image_files:
            if os.path.exists(img_path):
                os.remove(img_path)


async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理用户输入 /id 或 /chatid 查询 Chat ID 的函数"""
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "私聊/Private Chat"
    
    response_text = (
        f"📌 **Chat Information / 会话信息**\n\n"
        f"▪ **Title / 名称:** `{chat_title}`\n"
        f"▪ **Chat ID:** `{chat_id}`"
    )
    
    await update.message.reply_text(response_text, parse_mode="Markdown")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start 与 /help 指令的提示信息"""
    await update.message.reply_text(
        "👋 **您好！每个小时数据分析机器人已就绪。**\n\n"
        "▫ 指令 `/report` 或 `/run`: 生成并发送数据报告\n"
        "▫ 指令 `/id` 或 `/chatid`: 获取当前群组的 Chat ID"
    )


# ==================================================
# MAIN PROGRAM (BOT LISTENER)
# ==================================================
def main():
    print("🤖 机器人正在启动，正在监听指令...")
    
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .read_timeout(120)
        .write_timeout(120)
        .connect_timeout(60)
        .build()
    )

    # 1. Tự động đăng ký danh sách lệnh gợi ý khi gõ dấu /
    from telegram import BotCommand
    async def post_init(application):
        commands = [
            BotCommand("report", "生成并发送数据报告"),
            BotCommand("run", "生成并发送数据报告"),
            BotCommand("id", "获取当前群组的 Chat ID"),
            BotCommand("chatid", "获取当前群组的 Chat ID"),
            BotCommand("help", "显示帮助信息"),
        ]
        await application.bot.set_my_commands(commands)

    app.post_init = post_init

    # 2. 注册指令处理器
    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(CommandHandler(["report", "run"], run_report))
    app.add_handler(CommandHandler(["id", "chatid"], get_chat_id))

    # 3. 注册 MessageHandler (Bắt tin nhắn "biết nghe lời rồi đó")
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_praise))

    # 开始轮询监听 (Long Polling)
    app.run_polling()


if __name__ == "__main__":
    main()