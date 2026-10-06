import re
import requests
import pandas as pd
from datetime import date, timedelta, datetime

from database.db_helper import get_st_requests, get_report_qty
from database.db_helper import get_processed_power_tool_data
from database.db_helper import get_email_config

WEBHOOK_URL = "https://default8b8cc6cf0eaa4b6498e46d4672c449.30.environment.api.powerplatform.com:443/powerautomate/automations/direct/cu/20/workflows/4d841d0ea31c42069815cbc8825f8772/triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=cS8aqbT_i151ug54txEagGvZQF0i-OUPu5w1jg2lYNs"

TABLE_STYLE = 'border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; font-size: 13px; text-align: left;"'
TH_STYLE = 'background-color: #000000; color: #EBE600; font-weight: bold; text-align: center;'

def prepare_data():
    # ==========================================
    # 1. CALCULATE PENDING REPORT DAYS
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
    # 2. FILTER SHORTAGE ALERTS (Gap > 0)
    # ==========================================
    df_power_tool = get_processed_power_tool_data() 
    
    if not df_power_tool.empty and "is_suspended" in df_power_tool.columns:
        df_power_tool["is_suspended"] = df_power_tool["is_suspended"].fillna(False).astype(bool)
        df_power_tool = df_power_tool[df_power_tool["is_suspended"] == False].copy()

    df_shortage = pd.DataFrame()
    
    if not df_power_tool.empty and "Gap" in df_power_tool.columns:
        df_shortage = df_power_tool[df_power_tool["Gap"] > 0].sort_values(by="Gap", ascending=False)
        if not df_shortage.empty:
            cols_to_show = ["ORT model", "Model name", "P.I.C", "Gap", "Action required"]
            cols_exist = [col for col in cols_to_show if col in df_shortage.columns]
            df_shortage = df_shortage[cols_exist].reset_index(drop=True)
            df_shortage.insert(0, 'No.', range(1, len(df_shortage) + 1)) 

    # ==========================================
    # 3. FILTER ACTIVE REQUESTS (!= "closed")
    # ==========================================
    df_st = get_st_requests()
    df_active = pd.DataFrame()
    
    if not df_st.empty and "req_status" in df_st.columns:
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
            df_active.insert(0, 'No.', range(1, len(df_active) + 1)) 

    df_shortage.columns.name = None
    df_active.columns.name = None
    
    return df_shortage, df_active, pending_days_b

def send_automated_report():
    print("Compiling data for email report...")
    df_shortage, df_active, pending_days_b = prepare_data()
    
    if not df_shortage.empty:
        html_shortage = df_shortage.to_html(index=False, classes='qm-table', border=0)
    else:
        html_shortage = "<p style='color: green;'>✅ Great! The system currently records no models with sample shortages.</p>"
        
    if not df_active.empty:
        html_active = df_active.to_html(index=False, classes='qm-table', border=0)
    else:
        html_active = "<p style='color: green;'>✅ No pending requests at the moment.</p>"

    # ==========================================
    # CẬP NHẬT: TÁCH @TAG RIÊNG CHO TỪNG BỘ PHẬN
    # ==========================================
    config = get_email_config("vn_ort_daily")
    to_report_dynamic = config.get("to_report_emails", "") if config else ""
    to_team_dynamic = config.get("to_emails", "") if config else ""
    cc_email_dynamic = config.get("cc_emails", "") if config else ""

    def generate_dynamic_tags(email_string):
        if not email_string:
            return "Team"
        emails = [e.strip() for e in email_string.split(";") if e.strip()]
        tags = []
        for e in emails:
            raw_name = e.split('@')[0]
            display_name = raw_name.replace('.', ' ').title()
            tags.append(f'<a href="mailto:{e}" style="color: #2458A2; font-weight: bold; text-decoration: none;">@{display_name}</a>')
        return ", ".join(tags)

    tag_report = generate_dynamic_tags(to_report_dynamic)
    tag_team = generate_dynamic_tags(to_team_dynamic)
    combined_to_emails = f"{to_report_dynamic};{to_team_dynamic}".strip(";")

    # Build HTML Body
    email_body = f"""
    <div style="font-family: Arial, sans-serif; color: #333; max-width: 900px; margin: auto;">
        <h2 style="color: #000000; background-color: #EBE600; padding: 12px; text-align: center; margin-bottom: 30px;">
            ⚠️ VN ORT DAILY ALERT [{datetime.now().strftime('%b %d, %Y')}]
        </h2>
        
        <!-- MODULE REPORT QTY -->
        <div style="margin-bottom: 30px;">
            <p style="font-size: 15px;"><strong>Dear {tag_report},</strong></p>
            <p>The system detected missing Production Report Qty for <span style="font-size: 20px; color: red; font-weight: bold;">{pending_days_b}</span> working days.</p>
            <p><i>Please access the VNORTS system to update the missing data and ensure progress tracking.</i></p>
        </div>
        
        <hr style="border: 1px solid #ddd; margin: 25px 0;">
        
        <!-- MODULE SHORTAGE & REQUESTS -->
        <div style="margin-bottom: 30px;">
            <p style="font-size: 15px;"><strong>Dear {tag_team},</strong></p>
            <p>There are currently <span style="color: red; font-weight: bold; font-size: 20px;">{len(df_shortage)}</span> models with <b>SAMPLE SHORTAGES</b> (Gap > 0):</p>
            {html_shortage}
            
            <br>
            <p>List of <b>ACTIVE REQUESTS</b> (Not Closed):</p>
            {html_active}
        </div>
        
        <!-- FOOTER: CHỮ KÝ & AUTO EMAIL DISCLAIMER -->
        <div style="margin-top: 40px; font-size: 14px; color: #333;">
            <p>Best regards,<br>
            <span style="font-size: 16px;"><strong>MQA Automated System</strong></span><br>
            Techtronic Industries</p>
            
            <hr style="border: 0; border-top: 1px solid #eeeeee; margin: 20px 0 10px 0;">
            <p style="font-size: 12px; color: #888888; font-style: italic; margin-top: 0;">
                Please note: This is an automated email. Replies to this address are not monitored. If you have any inquiries, please contact the MQA team directly.
            </p>
        </div>
    </div>
    """
    
    email_body = email_body.replace('<tr style="text-align: right;">', '<tr>')
    email_body = re.sub(
        r'<table[^>]*>', 
        '<table width="100%" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%; min-width: 100%; border: 1px solid #bbbbbb; font-family: Arial, sans-serif; font-size: 13px; text-align: left;">', 
        email_body
    )
    email_body = re.sub(
        r'<td(.*?)>', 
        r'<td\1 style="border: 1px solid #dddddd; padding: 8px; text-align: center;">', 
        email_body
    )
    email_body = re.sub(
        r'<th(.*?)>', 
        r'<th\1 style="border: 1px solid #aaaaaa; padding: 10px; background-color: #000000; color: #EBE600; font-weight: bold; text-align: center;">', 
        email_body
    )
    
    payload = {
        "to_email": combined_to_emails, 
        "cc_email": cc_email_dynamic,
        "content": email_body,
        "task_key": "vn_ort_daily"
    }
    
    print(f"Sending email to TO: {combined_to_emails} | CC: {cc_email_dynamic}")
    response = requests.post(WEBHOOK_URL, json=payload)
    
    if response.status_code == 202:
        print("✅ Report sent successfully!")
    else:
        print(f"❌ Error sending email: {response.status_code} - {response.text}")

if __name__ == "__main__":
    send_automated_report()