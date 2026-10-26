import streamlit as st
import pandas as pd
from database.db_helper import authenticate_user, get_processed_power_tool_data
from database.ui_helper import load_custom_css, load_sidebar_logo, show_loader, hide_loader, set_goku_background
from datetime import datetime, time
import os
import base64

# ================= 1. IMPORT CÁC TRANG (THEO DẠNG HÀM) =================
# Đây là sự thay đổi quan trọng nhất. Thay vì st.Page, ta import như một thư viện nội bộ
# Giả định bạn đã bọc code trong các file pages/ thành hàm render(df_power_tool)
import importlib
try:
    # Sửa "pages..." thành "views..."
    dashboard_page = importlib.import_module("views.0_Dashboard")
    power_tool_page = importlib.import_module("views.1_M_&_M_Power_Tool")
    battery_page = importlib.import_module("views.2_M_&_M_Battery")
    report_page = importlib.import_module("views.3_Report_Qty")
    st_page = importlib.import_module("views.4_S_&_T")
    settings_page = importlib.import_module("views.5_Setting")
    email_page = importlib.import_module("views.6_Email_Center") # Thêm dòng này
    mqa_record_page = importlib.import_module("views.7_MQA_Record_Issue")
    action_tracker_page = importlib.import_module("views.8_Action_Tracker")
    handbook_page = importlib.import_module("views.9_Handbook")
    # Các trang khác bạn có thể thêm dần...
except ImportError as e:
    st.error(f"Lỗi load module giao diện: {e}")
    st.stop()

st.set_page_config(
    page_title="TIS",
    page_icon="assets/logo_icon.png",
    layout="wide"
)

def load_css(file_name):
    """Đọc và nạp file CSS tĩnh vào Streamlit"""
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"Không tìm thấy file CSS: {file_name}")

load_css("assets/style.css")
load_custom_css()

# ================= 2. QUẢN LÝ TRẠNG THÁI ĐĂNG NHẬP =================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None

# ================= 3. MÀN HÌNH ĐĂNG NHẬP (ULTRA INSTINCT - KAMEHAMEHA EDITION) =================

