from datetime import datetime, timedelta
import json
import os
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd
import requests

# ============================================================
# 1. CẤU HÌNH NHIỀU WEB
# ============================================================
WEB_CONFIGS = [
    {
        "name": "【15016】73J",
        "url": "https://api5.v-n-r-1.com/api/backend/trpc/platformRecord.detail",
        "tenantId": 1634560,
        "regionId": 1,
        "token": "s55v8su8dvgck7x1g2738elv6lb6z9wvp05onc5s",
    },
    {
        "name": "【16028】23E",
        "url": "https://api6.o-9-d-4.com/api/backend/trpc/platformRecord.detail",
        "tenantId": 9503839,
        "regionId": 1,
        "token": "op3dvim2q1xsrvng2wbt2itizu53fnmutk6sqz83",
    },
    {
        "name": "【16021】23A",
        "url": "https://api6.o-9-d-4.com/api/backend/trpc/platformRecord.detail",
        "tenantId": 2654039,
        "regionId": 1,
        "token": "viee7yg0flf11btvcih0m89cuveq6h25e7yrxs7q",
    },        

]

# ============================================================
# 2. TELEGRAM
# ============================================================
TELEGRAM_BOT_TOKEN = "8971726965:AAHG2LHxb2z97Rv2BUdzTRWPJCxrTHRqSI4"
TARGET_CHAT_ID = -5368832651

# ============================================================
# 3. NGÀY ĐỐI CHIẾU
# ============================================================
today = datetime.now()
date_yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
date_before = (today - timedelta(days=2)).strftime("%Y-%m-%d")

print("\n" + "=" * 60)
print("📌 BẮT ĐẦU ĐỐI CHIẾU")
print("=" * 60)
print(f"📅 昨天 (Hôm qua): {date_yesterday}")
print(f"📅 前天 (Hôm kia): {date_before}")
print(f"🌐 Tổng số WEB: {len(WEB_CONFIGS)}")
print("=" * 60 + "\n")


# ============================================================
# 4. TÌM FONT TIẾNG TRUNG
# ============================================================
def get_chinese_font():
    chinese_font = None
    font_names = [
        "pingfang",
        "heiti",
        "stheiti",
        "arial unicode ms",
        "microsoft yahei",
        "noto sans cjk",
    ]

    for font_path in fm.findSystemFonts(fontpaths=None, fontext="ttf"):
        try:
            prop = fm.FontProperties(fname=font_path)
            name = prop.get_name().lower()
            if any(fn in name for fn in font_names):
                chinese_font = prop
                break
        except Exception:
            continue
    return chinese_font


# ============================================================
# 5. LẤY DATA API
# ============================================================
def fetch_api_data(web_config, target_date):
    web_name = web_config["name"]
    api_url = web_config["url"]
    tenant_id = web_config["tenantId"]
    region_id = web_config["regionId"]
    token = web_config["token"]

    print(f"[{web_name}] 📥 Đang lấy dữ liệu {target_date}...")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    page = 1
    page_size = 5000
    all_records = []

    while True:
        params_data = {
            "json": {
                "regionId": region_id,
                "tenantId": tenant_id,
                "businessType": "OWN",
                "startTime": target_date,
                "endTime": target_date,
                "page": page,
                "pageSize": page_size,
                "order": [{"key": "returnRate", "type": "desc"}],
                "queryType": "table",
            }
        }

        encoded_input = urllib.parse.quote(json.dumps(params_data))
        full_url = f"{api_url}?input={encoded_input}"

        try:
            response = requests.get(full_url, headers=headers, timeout=30)
            if response.status_code != 200:
                print(f"[{web_name}] ❌ HTTP {response.status_code}: {response.text[:500]}")
                break

            res_json = response.json()
            rows = res_json.get("result", {}).get("data", {}).get("json", [])

            if not rows:
                break

            all_records.extend(rows)
            print(f"[{web_name}] 📄 Page {page}: {len(rows)} records")

            if len(rows) < page_size:
                break
            page += 1

        except Exception as e:
            print(f"[{web_name}] ❌ Lỗi API: {e}")
            break

    print(f"[{web_name}] ✅ {target_date}: {len(all_records)} records")
    return all_records


