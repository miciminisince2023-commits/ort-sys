import re
import requests
import pandas as pd
from datetime import date, timedelta, datetime

# Import trực tiếp các hàm từ hệ thống hiện tại của bạn
# Đảm bảo file auto_email_job.py được đặt cùng thư mục gốc với app.py
from database.db_helper import get_st_requests, get_report_qty
# Giả sử bạn có hàm get_power_tools() để lấy df_power_tool, nếu tên khác hãy đổi lại nhé
from database.db_helper import get_processed_power_tool_data 

WEBHOOK_URL = "https://default8b8cc6cf0eaa4b6498e46d4672c449.30.environment.api.powerplatform.com:443/powerautomate/automations/direct/cu/20/workflows/4d841d0ea31c42069815cbc8825f8772/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=cS8aqbT_i151ug54txEagGvZQF0i-OUPu5w1jg2lYNs"
# Khai báo thông tin người chịu trách nhiệm (P.I.C)
PIC_SHORTAGE_NAME = "Loki"
PIC_SHORTAGE_EMAIL = "Minhhung.Pham@ttigroup.com.vn"

PIC_REPORT_NAME = "Jason"
PIC_REPORT_EMAIL = "Minhhung.Pham@ttigroup.com.vn"

# Tự động gom email lại để gửi cho Power Automate
TARGET_EMAILS = f"{PIC_SHORTAGE_EMAIL}; {PIC_REPORT_EMAIL}"

TABLE_STYLE = 'border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; font-size: 13px; text-align: left;"'
TH_STYLE = 'background-color: #000000; color: #EBE600; font-weight: bold; text-align: center;'

def prepare_data():
    # ==========================================
    # 1. TÍNH TOÁN NGÀY PENDING (Tái sử dụng logic từ dashboard.txt)
    # ==========================================
    today = date.today()
    yesterday = today - timedelta(days=1)
    missing_dates = []
    
    df_recent = get_report_qty(all_time=True) 
    if not df_recent.empty and "rec_date" in df_recent.columns:
        all_dates = pd.to_datetime(df_recent["rec_date"], errors="coerce").dt.date
        valid_dates = all_dates[all_dates <= yesterday]
        
        if not valid_dates.empty:
            last_report_date = valid_dates.max()
            if last_report_date < yesterday:
                curr_date = last_report_date + timedelta(days=1)
                while curr_date <= yesterday:
                    missing_dates.append(curr_date.strftime("%b %d %Y"))
                    curr_date += timedelta(days=1)
                    
    pending_days_b = len(missing_dates)

    # ==========================================
    # 2. LỌC SHORTAGE ALERTS (Tái sử dụng logic Gap > 0)
    # ==========================================
    df_power_tool = get_processed_power_tool_data() # Lấy data Master
    df_shortage = pd.DataFrame()
    
    if not df_power_tool.empty and "Gap" in df_power_tool.columns:
        df_shortage = df_power_tool[df_power_tool["Gap"] > 0].sort_values(by="Gap", ascending=False)
        if not df_shortage.empty:
            cols_to_show = ["ORT model", "Model name", "P.I.C", "Gap", "Action required"]
            cols_exist = [col for col in cols_to_show if col in df_shortage.columns]
            df_shortage = df_shortage[cols_exist].reset_index(drop=True)
            df_shortage.insert(0, 'STT', range(1, len(df_shortage) + 1)) # Thêm dòng này
            #df_shortage.index = df_shortage.index + 1

    # ==========================================
    # 3. LỌC ACTIVE REQUESTS (Tái sử dụng logic != "closed")
    # ==========================================
    df_st = get_st_requests()
    df_active = pd.DataFrame()
    
    if not df_st.empty and "req_status" in df_st.columns:
        # Xử lý đổi tên cột cho giống dashboard
        df_st = df_st.rename(columns={
            "req_id": "Req. id", "req_date": "Req. date", "tti_model": "TTI model", 
            "ort_model": "ORT model", "req_qty": "Req. qty", "sam_job": "SAM Job", 
            "cb_f": "CB/F", "scp_f": "SCP/F", "dr_f": "DR/F", "item_test": "Item Test", 
            "start_date": "Start date", "end_date": "End date", "test_result": "Test result", 
            "req_status": "Req. status", "req_duration": "Req. duration"
        })
        
        df_active = df_st[df_st["Req. status"].astype(str).str.strip().str.lower() != "closed"].copy()
        if not df_active.empty:
            st_cols_to_show = ["Req. id", "Req. date", "TTI model", "ORT model", "Req. qty", "Req. duration", "Req. status"]
            st_cols_exist = [col for col in st_cols_to_show if col in df_active.columns]
            if "Req. date" in df_active.columns:
                df_active = df_active.sort_values(by="Req. date", ascending=False)
            df_active = df_active[st_cols_exist].reset_index(drop=True)
            df_active.insert(0, 'STT', range(1, len(df_active) + 1)) # Thêm dòng này
            #df_active.index = df_active.index + 1

    # Ép xóa sạch tên trục cột để Pandas không sinh thêm dòng thừa
    df_shortage.columns.name = None
    df_active.columns.name = None
    
    return df_shortage, df_active, pending_days_b

