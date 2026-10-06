import streamlit as st
import os

def load_custom_css():
    """Đọc file CSS từ thư mục assets và tiêm trực tiếp vào Streamlit"""
    css_path = os.path.join("assets", "style.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
            # Đưa logo vào top của sidebar (tự động chuyển đổi dạng full và icon khi thu gọn)
    else:
        st.warning("⚠️ Không tìm thấy file style.css trong thư mục assets!")

def load_sidebar_logo():
    """Tự động nạp logo cho sidebar (Hỗ trợ cả dạng full và icon thu gọn)"""
    full_logo = "assets/logo_full.png"
    icon_logo = "assets/logo_icon.png"
    
    
    # Kiểm tra xem file có tồn tại không trước khi gọi st.logo để tránh lỗi
    if os.path.exists(full_logo) and os.path.exists(icon_logo):
        st.logo(
            image=full_logo,
            icon_image=icon_logo
        )
    elif os.path.exists(full_logo):
        st.logo(image=full_logo)
