from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
import gspread
import requests

### ----------------------- Xử lý lấy dữ liệu từ API và lưu trữ dữ liệu để làm việc với Google Sheet -----------------------
def call_api(date):
    headers = {
        # Mỗi khi bị đăng xuất thì cần phải chỉnh lại tham số cấu hình xác thực
        'account': '3caaron',
        'authorization': 'Bearer us8qmqib4oq4wwhtmg4l5vsdyu2e4drqpnib16a8',
    }
    params = {
        # Chỉnh tham số xác thực ở tenantId
        'input': f'{{"json":{{"tenantId":8416670,"dateTime":"{date}"}}}}',
    }
    # Cập nhật lại đường link nếu dùng dữ liệu từ hệ thống nhà đài khác
    response = requests.get('https://api5.v-n-r-1.com/api/backend/trpc/realTimeData.list', params=params, headers=headers)
    data = response.json()
    all_data_list = data["result"]["data"]["json"]

    return all_data_list

### ------------------------- Tự động hóa theo ngày Việt Nam để tự lấy 4 ngày trở lại đây của Brazil -------------------------
now_vn = datetime.now()

# Convert sang ngày Brazil (UTC-3)
now_brazil = now_vn - timedelta(hours=10)

dates = [
    (now_brazil - timedelta(days=i)).strftime("%Y-%m-%d")
    for i in range(4)
]
### -------------------- Xong việc tự động hóa theo ngày Việt Nam để tự lấy 4 ngày trở lại đây của Brazil --------------------

### ------------------------------ Tự động hóa theo giờ Việt Nam để tự lấy chính xác giờ Brazil ------------------------------
time_now_vn = datetime.now()
vn_hour = time_now_vn.hour

brazil_hour = (vn_hour - 10) % 24
hour_key_brazil = f"{brazil_hour:02d}:00" # Vietnam: 17:00 --> Brazil: 07:00
### -------------------------- Xong việc tự động hóa theo giờ Việt Nam để tự lấy chính xác giờ Brazil --------------------------

print(f"Đang lấy dữ liệu nhà đài 33CC lúc {hour_key_brazil} Brazil ...")

final_data = {}

for date in dates:
    # Lấy từng ngày một theo thứ tự giảm dần
    data_list = call_api(date)

    for item in data_list:
        ### --------------------------------- Xử lý lấy các dữ liệu theo từng ngày từ API ---------------------------------
        # Parse time
        utc_time = datetime.fromisoformat(item["createTime"].replace("Z", ""))
        # Convert sang giờ Brazil (UTC-3)
        brazil_time = utc_time - timedelta(hours=3)
        # Lấy giờ và phút Brazil
        hour = brazil_time.hour
        minute = brazil_time.minute

        if minute == 0:
            # Xử lý lại số liệu
            recharge = item["rechargeAmount"] // 100
            withdraw = item["withdrawAmount"] // 100
            tenantProfit = round(item["tenantProfitAmount"] / 100, 2)
            manualRecharge = item["manualRechargeAmount"] // 100
            orderRecharge = item["orderRechargeAmount"] // 100
            manualWithdraw = item["manualWithdrawAmount"] // 100
            orderWithdraw = item["orderWithdrawAmount"] // 100
            diff = recharge - withdraw
            discount = item["discountAmount"] / 100
            # Format giờ đúng cấu trúc HH:00
            hour_key = f"{hour:02d}:00"

            if hour_key not in final_data:
                final_data[hour_key] = {}

            final_data[hour_key][date] = {
                "loginCount (登录用户)"                                     : item["loginCount"],
                "registerCount (新增注册)"                                  : item["registerCount"],
                "betCount (投注用户)"                                       : item["betCount"],
                "onlineCount (同时在线)"                                    : item["onlineCount"],
                "firstRechargeCount (首充用户)"                             : item["firstRechargeCount"],
                "subFirstRechargeCount (裂变首充)"                          : item["subFirstRechargeCount"],
                "rechargeCount (充值用户)"                                  : item["rechargeCount"],
                "tenantProfit (平台盈利)"                                   : tenantProfit,
                "manualRechargeAmount/manualRechargeTimes (人工充值/订单数)" : f'{manualRecharge} / {item["manualRechargeTimes"]}',
                "orderRechargeAmount/orderRechargeTimes (订单充值/订单数)"   : f'{orderRecharge} / {item["orderRechargeTimes"]}',
                "manualWithdrawAmount/manualWithdrawTimes (人工提现/订单数)" : f'{manualWithdraw} / {item["manualWithdrawTimes"]}',
                "orderWithdrawAmount/orderWithdrawTimes (订单提现/订单数)"   : f'{orderWithdraw} / {item["orderWithdrawTimes"]}',
                "充提差"                                                    : diff,
                "discountAmount (赠送金额)"                                 : discount,
            }
        ### ----------------------------- Đã xử lý xong việc lấy các dữ liệu theo từng ngày từ API -----------------------------

# Sắp xếp lại dữ liệu
final_data = dict(sorted(final_data.items()))

### ------------------- Đã xong việc xử lý lấy dữ liệu từ API và lưu trữ dữ liệu để làm việc với Google Sheet -------------------

