import warnings
warnings.filterwarnings("ignore")
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
import sqlite3
import time
from zoneinfo import ZoneInfo
import json
import pandas as pd
import requests



# ==================================================
# API CONFIG
# ==================================================

TOKEN = "z5hwwpepikzhyao7ahiyxz0b3t5aa0vihsmi1irl"
ACCOUNT = "jqr73j"
TENANT_ID = 1634560
REGION_ID = 1
BASE_URL = "https://api5.v-n-r-1.com/api/backend/trpc"

# Cố định người tạo/thao tác theo tài khoản của bạn

EXPECTED_OPERATOR = "jqr73j" 

HEADERS = {
    "authorization": f"Bearer {TOKEN}",
    "account": ACCOUNT,
    "x-admin-host": "admin-15016-e3adb6.y-7-l-x.com",
    "client-language": "zh-CN",
    "content-type": "application/json",
}


# ==================================================
# Brazil 昨天
# ==================================================

def get_brazil_yesterday():
    tz = ZoneInfo("America/Sao_Paulo")
    now = datetime.now(tz)
    return now.date() - timedelta(days=1)


# ==================================================
# 创建充值导出并记录发起时间 (1-1 锁定基准)
# ==================================================
def create_export(day):
    create_time = datetime.now(timezone.utc)

    payload = {
        "json": {
            "queryType": "export",
            "changeAmountStatus": "HAVE_ARRIVED",
            "timeType": "updateTime",
            "regionId": REGION_ID,
            "tenantId": TENANT_ID,
            "startTime": f"{day}T03:00:00.000Z",
            "endTime": f"{day + timedelta(days=1)}T02:59:59.999Z",
            "tableType": "success",
        }
    }

    r = requests.get(
        BASE_URL + "/payRecord.exportList",
        headers=HEADERS,
        params={"input": json.dumps(payload, separators=(",", ":"))},
        timeout=60,
    )
    print("创建导出响应状态:", r.status_code)
    
    return create_time


# ==================================================
# 查找专属的导出任务 (严格匹配时间、模块和操作人)
# ==================================================
def find_new_export(create_time):
    payload = {
        "json": {
            "page": 1,
            "pageSize": 20,
            "regionId": REGION_ID,
            "tenantId": TENANT_ID,
        }
    }

    r = requests.get(
        BASE_URL + "/exportData.list",
        headers=HEADERS,
        params={"input": json.dumps(payload, separators=(",", ":"))},
    )

    items = (
        r.json()
        .get("result", {})
        .get("data", {})
        .get("json", {})
        .get("exportDataList", [])
    )

    items = sorted(items, key=lambda x: x["id"], reverse=True)

    for item in items:
        # 1. Kiểm tra đúng module nạp tiền (hoặc module tương ứng theo hệ thống của bạn)
        if item.get("moduleType") != "SuccessPayRecord":
            continue

        # 2. Khớp đúng người tạo / thao tác (lastOperator hoặc operate)
        op = item.get("lastOperator") or item.get("operate")
        if EXPECTED_OPERATOR and op != EXPECTED_OPERATOR:
            continue

        api_time = datetime.fromisoformat(
            item["createTime"].replace("Z", "+00:00")
        )

        # 3. Khớp thời gian tạo phải sau thời điểm gọi request
        if api_time >= create_time:
            print(f"🎯 成功锁定专属任务 ID: {item['id']} | 操作人: {op} | 创建时间: {item['createTime']}")
            return item

    return None


# ==================================================
# 等待导出完成
# ==================================================
def wait_export(create_time):
    while True:
        task = find_new_export(create_time)

        if task:
            status = task.get("status")
            if status == "ExportSuccess":
                print("导出完成:", task["id"])
                return task["id"]
            elif status in ["ExportFailed", "Failed", "Error"]:
                print(f"❌ 任务 {task['id']} 在服务器端处理失败")
                return None
            else:
                print(f"生成中 (ID: {task['id']}, 状态: {status})...")
        else:
            print("等待任务写入列表...")

        time.sleep(5)


