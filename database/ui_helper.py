import streamlit as st
import os
import time
import base64
from database.db_helper import get_report_qty
import pandas as pd
from datetime import date, timedelta

def set_goku_background():
    # Đảm bảo đường dẫn này trỏ đúng vào file ảnh Goku của bạn
    bg_path = "assets/bg_goku_1.jpeg" 
    
    if os.path.exists(bg_path):
        with open(bg_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            
        st.markdown(f"""
        <style>
        /* 1. ÉP HÌNH NỀN GOKU CHO TOÀN TRANG */
        .stApp {{
            background-image: url("data:image/jpeg;base64,{encoded_string}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            background-repeat: no-repeat;
        }}
        
        /* 2. LÀM MỜ KHUNG NỘI DUNG CHÍNH ĐỂ DỄ ĐỌC CHỮ VÀ BẢNG */
        .block-container {{
            background-color: rgba(255, 255, 255, 0.85) !important; /* Trắng mờ 85% */
            padding: 2rem 3rem !important;
            margin-top: 0rem;
            box-shadow: 0px 10px 30px rgba(0,0,0,0.5);
        }}
        </style>
        """, unsafe_allow_html=True)
    else:
        st.warning("⚠️ Không tìm thấy hình nền Goku tại assets/bg_goku.jpeg")

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

# =====================================================================
# KHU VỰC CÁC HÀM UI DÙNG CHUNG (GLOBAL COMPONENTS)
# =====================================================================

def show_loader(sub_text="Synchronizing modules"):
    """
    Hàm gọi màn hình Loading toàn trang.
    Có thể truyền sub_text tùy ý để đổi câu chú thích bên dưới chữ LOADING DATA.
    """
    run_id = str(time.time()).replace(".", "")

    st.markdown(f"""
    <style>
    [data-testid="stHeader"] {{ z-index: 99999999 !important; }}
    [data-testid="stSidebar"] {{ z-index: 99999999 !important; }}
    div[data-testid="stMainBlockContainer"] {{ position: relative !important; }}
    
    .loader-bg-{run_id} {{
        position: absolute;
        top: -150px; left: -100px; right: -100px; bottom: -200px;
        height: max(150vh, 100%); 
        background-color: #ffffff; 
        z-index: 99999998 !important; 
    }}
    
    .spinner-container-{run_id} {{
        position: sticky;
        top: 40vh; 
        display: flex;
        flex-direction: column;
        justify-content: center; 
        align-items: center;
    }}
    
    .spinner-wrapper-{run_id} {{
        position: relative;
        width: 80px; height: 80px;
        margin-bottom: 20px;
    }}
    
    .spinner-circle-{run_id} {{
        box-sizing: border-box;
        border: 8px solid #f3f3f3;
        border-top: 8px solid #EBE600; 
        border-bottom: 8px solid #000000;
        border-radius: 50%;
        width: 100%; height: 100%;
        animation: spin-{run_id} 1s linear infinite;
    }}
    
    .percentage-{run_id} {{
        position: absolute;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        font-weight: 900;
        font-size: 15px;
        color: #000000;
    }}
    
    .percentage-{run_id}::after {{
        content: "0%";
        animation: countUp-{run_id} 1.2s ease-out forwards;
    }}
    
    .wavy-text-{run_id} {{
        margin: 0;
        font-weight: 900;
        display: flex;
        gap: 2px;
    }}
    
    .wavy-text-{run_id} span {{
        display: inline-block;
        color: #000000;
        font-size: 24px;
        text-transform: uppercase;
        animation: waveFlash-{run_id} 1.5s infinite;
        animation-delay: calc(0.1s * var(--i));
        will-change: transform, color;
        transform: translateZ(0);
    }}
    
    @keyframes spin-{run_id} {{ 
        0% {{ transform: rotate(0deg); }} 
        100% {{ transform: rotate(360deg); }} 
    }}
    
    @keyframes countUp-{run_id} {{
        0% {{ content: "0%"; }}
        15% {{ content: "23%"; }}
        30% {{ content: "48%"; }}
        45% {{ content: "67%"; }}
        60% {{ content: "82%"; }}
        75% {{ content: "94%"; }}
        100% {{ content: "99%"; }}
    }}
    
    @keyframes waveFlash-{run_id} {{
        0%, 40%, 100% {{
            transform: translate3d(0, 0, 0);
            color: #000000;
        }}
        20% {{
            transform: translate3d(0, -8px, 0);
            color: #EBE600;
        }}
    }}
    </style>
    
    <div class="loader-bg-{run_id}" id="loader-box-{run_id}">
    <div class="spinner-container-{run_id}">
    <div class="spinner-wrapper-{run_id}">
    <div class="spinner-circle-{run_id}"></div>
    <div class="percentage-{run_id}"></div>
    </div>
    <div class="wavy-text-{run_id}">
    <span style="--i:1">L</span>
    <span style="--i:2">O</span>
    <span style="--i:3">A</span>
    <span style="--i:4">D</span>
    <span style="--i:5">I</span>
    <span style="--i:6">N</span>
    <span style="--i:7">G</span>
    <span style="--i:8; width: 8px;"></span>
    <span style="--i:9">D</span>
    <span style="--i:10">A</span>
    <span style="--i:11">T</span>
    <span style="--i:12">A</span>
    <span style="--i:13">.</span>
    <span style="--i:14">.</span>
    <span style="--i:15">.</span>
    </div>
    <p style="color: #666666; font-size: 14px; margin-top: 5px;">{sub_text}</p>
    </div>
    </div>
    """, unsafe_allow_html=True)
    
    return run_id


def hide_loader(run_id, delay_seconds=1.2):
    """
    Hàm ẩn màn hình Loading sau khi đã xử lý xong dữ liệu.
    """
    st.markdown(f"""
    <style>
    @keyframes fadeOut-{run_id} {{
        0% {{ opacity: 1; visibility: visible; }}
        99% {{ opacity: 0; visibility: hidden; }}
        100% {{ opacity: 0; visibility: hidden; display: none; z-index: -1; }}
    }}
    
    #loader-box-{run_id} {{
        animation: fadeOut-{run_id} 0.3s ease {delay_seconds}s forwards !important; 
        pointer-events: none; 
    }}
    </style>
    """, unsafe_allow_html=True)

def render_global_marquee():
    """Hàm render thanh chữ chạy cảnh báo toàn cục cho mọi module"""
    today = date.today()
    yesterday = today - timedelta(days=1)
    missing_dates = []
    
    # 1. LOGIC KIỂM TRA DỮ LIỆU
    try:
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
            else:
                missing_dates.append(yesterday.strftime("%b %d %Y (Chưa có dữ liệu)"))
        else:
            missing_dates.append(yesterday.strftime("%b %d %Y (Database trống)"))
            
    except Exception as e:
        st.error(f"Lỗi quét ngày ở Marquee: {e}")

    # 2. XÁC ĐỊNH TRẠNG THÁI HIỂN THỊ
    if missing_dates:
        # TRẠNG THÁI 1: CÓ LỖI (MÀU ĐỎ/VÀNG)
        dates_str = ", ".join(missing_dates)
        marquee_msg = f"📢 MISSING Report Qty dates: [ {dates_str} ]"
        bg_color = "#EBE600"
        border_color = "#EBE600"
        text_color = "#cc0000"
        shadow_color = "rgba(0, 0, 0, 0.15)"
    else:
        # TRẠNG THÁI 2: ỔN ĐỊNH (MÀU XANH LÁ)
        marquee_msg = "✅ DATA UP TO DATE! Have a great and productive workday. ✅"
        bg_color = "#e8f5e9"
        border_color = "#4caf50" 
        text_color = "#2e7d32"
        shadow_color = "rgba(76, 175, 80, 0.2)"

    # 3. HIỂN THỊ UI BẰNG STREAMLIT
    st.markdown(f"""
<style>
/* KHUNG CHỨA TỔNG THỂ (Cần position: relative để neo khối đen) */
.marquee-container {{
    position: relative;
    width: 100%;
    margin-bottom: 15px;
    box-shadow: 4px 4px 0px {shadow_color};
    border-radius: 4px;
    overflow: hidden;
    border: 2px solid {border_color};
    background-color: {bg_color};
    display: flex;
    align-items: center;
}}

/* KHỐI ĐEN CỐ ĐỊNH (Neo cứng bên trái, che kín mép vàng và nằm đè lên trên) */
.marquee-label {{
    position: absolute;
    left: -2px; /* Dùng lề âm để ép khối đen lấp luôn cái viền vàng 2px */
    top: 0;
    height: 100%;
    background-color: #000000;
    color: #ffffff;
    font-weight: 900;
    font-size: 16px;
    padding: 0 20px; /* Tăng padding để chữ không bị kẹp sát lề */
    text-transform: uppercase;
    display: flex;
    align-items: center;
    justify-content: center;
    white-space: nowrap;
    z-index: 10; 
}}

/* KHỐI CHỮ CHẠY (Trải dài 100% khung để chữ trượt xuyên qua khối đen) */
.global-marquee-wrapper {{
    width: 100%;
    padding: 10px;
    overflow: hidden;
    white-space: nowrap;
    display: flex;
    align-items: center;
}}

.global-marquee-text {{
    display: inline-block;
    color: {text_color};
    font-weight: 900;
    font-size: 15px;
    text-transform: uppercase;
    animation: scroll-left-global 25s linear infinite; 
    padding-left: 100%; 
}}

/* Dừng chữ khi hover vào bất kỳ đâu trong thanh */
.marquee-container:hover .global-marquee-text {{
    animation-play-state: paused;
    cursor: pointer;
}}

@keyframes scroll-left-global {{
    0% {{ transform: translate(0, 0); }}
    100% {{ transform: translate(-100%, 0); }}
}}
</style>

<div class="marquee-container" title="System Status Notification">
<div class="marquee-label">ORT news:</div>
<div class="global-marquee-wrapper">
<div class="global-marquee-text">{marquee_msg}</div>
</div>
</div>
    """, unsafe_allow_html=True)