def set_login_background():
    # 💡 LƯU Ý NHỎ: Bạn kiểm tra kỹ lại xem tên file là ryobi.jpeg hay ryobi.jpg nhé
    bg_path = "assets/ryobi.jpeg" 
    
    if os.path.exists(bg_path):
        import base64
        with open(bg_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            
        st.markdown(f"""
        <style>
        /* 1. CHIA ĐÔI MÀN HÌNH: NỬA TRÁI LÀ ẢNH, NỬA PHẢI LÀ NỀN TRƠN */
        
        /* Gán màu nền xanh đen cho toàn bộ trang */
        [data-testid="stAppViewContainer"] {{
            background-color: #FFFFFF !important; 
        }}
        
        /* Tạo lớp ảnh ảo chiếm 50% bên trái */
        [data-testid="stAppViewContainer"]::before {{
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 40vw; /* Chiếm chính xác 50% chiều ngang màn hình */
            height: 100vh; /* Chiếm 100% chiều dọc */
            background-image: url("data:image/jpeg;base64,{encoded_string}");
            background-size: cover; /* Không làm méo ảnh */
            background-position: center;
            background-repeat: no-repeat;
            z-index: 0; /* ĐƯA LÊN LỚP 0 ĐỂ KHÔNG BỊ NỀN ĐEN CHE KHUẤT */
            border-right: 2px solid rgba(0, 242, 254, 0.3); 
        }}
        
        /* Đảm bảo Form đăng nhập nổi lên trên cùng */
        .block-container {{
            z-index: 1 !important;
            position: relative;
        }}
        
        /* 2. ẨN SIDEBAR & TOPBAR */
        [data-testid="stHeader"], [data-testid="stSidebar"] {{ 
            display: none !important; 
        }}
        
        /* 3. ĐỊNH DẠNG KHUNG FORM (GLASSMORPHISM) */
        [data-testid="stForm"] {{
            background: #000000 !important; 
            border-radius: 20px !important;
            padding: 40px 30px !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important; 
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.9) !important;
            backdrop-filter: blur(10px) !important; 
            -webkit-backdrop-filter: blur(10px) !important;
            overflow: visible !important; /* Vô cùng quan trọng để tia sáng có thể bắn ra ngoài Form */
        }}
        
        /* Đảm bảo các khung bao ngoài không cắt xén tia sáng */
        [data-testid="stVerticalBlock"], 
        div.element-container {{
            overflow: visible !important;
        }}
        
        /* 4. ÉP MÀU CHỮ THÀNH TRẮNG */
        [data-testid="stForm"] p, 
        [data-testid="stForm"] label,
        [data-testid="stMarkdownContainer"] h2 {{
            color: white !important;
        }}
        
        /* 5. TÙY CHỈNH Ô NHẬP LIỆU (INPUTS) */
        div[data-baseweb="input"] > div {{
            background-color: rgba(255, 255, 255, 0.05) !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-radius: 8px !important;
        }}
        div[data-baseweb="input"] input {{
            color: white !important;
        }}
        div[data-baseweb="input"] > div:focus-within {{
            border-color: #00f2fe !important;
            box-shadow: 0 0 10px rgba(0, 242, 254, 0.5) !important;
            background-color: rgba(255, 255, 255, 0.1) !important;
        }}

        </style>
        """, unsafe_allow_html=True)
    else:
        st.warning("⚠️ Không tìm thấy hình nền Goku tại assets/bg_goku.jpeg")

def show_login_screen():
    set_login_background()
    
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    
    # CHIA CỘT TỶ LỆ 50/50 (Trái 50% - Phải 50%) ĐỂ KHỚP VỚI HÌNH NỀN Ở TRÊN
    col_left, col_right = st.columns([1, 1])
    
    with col_right:
        # Code của form đăng nhập Goku System...
        with st.form("login_form", clear_on_submit=True):
            st.markdown("<h2 style='text-align: center; margin-top: -15px; text-shadow: 0px 4px 10px rgba(0,0,0,0.8);'>THIS IS SYSTEM</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; opacity: 0.8; margin-bottom: 25px;'>Authenticate to unleash power.</p>", unsafe_allow_html=True)
            
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            st.markdown("<br>", unsafe_allow_html=True)
            submit = st.form_submit_button("SIGN IN")
            
            if submit:
                # Import hàm xác thực tại đây
                from database.db_helper import authenticate_user
                user = authenticate_user(username, password)
                
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_info = user if isinstance(user, dict) else {"full_name": username, "role": "admin"}
                    safe_name = st.session_state.user_info.get('full_name', username)
                    st.success(f"🔓 Power Unlocked! Welcome, {safe_name}!")
                    st.rerun() 
                else:
                    st.error("❌ Invalid credentials. The lock holds strong.")
                    
        st.markdown("<p style='text-align: center; color: rgba(255,255,255,0.5); font-size: 12px; margin-top: 15px;'>Hover to charge, Click to fire!</p>", unsafe_allow_html=True)

if not st.session_state.logged_in:
    show_login_screen()
    st.stop()

# ================= 4. KHU VỰC KÉO DỮ LIỆU TẬP TRUNG TẠI APP.PY =================
# Dữ liệu chỉ kéo MỘT LẦN duy nhất khi đăng nhập thành công
with st.spinner("Đang tải dữ liệu tổng từ máy chủ..."):
    df_power_tool = get_processed_power_tool_data()
    # Nếu cần df_st hoặc df_master riêng lẻ, bạn kéo luôn ở đây
    # df_st = get_s_t_data()

# ================= 5. SIDEBAR, ĐIỀU HƯỚNG VÀ PHÂN QUYỀN TRANG (RBAC) =================
user_role = st.session_state.user_info.get("role", "viewer")
user_name = st.session_state.user_info.get("full_name", "User")

load_sidebar_logo()

# --- HÀM ĐỒNG BỘ TRẠNG THÁI MENU CHIA SECTION ---
if "active_page" not in st.session_state:
    st.session_state.active_page = "📊 Dashboard"

# Khởi tạo các giá trị radio vào session_state ngay từ đầu
if "ort_menu_radio" not in st.session_state:
    st.session_state.ort_menu_radio = "📊 Dashboard"
if "mqa_menu_radio" not in st.session_state:
    st.session_state.mqa_menu_radio = None
if "sys_menu_radio" not in st.session_state: 
    st.session_state.sys_menu_radio = None

def sync_sidebar_menus(clicked_section):
    """
    Hàm đồng bộ duy nhất: Quét xem người dùng vừa click vào section nào,
    lấy giá trị đó làm active_page và ép 2 section còn lại về None.
    """
    if clicked_section == "ort" and st.session_state.ort_menu is not None:
        st.session_state.active_page = st.session_state.ort_menu
        st.session_state.mqa_menu = None
        st.session_state.sys_menu = None
        
    elif clicked_section == "mqa" and st.session_state.mqa_menu is not None:
        st.session_state.active_page = st.session_state.mqa_menu
        st.session_state.ort_menu = None
        st.session_state.sys_menu = None
        
    elif clicked_section == "sys" and st.session_state.sys_menu is not None:
        st.session_state.active_page = st.session_state.sys_menu
        st.session_state.ort_menu = None
        st.session_state.mqa_menu = None

with st.sidebar:
    # ================= MAIN MENU (CHIA SECTION) =================
    # Phân loại danh sách trang theo Role và Section
    if user_role == "admin":
        ort_pages = [" Dashboard", " Power Tools", " Batteries", " Report Qty", " S & T"]
        mqa_pages = [" Record Issue", " Action Tracker"]
        sys_pages = [" Handbook", " Email Center", " Setting"]
    elif user_role == "user":
        ort_pages = [" Dashboard", " Power Tools", " Batteries", " Report Qty", " S & T"]
        mqa_pages = []
        sys_pages = []
    else:
        ort_pages = [" Dashboard"]
        mqa_pages = []
        sys_pages = []

    # --- KHU VỰC 1: ORT SECTION ---
    st.markdown("<p style='font-weight: 800; color: white; margin-bottom: 5px; font-size: 10px;'>ORT SECTION</p>", unsafe_allow_html=True)
    st.radio(
        "ORT_HIDDEN", 
        options=ort_pages, 
        key="ort_menu", 
        on_change=sync_sidebar_menus, 
        args=("ort",),           # <--- Truyền tham số để hàm biết đang click ở Section nào
        label_visibility="collapsed", 
        index=None
    )

    # --- KHU VỰC 2: MQA SECTION ---
    if mqa_pages: 
        st.markdown("<p style='font-weight: 800; color: white; margin-bottom: 5px; margin-top: 15px; font-size: 10px;'>MQA SECTION</p>", unsafe_allow_html=True)
        st.radio(
            "MQA_HIDDEN", 
            options=mqa_pages, 
            key="mqa_menu", 
            on_change=sync_sidebar_menus, 
            args=("mqa",),           # <--- Truyền tham số 
            label_visibility="collapsed", 
            index=None
        )

    # --- KHU VỰC 3: SYSTEM SECTION ---
    if sys_pages: 
        st.markdown("<p style='font-weight: 800; color: white; margin-bottom: 5px; margin-top: 15px; font-size: 10px;'>SYSTEM SECTION</p>", unsafe_allow_html=True)
        st.radio(
            "SYS_HIDDEN", 
            options=sys_pages, 
            key="sys_menu", 
            on_change=sync_sidebar_menus, 
            args=("sys",),           # <--- Truyền tham số 
            label_visibility="collapsed", 
            index=None
        )

    # Chốt biến truyền xuống hệ thống dưới
    selected_page = st.session_state.active_page

    st.divider()

    # ================= ACCOUNT (THU PHÓNG) =================
    with st.expander("ACCOUNT", expanded=True):
        st.markdown(
            f"<div style='font-size: 13px; color: #cccccc;'>"
            f"<div style='display: flex; justify-content: space-between; margin-bottom: 8px;'>"
            f"<b>Logged in as:</b>"
            f"<span style='background-color: #2b2b2b; padding: 2px 8px; border-radius: 4px; color: #fff;'>{user_name}</span>"
            f"</div>"
            f"<div style='display: flex; justify-content: space-between; margin-bottom: 15px;'>"
            f"<b>Role:</b>"
            f"<span style='background-color: #2b2b2b; padding: 2px 8px; border-radius: 4px; color: #fff;'>{user_role.upper()}</span>"
            f"</div>"
            f"</div>", 
            unsafe_allow_html=True
        )
        
        if st.button("Sign out", use_container_width=True, key="sidebar_sign_out"):
            st.session_state.logged_in = False
            st.session_state.user_info = None
            st.rerun()

    # ================= CSS TÙY CHỈNH SIDEBAR =================
    st.markdown("""
    <style>
    /* 1. Thu nhỏ cỡ chữ menu list (st.radio) */
    div[data-testid="stRadio"] label p {
        font-size: 14px !important;
    }
    
    /* 2. ĐỔI MÀU ĐEN & in đậm chữ ACCOUNT trên thanh thu phóng */
    div[data-testid="stExpander"] summary p {
        font-size: 15px !important;
        font-weight: 900 !important;
        color: #000000 !important; /* Ép thành màu đen để nổi bật trên nền sáng */
    }
    
    /* 3. KHẮC PHỤC LỖI MẤT VIỀN (Tạo lớp viền ảo bọc ngoài) */
    [data-testid="stSidebar"] div[data-testid="stExpander"] div.stButton {
        background-color: #444444; 
        clip-path: polygon(12px 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%, 0 12px);
        padding: 2px !important; 
        margin-top: 10px;
    }
    
    /* Thiết kế nút Sign Out bên trong */
    [data-testid="stSidebar"] div[data-testid="stExpander"] button {
        clip-path: polygon(11px 0, 100% 0, 100% calc(100% - 11px), calc(100% - 11px) 100%, 0 100%, 0 11px) !important;
        border-radius: 0px !important; 
        font-size: 14px !important;
        font-weight: bold !important;
        background-color: #1e1e1e !important;
        color: #ffffff !important;
        border: none !important; 
        transition: background-color 0.3s ease;
        height: 100%;
        width: 100%;
    }
    
    /* 4. ÉP ĐỔI ĐỒNG LOẠT CẢ NỀN VÀ VIỀN SANG ĐỎ KHI HOVER */
    [data-testid="stSidebar"] div[data-testid="stExpander"] div.stButton:hover button {
        background-color: #cc0000 !important; 
        color: #ffffff !important;
    }

    </style>
    """, unsafe_allow_html=True)

# ================= 5.5. KỶ LUẬT THỜI GIAN (LOCK APP SAU 08:30) =================
if user_role == "admin":
    # 1. Nhúng import local để gọi hàm kiểm tra database
    from database.db_helper import kiem_tra_da_gui
    
    now = datetime.now()
    current_time = now.time()
    deadline_time = time(8, 30, 0) # Mốc 08:30:00 sáng
    
    # 2. KIỂM TRA TRỰC TIẾP TỪ DATABASE (thay vì dùng session_state)
    has_sent_today = kiem_tra_da_gui("vn_ort_daily")
    
    # 3. Kích hoạt khóa
    if current_time > deadline_time and not has_sent_today:
        if selected_page != " Email Center":
            st.error("🚨 **HỆ THỐNG ĐÃ BỊ KHÓA TẠM THỜI!**")
            st.warning("Bạn chưa gửi báo cáo **VN ORT daily alert** sáng nay. Vui lòng chọn mục ** Email Center** ở thanh Menu bên trái để thực hiện tác vụ và mở khóa hệ thống.")
            st.stop() # Chặn đứng mọi xử lý bên dưới

# ================= 6. KHÔNG GIAN LÀM VIỆC CHÍNH (MAIN AREA) =================
if selected_page == " Dashboard":
    dashboard_page.render(df_power_tool)
elif selected_page == " Power Tools":
    power_tool_page.render(df_power_tool)
elif selected_page == " Batteries":
    battery_page.render(df_power_tool)
elif selected_page == " Report Qty":
    report_page.render(df_power_tool)
elif selected_page == " S & T":
    st_page.render(df_power_tool)
elif selected_page == " Setting":
    settings_page.render(df_power_tool)
elif selected_page == " Email Center":
    email_page.render(df_power_tool)
elif selected_page == " Action Tracker":  # Thêm luồng này
    action_tracker_page.render(df_power_tool)
elif selected_page == " Record Issue":    # Thêm luồng này
    mqa_record_page.render(df_power_tool)
elif selected_page == " Handbook":
    handbook_page.render(df_power_tool)
else:
    st.info(f"Bạn đang chọn {selected_page} - Đang chờ kết nối module.")