### ------------------- Kết nối tới Google Sheet -------------------

# Quyền truy cập
scopes = ["https://www.googleapis.com/auth/spreadsheets"]

# Load credentials
creds = Credentials.from_service_account_file(
    "credentials.json", scopes=scopes
)

# Kết nối
client = gspread.authorize(creds)

# Mở Google Sheet
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1gfsTt_nL0wK2mepUAXkBgRqZHLYRY3xqWmbAxkzp0ao/edit?pli=1&gid=0#gid=0").sheet1


### -------------------------------------- Đã xong việc kết nối tới Google Sheet --------------------------------------

### -------------------------------------- Lảm việc và xử lý với Google Sheet --------------------------------------

# Tạo Mapping
# Theo dòng (dữ liệu)
row_mapping = {
    "loginCount (登录用户)": 2,
    "registerCount (新增注册)": 3,
    "betCount (投注用户)": 4,
    "onlineCount (同时在线)": 5,
    "firstRechargeCount (首充用户)": 6,
    "subFirstRechargeCount (裂变首充)": 7,
    "rechargeCount (充值用户)": 8,
    "tenantProfit (平台盈利)": 9,
    "manualRechargeAmount/manualRechargeTimes (人工充值/订单数)": 10,
    "orderRechargeAmount/orderRechargeTimes (订单充值/订单数)": 11,
    "manualWithdrawAmount/manualWithdrawTimes (人工提现/订单数)": 12,
    "orderWithdrawAmount/orderWithdrawTimes (订单提现/订单数)": 13,
    "充提差": 14,
    "discountAmount (赠送金额)": 15,
}

# Theo cột (ngày)
col_mapping = {
    date: idx + 2
    for idx, date in enumerate(dates)
}

# Tạo helper chuyển (row, col) → "A1"
def to_cell(row, col):
    letter = chr(64 + col)
    return f"{letter}{row}"

# Tạo bảng dữ liệu
table = []
keys = list(row_mapping.keys())

print(f"Đang ghi dữ liệu nhà đài 33CC lúc {hour_key_brazil} Brazil lên Google Sheet ...")

# Tiến hành lưu dữ liệu trong bảng
for key in keys:
    row_data = [key]  # cột A (label)
    for date in dates:
        value = final_data[hour_key_brazil][date][key]
        row_data.append(value)

    table.append(row_data)

# Tiến hành ghi dữ liệu trên Google Sheet
sheet.update(
    range_name="A2",
    values=table
)

# Cập nhật theo giờ
sheet.update(range_name="G2", values=[[hour_key_brazil]])

print(f"Ghi dữ liệu nhà đài 33CC lúc {hour_key_brazil} Brazil lên Google Sheet thành công!")

# Đã lấy dữ liệu thành công nhưng chương trình chạy chậm
"""
for date in final_data[hour_key_brazil]:
    col = col_mapping[date]
    for key, value in final_data[hour_key_brazil][date].items():
        row = row_mapping[key]
        cell = to_cell(row, col)
        sheet.update(range_name=cell, values=[[value]])
"""

### -------------------------------------- Làm việc với file Excel local --------------------------------------

"""
wb = load_workbook("33CC_DataTemplate.xlsx")
ws = wb.active

# Tạo Mapping
# Theo dòng (dữ liệu)
row_mapping = {
    "loginCount (登录用户)": 2,
    "registerCount (新增注册)": 3,
    "betCount (投注用户)": 4,
    "onlineCount (同时在线)": 5,
    "firstRechargeCount (首充用户)": 6,
    "subFirstRechargeCount (裂变首充)": 7,
    "rechargeCount (充值用户)": 8,
    "tenantProfit (平台盈利)": 9,
    "manualRechargeAmount/manualRechargeTimes (人工充值/订单数)": 10,
    "orderRechargeAmount/orderRechargeTimes (订单充值/订单数)": 11,
    "manualWithdrawAmount/manualWithdrawTimes (人工提现/订单数)": 12,
    "orderWithdrawAmount/orderWithdrawTimes (订单提现/订单数)": 13,
    "充提差": 14,
    "discountAmount (赠送金额)": 15,
}

# Theo cột (ngày)
col_mapping = {
    date: idx + 2
    for idx, date in enumerate(dates)
}

# Tạo datetime cho Excel
excel_time = datetime(1900, 1, 1, brazil_hour, 0, 0)

# Ghi vào Excel
ws["G2"] = excel_time
ws["G2"].number_format = "h:mm"

# Bắt đầu gán từng dữ liệu từng ngày theo mốc giờ cho file Excel
for date in final_data[hour_key_brazil]:
    col = col_mapping[date]
    for key, value in final_data[hour_key_brazil][date].items():
        row = row_mapping[key]
        ws.cell(row=row, column=col, value=value)

print(f"Đã lấy thành công dữ liệu nhà đài 33CC lúc {hour_key_brazil} Brazil!")

wb.save(f"33CC_DataPerHour/33CC-{brazil_hour:02d}h.xlsx")
"""
### -------------------------------------- Làm xong việc với file Excel --------------------------------------
