import streamlit as st
import pandas as pd
from database.db_helper import authenticate_user, get_processed_power_tool_data
from database.ui_helper import load_custom_css, load_sidebar_logo
from datetime import datetime, time

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
    # Các trang khác bạn có thể thêm dần...
except ImportError as e:
    st.error(f"Lỗi load module giao diện: {e}")
    st.stop()

st.set_page_config(
    page_title="ORT System",
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

# ================= 3. MÀN HÌNH ĐĂNG NHẬP =================
def show_login_screen():
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center;'>🔐 System Authentication</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Please log in to access the ORT System.</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In", type="primary", use_container_width=True)
            
            if submit:
                user = authenticate_user(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_info = user
                    st.success(f"✅ Welcome back, {user.get('full_name', username)}!")
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password. Please try again.")

        st.markdown("<p style='text-align: center; color: gray;'>🔥 Continuous Improvement • Since 2026 🔥.</p>", unsafe_allow_html=True)
        
        st.markdown("""
        <style>
        /* 1. KHỐI FOOTER ẨN (Giữ nguyên như cũ) */
        .secret-footer {
            opacity: 0;
            transition: opacity 0.4s ease-in-out;
            text-align: center;
            color: gray;
            padding-top: 100px;
        }
        .secret-footer:hover {
            opacity: 1;
        }
        
        /* Chuyển emoji thành link bấm mượt mà */
        .secret-footer a.mail-icon {
            text-decoration: none;
            cursor: pointer;
            font-size: 20px;
            margin-left: 8px;
        }

        /* 2. KHUNG NỀN TỐI CỦA POPUP (Mặc định ẩn) */
        .modal-window {
            position: fixed;
            background-color: rgba(0, 0, 0, 0.75);
            top: 0; right: 0; bottom: 0; left: 0;
            z-index: 99999;
            visibility: hidden;
            opacity: 0;
            transition: all 0.3s;
        }

        /* KÍCH HOẠT HIỆN POPUP KHI CLICK VÀO EMOJI */
        .modal-window:target {
            visibility: visible;
            opacity: 1;
        }

        /* 3. HỘP THOẠI CHỨA NỘI DUNG THƯ */
        .modal-content {
            width: 450px;
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            padding: 2em;
            background: #1a1a1a; /* Tone nền tối công nghiệp */
            border: 1px solid #333;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.8);
            text-align: left;
        }

        /* Nút tắt Popup (dấu X) */
        .modal-close {
            color: #aaa;
            position: absolute;
            right: 15px;
            top: 15px;
            text-decoration: none;
            font-size: 18px;
            font-weight: bold;
        }
        .modal-close:hover {
            color: #EBE600; /* Vàng thương hiệu */
        }
        </style>
        
        <!-- HIỂN THỊ DÒNG CHỮ VÀ EMOJI -->
        <div class="secret-footer">
            <p style="margin-top: 0px;"> 🎓 Richard's Legacy 🎓 </p>
            <a href="#secret-mqa-letter" class="mail-icon" title="Đọc thư">📬</a>
        </div>

        <!-- CẤU TRÚC POPUP CHỨA LÁ THƯ -->
        <div id="secret-mqa-letter" class="modal-window">
            <div class="modal-content">
                <a href="#" title="Đóng" class="modal-close">✖</a>
                <h3 style="margin-top: 0; color: #EBE600;">A Letter to My Successor</h3>
                <div style="font-size: 15px; line-height: 1.6; color: #dddddd;">
                    <p>Dear My Successor,</p>
                    <p>
                        This system is the result of four years of experience, failures, lessons learned, and continuous improvement. It was built to solve real problems, not just to manage data.
                        I hope you will take it further than I ever could. Maintain it, improve it, and never stop looking for better ways to support the team.
                        We are not always visible, but our work matters.</p>
                    <p>Stay curious. Keep improving. Be a hidden hero,<br><b>Quality Driven • Since 2026</b></p>
                    <p> Nếu bạn đang đọc những dòng này, có lẽ hành trình của tôi tại TTi đã khép lại.
                        Hệ thống này được tạo nên từ bốn năm trải nghiệm thực tế, từ những thành công, thất bại, sai lầm và bài học quý giá trong suốt thời gian tôi phụ trách công việc này. Mỗi chức năng và mỗi cải tiến đều được xây dựng để giải quyết những vấn đề mà chúng ta thực sự gặp phải hằng ngày.
                        Tôi hy vọng bạn sẽ tiếp tục gìn giữ và phát triển nó, biến nó trở nên tốt hơn từng ngày. Đừng ngần ngại thay đổi, cải tiến và tạo ra những giá trị mới cho đội ngũ.
                        Có thể chúng ta luôn ở phía sau ánh đèn sân khấu, nhưng những gì chúng ta làm đều để lại dấu ấn.
                        Hãy luôn học hỏi. Không ngừng cải tiến. Và tiếp tục là những người hùng thầm lặng.</p>
                    <p>Hãy luôn học hỏi. Không ngừng cải tiến. Và tiếp tục là những người hùng thầm lặng,<br><b>Quality Driven • Since 2026</b></p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

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

def update_ort_menu():
    st.session_state.active_page = st.session_state.ort_menu_radio

def update_mqa_menu():
    st.session_state.active_page = st.session_state.mqa_menu_radio

with st.sidebar:
    # ================= MAIN MENU (CHIA SECTION) =================
    # Phân loại danh sách trang theo Role và Section
    if user_role == "admin":
        ort_pages = ["📊 Dashboard", "🛠️ Power Tools", "🔋 Batteries", "📄 Report Qty", "🧪 S & T", "📧 Email Center", "⚙️ Setting"]
        mqa_pages = ["📝 RI", "🎯 Action Tracker"]
    elif user_role == "user":
        ort_pages = ["📊 Dashboard", "🛠️ Power Tools", "🔋 Batteries", "📄 Report Qty", "🧪 S & T"]
        mqa_pages = []
    else:
        ort_pages = ["📊 Dashboard"]
        mqa_pages = []

    # --- KHU VỰC 1: ORT SECTION ---
    st.markdown("<p style='font-weight: 800; color: white; margin-bottom: 5px; font-size: 10px;'>ORT SECTION</p>", unsafe_allow_html=True)
    ort_idx = ort_pages.index(st.session_state.active_page) if st.session_state.active_page in ort_pages else None
    
    st.radio(
        "ORT_HIDDEN", 
        ort_pages, 
        index=ort_idx, 
        key="ort_menu_radio", 
        on_change=update_ort_menu, 
        label_visibility="collapsed"
    )

    # --- KHU VỰC 2: MQA SECTION ---
    if mqa_pages: # Chỉ hiển thị khu vực này nếu người dùng có quyền (có trang trong danh sách)
        st.markdown("<p style='font-weight: 800; color: white; margin-bottom: 5px; margin-top: 15px; font-size: 10px;'>MQA SECTION</p>", unsafe_allow_html=True)
        mqa_idx = mqa_pages.index(st.session_state.active_page) if st.session_state.active_page in mqa_pages else None
        
        st.radio(
            "MQA_HIDDEN", 
            mqa_pages, 
            index=mqa_idx, 
            key="mqa_menu_radio", 
            on_change=update_mqa_menu, 
            label_visibility="collapsed"
        )

    # Chốt lại biến selected_page để truyền xuống các tính năng bên dưới (Khóa app, render trang)
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
        
        if st.button("Sign Out", use_container_width=True, key="sidebar_sign_out"):
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
        if selected_page != "📧 Email Center":
            st.error("🚨 **HỆ THỐNG ĐÃ BỊ KHÓA TẠM THỜI!**")
            st.warning("Bạn chưa gửi báo cáo **VN ORT daily alert** sáng nay. Vui lòng chọn mục **📧 Email Center** ở thanh Menu bên trái để thực hiện tác vụ và mở khóa hệ thống.")
            st.stop() # Chặn đứng mọi xử lý bên dưới

# ================= 6. KHÔNG GIAN LÀM VIỆC CHÍNH (MAIN AREA) =================
if selected_page == "📊 Dashboard":
    dashboard_page.render(df_power_tool)
elif selected_page == "🛠️ Power Tools":
    power_tool_page.render(df_power_tool)
elif selected_page == "🔋 Batteries":
    battery_page.render(df_power_tool)
elif selected_page == "📄 Report Qty":
    report_page.render(df_power_tool)
elif selected_page == "🧪 S & T":
    st_page.render(df_power_tool)
elif selected_page == "⚙️ Setting":
    settings_page.render(df_power_tool)
elif selected_page == "📧 Email Center":
    email_page.render(df_power_tool)
elif selected_page == "🎯 Action Tracker":  # Thêm luồng này
    action_tracker_page.render(df_power_tool)
elif selected_page == "📝 RI":    # Thêm luồng này
    mqa_record_page.render(df_power_tool)
else:
    st.info(f"Bạn đang chọn {selected_page} - Đang chờ kết nối module.")