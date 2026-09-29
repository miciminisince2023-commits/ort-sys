import streamlit as st
import time

# IMPORT HÀM TỪ FILE CỦA BẠN (Cần trỏ đúng đường dẫn)
# Giả sử file auto_email_job.py của bạn đang nằm ở thư mục gốc (cùng cấp với app.py)
from auto_email_job import send_automated_report 

def render(df_power_tool=None):
    st.markdown("## 📧 TRUNG TÂM ĐIỀU HÀNH EMAIL")
    st.markdown("Quản lý và kích hoạt các báo cáo tự động trong ngày.")
    st.divider()

    # Kiểm tra phân quyền: Chỉ Admin mới được dùng chức năng này
    user_role = st.session_state.user_info.get("role", "viewer")
    if user_role != "admin":
        st.error("🚨 Bạn không có quyền truy cập vào khu vực này.")
        st.stop()

    # Cấu trúc bảng điều khiển các luồng Email
    col_task, col_status, col_action = st.columns([5, 2, 2])
    
    with col_task:
        st.markdown("**📌 Tên báo cáo (Task Name)**")
        st.markdown("1. VN ORT daily alert")
        
    with col_status:
        st.markdown("**Trạng thái hôm nay**")
        # Trạng thái sẽ liên kết với biến mqa_sent_today mà Sidebar đang dùng
        mqa_status = "✅ Đã gửi" if st.session_state.get("mqa_sent_today") else "❌ Chưa gửi"
        st.markdown(mqa_status)

    with col_action:
        st.markdown("**Hành động**")
        
        # Nút bấm kích hoạt gửi mail
        if st.button("🚀 Gửi ngay", key="btn_send_vn_ort"):
            with st.spinner("Đang tổng hợp dữ liệu và kích hoạt luồng Power Automate..."):
                try:
                    # GỌI HÀM THỰC THI GỬI EMAIL
                    # Lưu ý: Cần điều chỉnh import ở trên cùng nếu file auto_email_job.py nằm trong folder khác
                    send_automated_report() 
                    
                    # Xác nhận thành công và cập nhật trạng thái hệ thống
                    st.session_state["mqa_sent_today"] = True
                    st.success("Đã kích hoạt gửi mail qua luồng tự động thành công!")
                    time.sleep(1) # Dừng 1 giây để người dùng đọc thông báo trước khi làm mới giao diện
                    st.rerun() # Tải lại trang để cập nhật chữ "✅ Đã gửi" và mở khóa Dashboard
                except Exception as e:
                    st.error(f"Lỗi hệ thống khi kích hoạt email: {e}")