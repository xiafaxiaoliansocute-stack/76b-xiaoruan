import pandas as pd
import gspread
import time

from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials


# ==================================================
# GOOGLE CONFIG
# ==================================================

GOOGLE_JSON = (
    "/Users/xiaoruan/Documents/service_account.json"
)

SHEET_ID = (
    "1gfsTt_nL0wK2mepUAXkBgRqZHLYRY3xqWmbAxkzp0ao"
)

SHEET_FIRST = "每日首充"
SHEET_RECHARGE = "三方充值"
SHEET_OUTPUT = "留存1"


# ==================================================
# 留存天数
# ==================================================

RETENTION_LIST = [
    1,      # 二日
    2,      # 三日
    3,      # 四日
    4,      # 五日
    5,      # 六日
    6,      # 七日
    9,      # 十日
    13,     # 十四日
    29      # 三十日
]

RETENTION_NAME = {
    1: "二日留存",
    2: "三日留存",
    3: "四日留存",
    4: "五日留存",
    5: "六日留存",
    6: "七日留存",
    9: "十日留存",
    13: "十四日留存",
    29: "三十日留存"
}


# ==================================================
# Google
# ==================================================

def get_client():

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_file(
        GOOGLE_JSON,
        scopes=scopes
    )

    return gspread.authorize(creds)


# ==================================================
# 读取Sheet
# ==================================================

def read_sheet(sheet_name):

    client = get_client()

    ws = client.open_by_key(
        SHEET_ID
    ).worksheet(
        sheet_name
    )

    data = ws.get_all_records()

    df = pd.DataFrame(data)

    print(f"{sheet_name} 数量: {len(df)}")

    return df


# ==================================================
# 数据清理
# ==================================================

def clean_data(first_df, recharge_df):

    print("开始清理数据...")

    # ---------- 首充 ----------

    first_df["会员id"] = (
        first_df["会员id"]
        .astype(str)
        .str.strip()
    )

    first_df["统计时间"] = pd.to_datetime(
        first_df["统计时间"]
    )

    # ---------- 三方充值 ----------

    recharge_df["会员id"] = (
        recharge_df["会员id"]
        .astype(str)
        .str.strip()
    )

    recharge_df["完成时间"] = pd.to_datetime(
        recharge_df["完成时间"]
    )

    recharge_df["支付金额"] = pd.to_numeric(
        recharge_df["支付金额"],
        errors="coerce"
    ).fillna(0)

    recharge_df["支付次数"] = pd.to_numeric(
        recharge_df["支付次数"],
        errors="coerce"
    ).fillna(0)

    print("清理完成")

    return first_df, recharge_df
# ==================================================
# 建立充值索引
# ==================================================

def build_recharge_map(recharge_df):

    print("建立充值索引...")

    recharge_map = {}

    # Gom theo会员
    for uid, group in recharge_df.groupby("会员id"):

        recharge_map[uid] = {

            # Các ngày có phát sinh nạp
            "dates": set(
                group["完成时间"].dt.date
            ),

            # Tổng tiền
            "amount": group["支付金额"].sum(),

            # Tổng số lần nạp
            "count": group["支付次数"].sum(),

            # Tiền theo từng ngày (để tính首充金额 nhanh hơn)
            "amount_by_date": (
                group
                .groupby(group["完成时间"].dt.date)["支付金额"]
                .sum()
                .to_dict()
            )
        }

    print("充值会员:", len(recharge_map))

    return recharge_map


# ==================================================
# 计算留存（第一部分）
# ==================================================

def calc_retention(first_df, recharge_df):

    start = time.time()

    recharge_map = build_recharge_map(recharge_df)

    result = []

    group_cols = [
        "统计时间",
        "会员渠道"
    ]

    print("开始计算...")

    for (day, channel), group in first_df.groupby(group_cols):

        total_users = set(group["会员id"])

        total_count = len(total_users)

        direct_users = set(
            group[
                group["直推/裂变"] == "直推"
            ]["会员id"]
        )

        split_users = set(
            group[
                group["直推/裂变"] == "裂变"
            ]["会员id"]
        )

        row = {

            "日期": day.strftime("%Y-%m-%d"),

            "渠道": channel,

            "总首充": total_count,

            "直推首冲": len(direct_users),

            "裂变首冲": len(split_users)

        }

        # ============================================
        # 首充金额 + 复冲率
        # ============================================

        first_amount = 0

        repeat_users = 0

        for uid in total_users:

            info = recharge_map.get(uid)

            if info is None:
                continue

            # 首充当天金额
            first_amount += info["amount_by_date"].get(
                day.date(),
                0
            )

            # ★ 修正复冲率（按支付次数）
            if info["count"] > 1:
                repeat_users += 1

        row["首充金额"] = round(first_amount, 2)

        row["复充人数"] = repeat_users

        row["复充率"] = (
            round(repeat_users / total_count, 4)
            if total_count else 0
        )

        # ============================================
        # 留存
        # （Phần 3 sẽ tiếp tục ngay dưới đây）
        # ============================================
                # ============================================
        # 留存计算
        # ============================================

        for day_num in RETENTION_LIST:

            check_date = (
                day.date() +
                timedelta(days=day_num)
            )

            total_ret = 0
            direct_ret = 0
            split_ret = 0

            for uid in total_users:

                info = recharge_map.get(uid)

                if info is None:
                    continue

                if check_date not in info["dates"]:
                    continue

                total_ret += 1

                if uid in direct_users:
                    direct_ret += 1

                elif uid in split_users:
                    split_ret += 1

            name = RETENTION_NAME[day_num]

            # -----------------------------
            # 总留存（数值，Google显示百分比）
            # -----------------------------
            row[name] = (
                round(total_ret / total_count, 4)
                if total_count else 0
            )

            # -----------------------------
            # 直推留存
            # -----------------------------
            if len(direct_users):

                rate = direct_ret / len(direct_users)

                row[name + "直推"] = (
                    f"{rate:.2%} ({direct_ret})"
                )

            else:

                row[name + "直推"] = "0.00% (0)"

            # -----------------------------
            # 裂变留存
            # -----------------------------
            if len(split_users):

                rate = split_ret / len(split_users)

                row[name + "裂变"] = (
                    f"{rate:.2%} ({split_ret})"
                )

            else:

                row[name + "裂变"] = "0.00% (0)"

        result.append(row)

    # ============================================
    # DataFrame
    # ============================================

    df = pd.DataFrame(result)

    print("生成行:", len(df))

    print(
        "计算耗时:",
        round(time.time() - start, 2),
        "秒"
    )

    return df
