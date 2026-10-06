import streamlit as st
import time

# IMPORT HÀM TỪ FILE CỦA BẠN (Cần trỏ đúng đường dẫn)
from auto_email_job import send_automated_report 

# BỔ SUNG: Import các hàm thao tác với Supabase
from database.db_helper import (
    kiem_tra_da_gui, 
    ghi_nhan_gui_thanh_cong,
    get_email_config,
    update_email_config
)

def render(df_power_tool=None):
    # ================= 1. TIÊU ĐỀ TRANG =================
    st.markdown("""
<style>
.module-header-wrapper {
    filter: drop-shadow(4px 4px 0px rgba(0, 0, 0, 0.2));
    margin-bottom: 25px;
    margin-top: 30px;
}

.module-header {
    background-color: #EBE600;
    color: #000000;
    padding: 15px 25px;
    font-size: 35px;
    font-weight: 800;
    clip-path: polygon(25px 0, 100% 0, 100% calc(100% - 25px), calc(100% - 25px) 100%, 0 100%, 0 25px); 
    text-transform: uppercase;
}
</style>
<div class="module-header-wrapper">
    <div class="module-header">
    <h2 style='text-align: center; color: #000000; background-color: #EBE600; padding: 10px;'>
            📧 EMAIL CENTER
</h2></div>
</div>
""", unsafe_allow_html=True)

    st.markdown("Manage configurations and manually trigger automated daily reports.")
    st.divider()

    # Lấy thông tin user hiện tại để ghi log
    user_info = st.session_state.get("user_info", {})
    user_role = user_info.get("role", "viewer")
    username = user_info.get("username", "Admin_Web")

    # Kiểm tra phân quyền: Chỉ Admin mới được dùng chức năng này
    if user_role != "admin":
        st.error("🚨 You do not have permission to access this area.")
        st.stop()

    # ========================================================
    # 2. TRIGGER REPORTS (NÚT BẤM GỬI MAIL)
    # ========================================================
    st.subheader("🚀 Manual Trigger")
    
    task_key_trigger = "vn_ort_daily"
    da_gui_hom_nay = kiem_tra_da_gui(task_key_trigger)

    col_task, col_status, col_action = st.columns([5, 2, 2])
    
    with col_task:
        st.markdown("**📌 Task Name**")
        st.markdown("1. VN ORT Daily Report")
        
    with col_status:
        st.markdown("**Today's Status**")
        mqa_status = "✅ Sent" if da_gui_hom_nay else "❌ Pending"
        st.markdown(mqa_status)

    with col_action:
        st.markdown("**Action**")
        
        if da_gui_hom_nay:
            st.success("Completed")
            
            if st.checkbox("🔧 Unlock Resend"):
                if st.button("🚀 Resend Now", key="btn_resend"):
                    with st.spinner("Triggering Power Automate flow..."):
                        try:
                            send_automated_report()
                            ghi_nhan_gui_thanh_cong(task_key_trigger, sent_by=f"{username} (Resend)")
                            st.success("Resent successfully!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
        else:
            if st.button("🚀 Send Now", key="btn_send_vn_ort"):
                with st.spinner("Compiling data and triggering flow..."):
                    try:
                        send_automated_report() 
                        ghi_nhan_gui_thanh_cong(task_key_trigger, sent_by=username)
                        
                        st.success(f"Automated email triggered successfully by {username}!")
                        time.sleep(1) 
                        st.rerun() 
                    except Exception as e:
                        st.error(f"System error when triggering email: {e}")

    # ========================================================
    # 3. EMAIL AUTOMATION SETUP (CẤU HÌNH NGƯỜI NHẬN)
    # ========================================================
    st.divider()
    st.subheader("⚙️ Automated Report Setup")
    st.info("💡 **Rule:** Configure the dynamic recipient lists (TO and CC) for automated webhooks. Use semicolons (;) to separate multiple emails.")

    # Dictionary phân loại các báo cáo đang có
    task_dict = {
        "vn_ort_daily": "VN ORT Daily Report",
        "weekly_report": "MQA Weekly Report"
    }
    
    selected_task_name = st.selectbox("📌 Select process to configure:", list(task_dict.values()))
    
    # Tìm task_key tương ứng với lựa chọn
    selected_task_key = [k for k, v in task_dict.items() if v == selected_task_name][0]

    # Kéo cấu hình từ Database
    config = get_email_config(selected_task_key)

    if config is not None:
        with st.form(f"form_config_email_{selected_task_key}"):
            # TÁCH LÀM 2 Ô TO RIÊNG BIỆT
            to_report = st.text_input("TO (Report P.I.C) - Nhắc nhở nhập liệu:", value=config.get("to_report_emails", ""))
            to_team = st.text_input("TO (Team P.I.C) - Nhắc nhở thiếu mẫu:", value=config.get("to_emails", ""))
            cc_emails = st.text_input("Carbon Copy (CC):", value=config.get("cc_emails", ""))
            
            submit_btn = st.form_submit_button("💾 Save Email Config", type="primary")
            
            if submit_btn:
                clean_report = ";".join([email.strip() for email in to_report.split(";") if email.strip()])
                clean_team = ";".join([email.strip() for email in to_team.split(";") if email.strip()])
                clean_cc = ";".join([email.strip() for email in cc_emails.split(";") if email.strip()])
                
                # Gọi hàm mới với 3 tham số TO
                success = update_email_config(selected_task_key, clean_report, clean_team, clean_cc)
                if success:
                    st.success(f"✅ Successfully updated email configuration for {selected_task_name}!")
                    time.sleep(1)
                    st.rerun() 
                else:
                    st.error("❌ Error saving to Database.")
    else:
        st.warning(f"⚠ Configuration for '{selected_task_name}' not found in Database. Please run SQL INSERT first.")