def send_automated_report():
    print("Đang tổng hợp dữ liệu...")
    df_shortage, df_active, pending_days_b = prepare_data()
    
    # 1. Chuyển DataFrame thành HTML (Thêm index=False để loại bỏ cột index đen xì)
    if not df_shortage.empty:
        html_shortage = df_shortage.to_html(index=False, classes='qm-table', border=0)
    else:
        html_shortage = "<p style='color: green;'>✅ Tuyệt vời! Hiện tại hệ thống không ghi nhận Model nào bị thiếu mẫu.</p>"
        
    if not df_active.empty:
        html_active = df_active.to_html(index=False, classes='qm-table', border=0)
    else:
        html_active = "<p style='color: green;'>✅ Không có Request nào đang bị tồn đọng.</p>"

    # 2. Xây dựng form HTML
    email_body = f"""
    <div style="font-family: Arial, sans-serif; color: #333; max-width: 900px; margin: auto;">
        <h2 style="color: #000000; background-color: #EBE600; padding: 12px; text-align: center; margin-bottom: 30px;">
            ⚠️ VN ORT SYSTEM ALERT ({datetime.now().strftime('%d/%m/%Y')})
        </h2>
        
        <div style="margin-bottom: 30px;">
            <p>Dear <a href="mailto:{PIC_SHORTAGE_EMAIL}" style="color: #0078D4; text-decoration: none; font-weight: bold;">@{PIC_SHORTAGE_NAME}</a>,</p>
            <p>There are currently <span style="color: red; font-weight: bold; font-size: 16px;">{len(df_shortage)}</span> model with <b>SAMPLE SHORTAGE</b> (Gap > 0):</p>
            {html_shortage}
            
            <br>
            <p>List of <b>ACTIVE REQUESTS</b> not yet Closed:</p>
            {html_active}
        </div>
        
        <hr style="border: 1px solid #ddd; margin: 25px 0;">
        
        <div style="margin-bottom: 30px;">
            <p>Dear <a href="mailto:{PIC_REPORT_EMAIL}" style="color: #0078D4; text-decoration: none; font-weight: bold;">@{PIC_REPORT_NAME}</a>,</p>
            <p>The system has detected that you are missing <span style="font-size: 20px; color: red; font-weight: bold;">{pending_days_b}</span> day(s) of Report Qty data.</p>
            <p><i>Please access the Dashboard and update the missing data to ensure reporting progress stays on track.</i></p>
        </div>
    </div>
    """
    
    # ==========================================
    # 3. Add CSS cho Table Outlook bằng REGEX (Bản vá lỗi dòng thừa)
    # ==========================================
    # Xóa định dạng căn lề phải mặc định gây lệch khung của Pandas
    email_body = email_body.replace('<tr style="text-align: right;">', '<tr>')
    
    # Ép thẻ table luôn full width
    email_body = re.sub(
        r'<table[^>]*>', 
        '<table width="100%" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%; min-width: 100%; border: 1px solid #bbbbbb; font-family: Arial, sans-serif; font-size: 13px; text-align: left;">', 
        email_body
    )
    
    # Ép lưới và CĂN GIỮA nội dung cho từng ô dữ liệu (TD)
    email_body = re.sub(
        r'<td(.*?)>', 
        r'<td\1 style="border: 1px solid #dddddd; padding: 8px; text-align: center;">', 
        email_body
    )
    
    # Ép màu vàng đen thương hiệu cho Header (TH) - dùng \1 để giữ nguyên thuộc tính gốc
    email_body = re.sub(
        r'<th(.*?)>', 
        r'<th\1 style="border: 1px solid #aaaaaa; padding: 10px; background-color: #000000; color: #EBE600; font-weight: bold; text-align: center;">', 
        email_body
    )
    
    # 4. Gửi qua Power Automate
    payload = {"html_content": email_body, "target_emails": TARGET_EMAILS}
    print("Đang gửi qua Power Automate...")
    response = requests.post(WEBHOOK_URL, json=payload)
    
    if response.status_code == 202:
        print("✅ Đã gửi báo cáo thành công!")
    else:
        print(f"❌ Lỗi gửi email: {response.status_code} - {response.text}")

if __name__ == "__main__":
    send_automated_report()