# ==================================================
# 获取CSV地址 (带有下载重试机制)
# ==================================================
def get_csv_url(export_id, max_retries=3):
    payload = {
        "json": {
            "tenantId": TENANT_ID,
            "id": export_id,
        }
    }

    for attempt in range(1, max_retries + 1):
        try:
            r = requests.post(
                BASE_URL + "/exportData.download",
                headers=HEADERS,
                json=payload,
                timeout=60,
            )
            r.raise_for_status()
            data = r.json()

            url = (
                data.get("result", {})
                .get("data", {})
                .get("json", {})
                .get("filePath")
            )

            if not url:
                raise ValueError(f"未找到 filePath: {data}")

            print(f"CSV地址获取成功 (尝试 {attempt}):", url)
            return url

        except Exception as e:
            print(f"⚠️ 第 {attempt}/{max_retries} 次获取下载链接失败: {e}")
            if attempt < max_retries:
                time.sleep(5)
            else:
                raise Exception("多次尝试后无法获取 CSV 下载地址。")


# ==================================================
# 处理充值数据
# ==================================================
def process_recharge(csv_url):
    print("读取充值CSV...")

    r = requests.get(csv_url, timeout=120)
    r.raise_for_status()

    raw = pd.read_csv(StringIO(r.content.decode("utf-8-sig")))
    raw = raw.fillna("")

    print("原始充值数量:", len(raw))
    print("CSV字段:", raw.columns.tolist())

    user_col = None
    amount_col = None
    channel_col = None
    time_col = None

    for c in raw.columns:
        name = str(c).lower()

        if name in ["会员id", "userid", "user_id"]:
            user_col = c
        elif name in ["支付金额", "充值金额", "amount"]:
            amount_col = c
        elif name in ["会员渠道", "渠道", "channel"]:
            channel_col = c
        elif "完成时间" in str(c) or "time" in name:
            time_col = c

    print("识别字段:", user_col, amount_col, channel_col, time_col)

    if not all([user_col, amount_col, channel_col, time_col]):
        raise Exception("CSV字段错误，未能完整识别必要列")

    df = raw[[user_col, amount_col, channel_col, time_col]].copy()
    df.columns = ["会员id", "支付金额", "会员渠道", "完成时间"]

    df["会员id"] = df["会员id"].astype(str)
    df["完成时间"] = pd.to_datetime(df["完成时间"]).dt.strftime("%Y-%m-%d")
    df["支付金额"] = pd.to_numeric(df["支付金额"], errors="coerce").fillna(0)

    pay_count = (
        df.groupby(["会员id", "完成时间"]).size().reset_index(name="支付次数")
    )

    df = (
        df.groupby(["会员id", "完成时间"], as_index=False)
        .agg({"支付金额": "sum", "会员渠道": "first"})
    )

    df = df.merge(pay_count, on=["会员id", "完成时间"], how="left")

    print("合并后:", len(df))
    return df


# ==================================================
# MAIN
# ==================================================
if __name__ == "__main__":
    print("\n🚀 三方充值开始")
    start = time.time()

    day = get_brazil_yesterday()
    print("🇧🇷 日期:", day)

    create_time = create_export(day)

    print("⏳ 等待任务生成...")
    export_id = wait_export(create_time)

    if not export_id:
        print("❌ 任务失败或超时终止")
        exit()

    print("Export ID:", export_id)

    csv_url = get_csv_url(export_id)
    df = process_recharge(csv_url)
    print("保存日期:", df["完成时间"].unique())

    db = Path(__file__).parent / "73J.db"
    conn = sqlite3.connect(db)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS recharge (
        完成时间 TEXT,
        会员id TEXT,
        支付金额 INTEGER,
        会员渠道 TEXT,
        支付次数 INTEGER,
        PRIMARY KEY (完成时间, 会员id)
    )"""
    )
    conn.execute("DELETE FROM recharge")
    
    df["支付金额"] = df["支付金额"].astype(int)

    rows = df[
        ["完成时间", "会员id", "支付金额", "会员渠道", "支付次数"]
    ].values.tolist()
    
    conn.executemany(
        """
    INSERT INTO recharge
    (完成时间, 会员id, 支付金额, 会员渠道, 支付次数)
    VALUES (?, ?, ?, ?, ?)
    """,
        rows,
    )

    added = len(rows)
    conn.commit()
    conn.close()
    print(f"✅ 保存 SQLite，新增 {added} 条")

    cost = round(time.time() - start, 2)
    print("\n🎉 全部完成")
    print("耗时:", cost, "秒")