# ============================================================
# 6. LẤY 2 NGÀY CHO 1 WEB
# ============================================================
def fetch_web_data(web_config):
    web_name = web_config["name"]
    print(f"\n🚀 [{web_name}] BẮT ĐẦU")

    raw_data_before = fetch_api_data(web_config, date_before)
    raw_data_yesterday = fetch_api_data(web_config, date_yesterday)

    print(f"✅ [{web_name}] Hoàn thành lấy dữ liệu")
    return {
        "web_config": web_config,
        "before": raw_data_before,
        "yesterday": raw_data_yesterday,
    }


# ============================================================
# 7. CHUẨN HÓA DATAFRAME
# ============================================================
def prepare_dataframe(raw_data):
    df = pd.DataFrame(raw_data)
    if df.empty:
        return df

    for col in ["betAmount", "validBetAmount"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0) / 100.0

    for col in ["totalGameRounds", "totalUserCount"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


# ============================================================
# 8. GROUP DATA
# ============================================================
def group_dataframe(df):
    columns = [
        "platformName",
        "gameName",
        "validBetAmount",
        "totalUserCount",
        "totalGameRounds",
        "平均下注",
    ]

    if df.empty:
        return pd.DataFrame(columns=columns)

    agg_cols = {
        "validBetAmount": "sum",
        "totalUserCount": "sum",
        "totalGameRounds": "sum",
        "betAmount": "sum",
    }

    grouped = df.groupby(["platformName", "gameName"], as_index=False).agg(agg_cols)

    grouped["平均下注"] = grouped.apply(
        lambda row: round(row["betAmount"] / row["totalGameRounds"], 2)
        if row["totalGameRounds"] > 0
        else 0.0,
        axis=1,
    )

    return grouped


# ============================================================
# 9. KIỂM TRA BẤT THƯỜNG
# ============================================================
def check_anomaly(row):
    before_users = row.get("totalUserCount_前天", 0)
    yesterday_users = row.get("totalUserCount_昨天", 0)

    # Tổng người của 2 ngày < 200 thì bỏ qua
    if (before_users + yesterday_users) < 200:
        return ""

    if before_users == 0:
        return "异常" if yesterday_users > 0 else "正常"

    ratio = yesterday_users / before_users
    if ratio > 1.5 or ratio < 0.5:
        return "异常"

    return "正常"


# ============================================================
# 10. TẠO FINAL RESULT
# ============================================================
def process_data(raw_data_before, raw_data_yesterday):
    df_b = prepare_dataframe(raw_data_before)
    df_y = prepare_dataframe(raw_data_yesterday)

    b_grouped = group_dataframe(df_b)
    y_grouped = group_dataframe(df_y)

    merged = pd.merge(
        b_grouped,
        y_grouped,
        on=["platformName", "gameName"],
        how="outer",
        suffixes=("_前天", "_昨天"),
    ).fillna(0)

    merged["人数对比"] = merged.apply(check_anomaly, axis=1)

    final_result = pd.DataFrame({
        "厂商": merged["platformName"],
        "游戏名称": merged["gameName"],
        "有效投注_前天": merged["validBetAmount_前天"],
        "投注人数_前天": merged["totalUserCount_前天"],
        "注单数_前天": merged["totalGameRounds_前天"],
        "平均下注_前天": merged["平均下注_前天"],
        "有效投注_昨天": merged["validBetAmount_昨天"],
        "投注人数_昨天": merged["totalUserCount_昨天"],
        "注单_昨天": merged["totalGameRounds_昨天"],
        "平均下注_昨天": merged["平均下注_昨天"],
        "人数对比": merged["人数对比"],
    })

    return final_result


# ============================================================
# 11. GỬI TELEGRAM
# ============================================================
def send_telegram_photo(photo_path, caption):
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(photo_path, "rb") as photo:
            payload = {
                "chat_id": TARGET_CHAT_ID,
                "caption": caption,
                "parse_mode": "Markdown",
            }
            files = {"photo": photo}
            response = requests.post(telegram_url, data=payload, files=files, timeout=30)

        if response.status_code == 200:
            print("✅ Gửi Telegram thành công!")
            return True
        else:
            print(f"❌ Gửi Telegram thất bại:\n{response.text}")
            return False
    except Exception as e:
        print(f"❌ Lỗi Telegram: {e}")
        return False


# ============================================================
# 12. TẠO ẢNH BÁO CÁO
# ============================================================
def create_report_image(final_result, web_name):
    df_anomaly = (
        final_result[final_result["人数对比"] == "异常"]
        .sort_values(by=["有效投注_昨天", "投注人数_昨天"], ascending=[False, False])
    )

    if df_anomaly.empty:
        print(f"[{web_name}] ✨ Không có dữ liệu bất thường.")
        return None

    print(f"[{web_name}] 🚨 Phát hiện {len(df_anomaly)} dòng bất thường.")

    chinese_font = get_chinese_font()
    if chinese_font:
        plt.rcParams["font.family"] = chinese_font.get_name()
    else:
        plt.rcParams["font.sans-serif"] = ["Arial Unicode MS", "PingFang SC", "sans-serif"]

    plt.rcParams["axes.unicode_minus"] = False

    table_data = []
    for _, row in df_anomaly.iterrows():
        table_data.append([
            str(row["厂商"]),
            str(row["游戏名称"]),
            f"{row['有效投注_前天']:,.2f}",
            int(row["投注人数_前天"]),
            int(row["注单数_前天"]),
            f"{row['平均下注_前天']:.2f}",
            f"{row['有效投注_昨天']:,.2f}",
            int(row["投注人数_昨天"]),
            int(row["注单_昨天"]),
            f"{row['平均下注_昨天']:.2f}",
            str(row["人数对比"]),
        ])

    header_row = [
        "厂商",
        "游戏名称",
        f"有效投\n({date_before})",
        f"投注人数\n({date_before})",
        f"注单数\n({date_before})",
        f"平均下注\n({date_before})",
        f"有效投\n({date_yesterday})",
        f"投注人数\n({date_yesterday})",
        f"注单数\n({date_yesterday})",
        f"平均下注\n({date_yesterday})",
        "人数对比",
    ]

    full_table_data = [header_row] + table_data

    # Tạo khung vẽ với chiều cao thoáng hơn một chút để chứa tiêu đề phía trên
    fig, ax = plt.subplots(figsize=(16, max(4, len(full_table_data) * 0.45 + 1.8)))
    ax.axis("off")
    ax.axis("tight")

    # 📌 ĐẶT TIÊU ĐỀ CHUẨN XÁC Ở PHÍA TRÊN CÙNG (Dùng suptitle của figure để tránh bị đè hoặc lệch bảng)
    title_text = f"{web_name} 游戏跟进异常人数变动报告"
    fig.suptitle(
        title_text, 
        fontsize=18, 
        weight="bold", 
        y=0.95,  # Vị trí chiều dọc nằm ở đỉnh ảnh
        fontproperties=chinese_font if chinese_font else None
    )

    col_widths = [0.08, 0.16, 0.095, 0.095, 0.095, 0.095, 0.095, 0.095, 0.095, 0.095, 0.10]
    
    # Giữ nguyên bản cấu trúc bảng gốc đẹp đẽ
    the_table = ax.table(cellText=full_table_data, loc="center", cellLoc="center", colWidths=col_widths)

    the_table.auto_set_font_size(False)
    the_table.set_fontsize(10)
    the_table.scale(1.2, 1.5)

    cells = the_table.get_celld()

    # Định dạng Header
    for c in range(11):
        header_cell = cells[(0, c)]
        header_cell.get_text().set_fontsize(16)
        header_cell.get_text().set_weight("bold")
        header_cell.get_text().set_verticalalignment("center")
        header_cell.set_height(0.08)

        if c in [0, 1]:
            header_cell.set_facecolor("#ffe599")
        elif 2 <= c <= 5:
            header_cell.set_facecolor("#f9cb9c")
        elif 6 <= c <= 9:
            header_cell.set_facecolor("#bf9000")
            header_cell.get_text().set_color("white")
        elif c == 10:
            header_cell.set_facecolor("#a2d9ce")

    # Định dạng Data Rows
    for r in range(1, len(full_table_data)):
        for c in range(11):
            data_cell = cells[(r, c)]
            data_cell.set_facecolor("#fcfcfc")
            data_cell.set_height(0.03)
            data_cell.get_text().set_fontsize(10)
            data_cell.get_text().set_weight("bold")
            data_cell.get_text().set_verticalalignment("center")

            if c == 10:
                data_cell.get_text().set_color("#d9534f")

    if chinese_font:
        for key, cell in cells.items():
            cell.get_text().set_fontproperties(chinese_font)
            cell.get_text().set_fontsize(16 if key[0] == 0 else 10)
            cell.get_text().set_weight("bold")

    safe_web_name = web_name.replace("/", "_").replace("\\", "_").replace(" ", "_")
    output_img_path = f"anomaly_{safe_web_name}_{date_yesterday}.png"

    # Lưu ảnh với bbox_inches='tight' để tự động căn chuẩn phần tiêu đề suptitle vừa thêm
    plt.savefig(output_img_path, bbox_inches="tight", dpi=200)
    plt.close()

    print(f"[{web_name}] 🖼️ Đã tạo ảnh: {output_img_path}")
    return output_img_path

# ============================================================
# 13. XỬ LÝ 1 WEB
# ============================================================
def process_one_web(web_result):
    web_config = web_result["web_config"]
    web_name = web_config["name"]

    print("\n" + "=" * 60)
    print(f"📊 ĐANG XỬ LÝ: {web_name}")
    print("=" * 60)

    try:
        final_result = process_data(web_result["before"], web_result["yesterday"])
        output_img_path = create_report_image(final_result, web_name)

        if output_img_path is None:
            return

        caption = (
            f"⚠️ *游戏跟进异常人数变动报告* 🚨\n"
            f"🌐 站点: `{web_name}`\n"
            f"📅 对比: `{date_yesterday}` 和 `{date_before}`"
        )

        send_telegram_photo(output_img_path, caption)

        if os.path.exists(output_img_path):
            os.remove(output_img_path)
            print(f"[{web_name}] 🧹 Đã xóa file ảnh tạm.")

    except Exception as e:
        print(f"[{web_name}] ❌ Lỗi xử lý WEB: {e}")


# ============================================================
# 14. MAIN
# ============================================================
def main():
    print("\n" + "=" * 60)
    print("🚀 BẮT ĐẦU LẤY TẤT CẢ WEB SONG SONG")
    print("=" * 60)

    all_results = []
    max_workers = max(1, len(WEB_CONFIGS))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_web_data, web_config): web_config
            for web_config in WEB_CONFIGS
        }

        for future in as_completed(futures):
            web_config = futures[future]
            web_name = web_config["name"]
            try:
                result = future.result()
                all_results.append(result)
                print(f"✅ [{web_name}] Đã lấy xong.")
            except Exception as e:
                print(f"❌ [{web_name}] Lỗi: {e}")

    print("\n" + "=" * 60)
    print("📊 BẮT ĐẦU TẠO BÁO CÁO")
    print("=" * 60)

    for result in all_results:
        process_one_web(result)

    print("\n" + "=" * 60)
    print("🎉 TẤT CẢ WEB ĐÃ HOÀN THÀNH")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()