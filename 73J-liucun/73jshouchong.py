import warnings
warnings.filterwarnings("ignore")
import json
from pathlib import Path
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from io import BytesIO
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests



# =============================
# CONFIG
# =============================

TOKEN = "z5hwwpepikzhyao7ahiyxz0b3t5aa0vihsmi1irl"

ACCOUNT = "jqr73j"

TENANT_ID = 1634560

REGION_ID = 1

# Tài khoản tạo/thao tác (Cố định để lọc chuẩn 100%)

EXPECTED_OPERATOR = ACCOUNT


# 第一次同步日期


FIRST_DATE = "2026-08-04"

# =============================
# API地址
# =============================
USERDAY_API = "https://api5.v-n-r-1.com/api/backend/trpc/userDay.list"
EXPORT_LIST_API = "https://api5.v-n-r-1.com/api/backend/trpc/exportData.list"
DOWNLOAD_API = "https://api5.v-n-r-1.com/api/backend/trpc/exportData.download"
# =============================
# HEADERS
# =============================
headers = {
    "account": ACCOUNT,
    "authorization": f"Bearer {TOKEN}",
    "fingerprint-id": "dAuuHs0kUqzUjz3Dnv1i",
    "client-language": "zh-CN",
    "content-type": "application/json",
    "origin": "https://admin-15016-e3adb6.y-7-l-x.com",
    "referer": "https://admin-15016-e3adb6.y-7-l-x.com/",
    "x-admin-host": "admin-15016-e3adb6.y-7-l-x.com",
    "user-agent": "Mozilla/5.0"

}

# =============================
# TRPC GET
# =============================
def get_api(url, payload):
    params = {"input": json.dumps({"json": payload}, separators=(",", ":"))}
    r = requests.get(url, params=params, headers=headers, timeout=60)
    r.raise_for_status()
    return r.json()


# =============================
# 获取SQLite最后日期
# =============================
def get_last_db_date():
    db = Path(__file__).parent / "73J.db"
    if not db.exists():
        return None

    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT MAX(统计时间) FROM shouchong")
        last = cursor.fetchone()[0]
    except sqlite3.OperationalError:
        last = None

    conn.close()
    return last


# =============================
# 获取需要同步日期
# =============================
def get_need_days():
    brazil_today = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    end_date = (brazil_today - timedelta(days=1)).strftime("%Y-%m-%d")

    last = get_last_db_date()

    if last:
        start_date = (
            datetime.strptime(last, "%Y-%m-%d") + timedelta(days=1)
        ).strftime("%Y-%m-%d")
    else:
        start_date = FIRST_DATE

    print("CSV最后日期:", last)
    print("开始:", start_date)
    print("结束:", end_date)

    days = []
    current = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    while current <= end:
        days.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    return days