# ==================================================
# 整理输出格式
# ==================================================

def format_output(df):

    columns = [

        "日期",
        "渠道",
        "总首充",
        "直推首冲",
        "裂变首冲",
        "首充金额",
        "复充率",

        "二日留存",
        "二日留存直推",
        "二日留存裂变",

        "三日留存",
        "三日留存直推",
        "三日留存裂变",

        "四日留存",
        "四日留存直推",
        "四日留存裂变",

        "五日留存",
        "五日留存直推",
        "五日留存裂变",

        "六日留存",
        "六日留存直推",
        "六日留存裂变",

        "七日留存",
        "七日留存直推",
        "七日留存裂变",

        "十日留存",
        "十日留存直推",
        "十日留存裂变",

        "十四日留存",
        "十四日留存直推",
        "十四日留存裂变",

        "三十日留存",
        "三十日留存直推",
        "三十日留存裂变"

    ]

    for col in columns:

        if col not in df.columns:
            df[col] = ""

    df = df[columns]

    return df


# ==================================================
# 上传 Google Sheet
# 保留前两行
# 从A3开始上传
# ==================================================

def upload_retention(df):

    print("准备上传留存1...")

    client = get_client()

    ws = client.open_by_key(
        SHEET_ID
    ).worksheet(
        SHEET_OUTPUT
    )

    # ============================================
    # 只删除第三行以下
    # ============================================

    last_row = ws.row_count

    ws.batch_clear([
        f"A3:AI{last_row}"
    ])

    print("旧数据删除完成（保留第1、2行）")

    # ============================================
    # 整理上传数据
    # ============================================

    rows = []

    for date, group in df.groupby(
        "日期",
        sort=True
    ):

        rows.extend(
            group.values.tolist()
        )

        # 每个日期空一行
        rows.append(
            [""] * len(df.columns)
        )

    print(
        "准备上传",
        len(rows),
        "行"
    )

    # ============================================
    # 分批上传
    # ============================================

    batch_size = 5000

    start_row = 3

    for i in range(
        0,
        len(rows),
        batch_size
    ):

        part = rows[
            i:i + batch_size
        ]

        print(
            f"上传 A{start_row}"
        )

        ws.update(
            range_name=f"A{start_row}",
            values=part,
            value_input_option="USER_ENTERED"
        )

        start_row += len(part)

    print("✅ 留存1更新完成")
    # ==================================================
# MAIN
# ==================================================

if __name__ == "__main__":

    start = time.time()

    print("=" * 60)
    print("🚀 开始计算留存")
    print("=" * 60)

    # ============================================
    # 读取 Google Sheet
    # ============================================

    first_df = read_sheet(
        SHEET_FIRST
    )

    recharge_df = read_sheet(
        SHEET_RECHARGE
    )

    # ============================================
    # 清理数据
    # ============================================

    first_df, recharge_df = clean_data(
        first_df,
        recharge_df
    )

    print()
    print("首充数据:", len(first_df))
    print("充值数据:", len(recharge_df))
    print()

    # ============================================
    # 计算留存
    # ============================================

    result_df = calc_retention(
        first_df,
        recharge_df
    )

    print()
    print("计算完成")
    print()

    # ============================================
    # 整理输出格式
    # ============================================

    result_df = format_output(
        result_df
    )

    print("输出行数:", len(result_df))
    print()

    # ============================================
    # 排序
    # 日期升序
    # 渠道升序
    # ============================================

    result_df = result_df.sort_values(
        by=[
            "日期",
            "渠道"
        ],
        ascending=[
            True,
            True
        ]
    ).reset_index(drop=True)

    # ============================================
    # 上传 Google Sheet
    # ============================================

    upload_retention(
        result_df
    )

    print()
    print("=" * 60)
    print("🎉 全部完成")
    print(
        "耗时:",
        round(
            time.time() - start,
            2
        ),
        "秒"
    )
    print("=" * 60)
# ==================================================
# 检查数据
# ==================================================

def check_columns(first_df, recharge_df):

    first_need = [
        "会员id",
        "统计时间",
        "会员渠道",
        "直推/裂变"
    ]

    recharge_need = [
        "会员id",
        "完成时间",
        "支付金额",
        "支付次数"
    ]

    for c in first_need:

        if c not in first_df.columns:
            raise Exception(f"每日首充 缺少字段: {c}")

    for c in recharge_need:

        if c not in recharge_df.columns:
            raise Exception(f"三方充值 缺少字段: {c}")