# =============================
# 创建导出任务并严格锁定专属 ID (基于时间、模块、remark和操作人)
# =============================
def create_and_get_export_id(day):
    print("🚀 创建:", day)
    
    # 1. Ghi lại mốc thời gian UTC chính xác trước khi gửi lệnh tạo task
    create_time = datetime.now(timezone.utc)

    tomorrow = (
        datetime.strptime(day, "%Y-%m-%d") + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    payload = {
        "valueType": "phone",
        "isRecharge": True,
        "queryTime": day,
        "type": "normal",
        "regionId": REGION_ID,
        "tenantId": TENANT_ID,
        "firstRechargeStartTime": f"{day}T03:00:00.000Z",
        "firstRechargeEndTime": f"{tomorrow}T02:59:59.999Z",
        "queryData": [],
        "queryType": "export",
    }

    # 2. Gửi request tạo task
    get_api(USERDAY_API, payload)
    print("✅ 创建成功，正在精准匹配并锁定专属 ID...")

    # 3. Quét danh sách task trả về để lọc chuẩn 100%
    for _ in range(15):
        time.sleep(2)
        data = get_api(
            EXPORT_LIST_API,
            {
                "page": 1,
                "pageSize": 20,
                "regionId": REGION_ID,
                "tenantId": TENANT_ID,
            },
        )

        items = data.get("result", {}).get("data", {}).get("json", {}).get("exportDataList", [])
        
        # Sắp xếp theo ID giảm dần để kiểm tra các task mới nhất trước
        items = sorted(items, key=lambda x: x["id"], reverse=True)

        for item in items:
            remark = item.get("remark", "")
            module_type = item.get("moduleType", "")
            
            # Điều kiện 1: Đúng module dữ liệu người dùng hàng ngày
            if module_type != "UserDayData":
                continue

            # Điều kiện 2: Phải chứa đúng ngày cần truy vấn trong remark
            if f"查询时间:{day}" not in remark:
                continue

            # Điều kiện 3: Khớp đúng người tạo / thao tác (lastOperator hoặc operate)
            op = item.get("lastOperator") or item.get("operate")
            if EXPECTED_OPERATOR and op != EXPECTED_OPERATOR:
                continue

            # Điều kiện 4: Thời gian tạo task trên server phải SAU thời điểm script vừa gọi lệnh
            api_time = datetime.fromisoformat(
                item["createTime"].replace("Z", "+00:00")
            )
            if api_time >= create_time:
                print(f"🎯 成功锁定 Task ID: {item['id']} | 操作人: {op} | 创建时间: {item['createTime']}")
                return item["id"]

    print(f"⚠️ 无法自动捕获日期 {day} 的 ID")
    return None


# =============================
# 查询状态
# =============================
def check_status(export_id):
    data = get_api(
        EXPORT_LIST_API,
        {
            "page": 1,
            "pageSize": 200,
            "regionId": REGION_ID,
            "tenantId": TENANT_ID,
        },
    )

    items = data.get("result", {}).get("data", {}).get("json", {}).get("exportDataList", [])

    for item in items:
        if item["id"] == export_id:
            return item.get("status")

    return None


# =============================
# 下载CSV到内存 (Thêm Retry 3 lần & Check HTTP status)
# =============================
def download_csv(export_id, day, max_retries=3):
    print("⬇️ 下载:", day)

    for attempt in range(1, max_retries + 1):
        try:
            r = requests.post(
                DOWNLOAD_API,
                headers=headers,
                json={"json": {"tenantId": TENANT_ID, "id": export_id}},
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

            print(f"下载地址 (尝试 {attempt}):", url)

            res = requests.get(url, timeout=180)
            res.raise_for_status()

            if not res.content or len(res.content) < 10:
                raise ValueError("下载的内容为空或无效!")

            return res.content

        except Exception as e:
            print(f"⚠️ 第 {attempt}/{max_retries} 次下载失败 ({day}): {e}")
            if attempt < max_retries:
                time.sleep(5)
            else:
                raise Exception(f"多次尝试后无法下载日期 {day} 的 CSV。")


# =============================
# 写入 SQLite
# =============================
def save_db(csv_content, day):
    print("📥 写入 SQLite:", day)

    df = pd.read_csv(BytesIO(csv_content), encoding="utf-8")

    user_col = None
    invite_col = None
    channel_col = None

    for c in df.columns:
        name = str(c).lower().strip()
        if name in ["userid", "user_id", "会员id", "用户id"]:
            user_col = c
        elif name in ["inviteid", "invite_id", "邀请id"]:
            invite_col = c
        elif name in ["channelname", "channel", "渠道"]:
            channel_col = c

    df["会员id"] = df[user_col] if user_col else ""
    df["邀请id"] = df[invite_col] if invite_col else ""
    df["渠道"] = df[channel_col] if channel_col else ""

    def check_type(row):
        invite = str(row["邀请id"]).strip()
        if invite in ["", "nan", "None", "0"]:
            return "直推"
        return "裂变"

    df["类型"] = df.apply(check_type, axis=1)
    df["统计时间"] = day

    df = df[["统计时间", "会员id", "邀请id", "渠道", "类型"]]
    df = df.replace([np.inf, -np.inf], "")
    df = df.fillna("")

    db = Path(__file__).parent / "73J.db"
    conn = sqlite3.connect(db)
    conn.execute(
        """
    CREATE TABLE IF NOT EXISTS shouchong (
        统计时间 TEXT,
        会员id TEXT,
        邀请id TEXT,
        渠道 TEXT,
        类型 TEXT,
        PRIMARY KEY (统计时间, 会员id)
    )
    """
    )

    rows = df.values.tolist()
    conn.executemany(
        """INSERT OR IGNORE INTO shouchong
    (统计时间, 会员id, 邀请id, 渠道, 类型)
    VALUES (?, ?, ?, ?, ?)
    """,
        rows,
    )

    added = conn.total_changes
    conn.commit()
    conn.close()
    print(f"✅ 保存 SQLite，新增 {added} 条")


# =============================
# MAIN
# =============================
if __name__ == "__main__":
    days = get_need_days()

    if not days:
        print("✅ 数据已经最新")
        exit()

    print("需要更新:", days)

    for day in days:
        try:
            # 1. 创建任务并精准锁定专属 ID (通过时间、模块、remark和操作人)
            export_id = create_and_get_export_id(day)

            if not export_id:
                print(f"❌ 无法获取日期 {day} 的导出 ID")
                continue

            # 2. 等待该专属 ID 导出完成
            success = False
            for i in range(60):
                status = check_status(export_id)
                print(f"状态 [ID: {export_id}]: {status} ({i+1}/60)")

                if status == "ExportSuccess":
                    success = True
                    break
                elif status in ["ExportFailed", "Failed", "Error"]:
                    print(f"❌ 任务 {export_id} 在服务器端处理失败")
                    break

                time.sleep(10)

            # 3. 成功后精准下载该 ID 的文件
            if success:
                csv_content = download_csv(export_id, day)
                save_db(csv_content, day)
            else:
                print(f"❌ 导出超时或失败: {day}")

        except Exception as e:
            print("❌ 错误:", e)

    print("\n🎉 全部更新完成")