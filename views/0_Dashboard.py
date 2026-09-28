import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import math 
from datetime import date, timedelta
import plotly.express as px

# 1. Import đúng tên hàm từ db_helper
try:
    from database.db_helper import get_st_requests, get_report_qty
except ImportError:
    pass

def render(df_power_tool):
    # ================= 0. KHU VỰC CẢNH BÁO THIẾU DỮ LIỆU (SMART ALERT) =================
    today = date.today()
    yesterday = today - timedelta(days=1)
    missing_dates = []
    
    try:
        # Ép lấy toàn bộ lịch sử để không bỏ sót bất kỳ mốc nào
        df_recent = get_report_qty(all_time=True) 
        
        if not df_recent.empty and "rec_date" in df_recent.columns:
            # 1. Chuyển đổi toàn bộ sang định dạng ngày tháng
            all_dates = pd.to_datetime(df_recent["rec_date"], errors="coerce").dt.date
            
            # 2. LỌC BỎ TƯƠNG LAI: Chỉ lấy những ngày <= hôm qua
            valid_dates = all_dates[all_dates <= yesterday]
            
            if not valid_dates.empty:
                # 3. Tìm ngày lớn nhất trong tập hợp hợp lệ
                last_report_date = valid_dates.max()
                
                # Nếu mốc cuối cùng vẫn nhỏ hơn hôm qua -> Bắt đầu đếm thiếu
                if last_report_date < yesterday:
                    curr_date = last_report_date + timedelta(days=1)
                    
                    while curr_date <= yesterday:
                        # MẸO: Nếu nhà máy không làm việc Chủ Nhật, hãy BỎ DẤU # ở dòng dưới đây
                        # if curr_date.weekday() != 6: 
                        missing_dates.append(curr_date.strftime("%b %d %Y"))
                        curr_date += timedelta(days=1)
            else:
                # Nếu toàn ngày tương lai (hoặc lỗi parse ngày)
                missing_dates.append(yesterday.strftime("%b %d %Y (Chưa có dữ liệu hợp lệ)"))
        else:
            # Trường hợp database hoàn toàn trống
            missing_dates.append(yesterday.strftime("%b %d %Y (Database trống)"))
            
    except Exception as e:
        # Tạm thời in lỗi ra để bắt bệnh nếu code vẫn sập ngầm
        st.error(f"Lỗi quét ngày: {e}")

    # ĐỊNH NGHĨA MODAL POPUP
    @st.dialog("📣 CẢNH BÁO: QUÊN NHẬP REPORT QTY", width="small")
    def modal_missing_alert(dates):
        st.error("Hệ thống phát hiện chưa có báo cáo sản lượng cho các ngày sau:")
        for d in dates:
            st.markdown(f"- **{d}**")
        st.caption("💡 Vui lòng nhập bổ sung để Dashboard tính toán FG Accum và Gap chính xác nhất.")
        if st.button("Đã hiểu & Đóng", use_container_width=True):
            st.rerun()

    # THIẾT KẾ NÚT RUNG NỔI LÊN TOPBAR (BẢN VÁ LỖI LAYOUT CHUẨN XÁC)
    if missing_dates:

        # 1. Đếm số lượng ngày thiếu (pending items)
        num_missing = len(missing_dates)
        
        # 2. Nhúng biến đếm vào chuỗi text để hiển thị động
        button_text = f"📢Tokuda ({num_missing})"

        # Chèn một "bia ngắm" tàng hình và CSS xử lý ngay trước nút bấm
        st.markdown("""
        <span class="alert-btn-wrapper"></span>
        <style>
        /* 1. Biến khung nội dung chính thành mốc tọa độ trói buộc */
        div[data-testid="block-container"] {
            position: relative;
        }
        
        /* 2. Nhắm vào nút Alert và đẩy ngược lên Topbar */
        div[data-testid="stElementContainer"]:has(.alert-btn-wrapper) + div[data-testid="stElementContainer"] button {
            position: absolute !important; /* CHÌA KHÓA: Dùng absolute thay vì fixed */
            top: -70px !important; /* Đẩy ngược lên khu vực trống của Topbar */
            left: 25px !important; /* Bám sát mép trái của khu vực nội dung chính */
            z-index: 999999 !important;
            animation: ring_phone 1s infinite;
            background-color: #ffcccc !important;
            border: 2px solid #cc0000 !important;
            color: #cc0000 !important;
            border-radius: 20px !important;
            height: 40px !important;
            padding: 0px 15px !important;
            width: auto !important;
            /* 2 THUỘC TÍNH MỚI ĐỂ CHỐNG TRÀN CHỮ DỌC */
            width: max-content !important; 
            white-space: nowrap !important;
        }
        
        @keyframes ring_phone {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 1; transform: scale(1.14); }
            100% { opacity: 1; transform: scale(1); }
        }
        </style>
        """, unsafe_allow_html=True)
        
        # 3. Gắn chuỗi text động vào nút st.button
        alert_clicked = st.button(button_text, help="Click để xem chi tiết các ngày thiếu Report")
    else:
        alert_clicked = False

    # LOGIC TỰ ĐỘNG BẬT POPUP LẦN ĐẦU TIÊN
    if "dashboard_alert_shown" not in st.session_state:
        st.session_state.dashboard_alert_shown = False

    if missing_dates and not st.session_state.dashboard_alert_shown:
        st.session_state.dashboard_alert_shown = True
        modal_missing_alert(missing_dates)

    # BẬT POPUP THỦ CÔNG KHI CLICK ICON
    if alert_clicked and missing_dates:
        modal_missing_alert(missing_dates)

    # ================= 1. CHUẨN BỊ DỮ LIỆU BỔ SUNG =================
    try:
        df_st_raw = get_st_requests()
        
        if not df_st_raw.empty:
            # Đổi tên TOÀN BỘ các cột từ DB cho đẹp mắt
            df_st = df_st_raw.rename(columns={
                "req_id": "Req. id",
                "req_date": "Req. date",
                "tti_model": "TTI model",
                "ort_model": "ORT model",
                "req_qty": "Req. qty",
                "sam_job": "SAM Job",
                "cb_f": "CB/F",
                "scp_f": "SCP/F",
                "dr_f": "DR/F",
                "item_test": "Item Test",
                "start_date": "Start date",
                "end_date": "End date",
                "test_result": "Test result",
                "req_status": "Req. status",
                "req_duration": "Req. duration"
            })
        else:
            # Khai báo khung rỗng đầy đủ cột
            df_st = pd.DataFrame(columns=[
                "Req. id", "Req. date", "TTI model", "ORT model", "Req. qty", 
                "SAM Job", "CB/F", "SCP/F", "DR/F", "Item Test", 
                "Start date", "End date", "Test result", "Req. status", "Req. duration"
            ])
            
    except Exception as e:
        st.error(f"Lỗi hệ thống khi tải dữ liệu S&T: {e}")
        df_st = pd.DataFrame()

    # ================= 2. TÍNH TOÁN THẺ CHỈ SỐ =================
    total_models = len(df_power_tool) if not df_power_tool.empty else 0
    
    if not df_power_tool.empty and "Sample Status" in df_power_tool.columns:
        shortage_models = len(df_power_tool[df_power_tool["Sample Status"] == "Shortage"])
    else:
        shortage_models = 0

    # LUẬT MỚI: Nếu > 0 thì gắn CSS màu đỏ + hiệu ứng nhấp nháy (blink)
    if shortage_models > 0:
        shortage_style = "color: red; background-color: pink; animation: blinkAlert 1s infinite;"
    else:
        shortage_style = "color: #000000;"
        
    active_reqs = len(df_st[df_st["Req. status"].isin(["Open", "In testing"])]) if not df_st.empty and "Req. status" in df_st.columns else 0
    overdue_reqs = len(df_st[df_st["Req. status"] == "Overdue"]) if not df_st.empty and "Req. status" in df_st.columns else 0

    # ================= 3. GIAO DIỆN CHỈ SỐ NHANH =================
    st.markdown(f"""
    <style>
    /* 1. LỚP BỌC NGOÀI ĐỂ TẠO BÓNG ĐỔ */
    .ort-header-wrapper {{
        filter: drop-shadow(4px 4px 0px rgba(0, 0, 0, 0.15)); /* Bóng đổ xám nhạt */
        margin-bottom: 25px;
        margin-top: 30px;
    }}

    /* 2. KHỐI TIÊU ĐỀ ĐƯỢC VÁT 2 GÓC */
    .ort-header {{
        background-color: #EBE600;
        color: #000000;
        padding: 2px 25px;
        font-size: 50px;
        font-weight: 800;
        /* Vát góc trên-trái và góc dưới-phải (25px) */
        clip-path: polygon(25px 0, 100% 0, 100% calc(100% - 25px), calc(100% - 25px) 100%, 0 100%, 0 25px); 
        text-transform: uppercase;
    }}
    .metric-container {{
        display: flex;
        gap: 20px;
        margin-bottom: 30px;
    }}
    .metric-card {{
        flex: 1;
        display: flex;
        flex-direction: column;
        border: 1px solid #000000;
        background-color: #ffffff;
        box-shadow: 4px 4px 0px rgba(0,0,0,0.15); 
        border-radius: 0px !important;
        position: relative;
    }}
    .metric-card::before {{
        content: "";
        position: absolute;
        top: -3px;
        left: -3px; 
        width: 0;
        height: 0;
        border-top: 24px solid #ffffff;
        border-right: 24px solid transparent;
        z-index: 10;
    }}
    .metric-card::after {{
        content: "";
        position: absolute;
        top: 10.5px;
        left: -5px;
        width: 34px;
        height: 3px;
        background-color: #000000;
        transform: rotate(-45deg);
        z-index: 11;
    }}
    .metric-title {{
        background-color: #000000;
        color: #ffffff;
        padding: 5px;
        text-align: center;
        font-weight: bold;
        font-size: 20px;
        border-bottom: 2px solid #000000;
    }}
    /* THÊM ĐOẠN NÀY ĐỂ TẠO HIỆU ỨNG NHẤP NHÁY (Chú ý dấu {{ và }}) */
    @keyframes blinkAlert {{
        0% {{ opacity: 1; transform: scale(1); }}
        50% {{ opacity: 0.2; transform: scale(1.1); }} 
        100% {{ opacity: 1; transform: scale(1); }}
    }}
    .metric-value {{
        padding: 4px;
        text-align: center;
        font-size: 40px;
        font-weight: 900;
        color: #000000;
        background-color: #ffffff;
    }}
    </style>

    <div class="ort-header-wrapper">
        <div class="ort-header">
            <h2 style='text-align: center; color: #000000; background-color: transparent; margin: 5px 0;'>
                📊 M A S T E R - D A S H B O A R D
            </h2>
        </div>
    </div>

    <div class="metric-container">
        <div class="metric-card">
            <div class="metric-title">TOTAL MODELS</div>
            <div class="metric-value">{total_models}</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">⚠️ SHORTAGE ALERTS</div>
            <div class="metric-value" style="{shortage_style}">{shortage_models}</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">ACTIVE REQUESTS</div>
            <div class="metric-value">{active_reqs}</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">OVERDUE REQUESTS</div>
            <div class="metric-value">{overdue_reqs}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ================= 4. KHU VỰC BIỂU ĐỒ (DASHBOARD) =================
    st.divider()
    
    # CSS định dạng viền cho chart (Giữ nguyên của bạn)
    st.markdown("""
    <style>
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border: 3px solid #000000 !important;
        border-radius: 0px !important;
        clip-path: polygon(25px 0, 100% 0, 100% calc(100% - 25px), calc(100% - 25px) 100%, 0 100%, 0 25px) !important;
        background-color: #ffffff !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        padding: 0px !important; width: 100% !important;
    }
    .industrial-header-title {
        background-color: #000000 !important; color: #ffffff !important;
        padding: 15px 20px !important; font-size: 16px !important;
        font-weight: 800 !important; text-align: center !important;
        text-transform: uppercase !important; margin: 0px !important;
        border-bottom: 2px solid #000000 !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] > div > div:nth-child(n+2) {
        padding: 10px 20px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # CHIA LÀM 2 CỘT CHO PIE CHART VÀ LINE CHART
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        with st.container(border=True):
            st.markdown('<div class="industrial-header-title">🎯 Tỷ lệ Pass/Fail (First Pass Yield)</div>', unsafe_allow_html=True)
            
            if not df_st.empty and "Test result" in df_st.columns:
                # Lọc bỏ các dòng chưa có kết quả (Null)
                df_pie = df_st[df_st["Test result"].notna() & (df_st["Test result"].str.strip() != "")].copy()
                pie_data = df_pie["Test result"].value_counts().reset_index()
                pie_data.columns = ["Trạng thái", "Số lượng"]
                
                # Vẽ biểu đồ Pie (Dạng Donut cho hiện đại)
                fig_pie = px.pie(
                    pie_data, 
                    names="Trạng thái", 
                    values="Số lượng",
                    color="Trạng thái",
                    color_discrete_map={
                        "Pass": "#28a745",       # Xanh lá
                        "Fail": "#dc3545",       # Đỏ
                        "In testing": "#ffc107", # Vàng
                        "Pending": "#6c757d"     # Xám
                    },
                    hole=0.4 
                )
                fig_pie.update_layout(margin=dict(t=15, b=15, l=15, r=15))
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Chưa có dữ liệu Test Result.")

    with col_chart2:
        with st.container(border=True):
            st.markdown('<div class="industrial-header-title">📉 Biến động Chất lượng (Pass/Fail) theo tháng</div>', unsafe_allow_html=True)
            
            if not df_st.empty and "End date" in df_st.columns:
                # Chỉ lấy những mẫu đã test xong (Pass hoặc Fail)
                df_line = df_st[df_st["Test result"].isin(["Pass", "Fail"])].copy()
                df_line['End date'] = pd.to_datetime(df_line['End date'], errors='coerce')
                df_line = df_line.dropna(subset=['End date'])
                
                if not df_line.empty:
                    # Gom nhóm theo tháng hoàn thành
                    df_line['Tháng'] = df_line['End date'].dt.strftime('%Y-%m')
                    line_data = df_line.groupby(['Tháng', 'Test result']).size().unstack(fill_value=0).reset_index()
                    
                    # Xác định các đường cần vẽ
                    y_cols = [c for c in ["Fail", "Pass"] if c in line_data.columns]
                    
                    # Vẽ biểu đồ Line
                    fig_line = px.line(
                        line_data, 
                        x="Tháng", 
                        y=y_cols,
                        markers=True,
                        color_discrete_map={"Fail": "#dc3545", "Pass": "#28a745"}
                    )
                    fig_line.update_layout(
                        margin=dict(t=15, b=15, l=15, r=15),
                        xaxis_title="", 
                        yaxis_title="Số lượng mẫu",
                        legend_title="Kết quả"
                    )
                    st.plotly_chart(fig_line, use_container_width=True)
                else:
                    st.info("Chưa có mẫu nào hoàn thành để vẽ biểu đồ.")
            else:
                st.info("Thiếu dữ liệu End date.")

    # BIỂU ĐỒ MIỀN (AREA CHART) FULL CHIỀU RỘNG Ở HÀNG DƯỚI
    with st.container(border=True):
        st.markdown('<div class="industrial-header-title">🌊 Xu hướng Năng lực phòng Test: Mở mới vs. Hoàn thành</div>', unsafe_allow_html=True)
        
        # Giải thích logic: Vì chúng ta chưa có dữ liệu lịch sử của cột Gap từng ngày trong quá khứ, 
        # cách tốt nhất để xem xu hướng "Shortage/Tồn đọng" là so sánh lượng Yêu cầu gửi vào (Mở mới) 
        # và lượng Yêu cầu test xong (Hoàn thành) theo từng tháng.
        if not df_st.empty and "Req. date" in df_st.columns and "End date" in df_st.columns:
            df_area = df_st.copy()
            
            # Đếm số lượng Mở mới theo tháng
            df_area['Req. date'] = pd.to_datetime(df_area['Req. date'], errors='coerce')
            opened = df_area.dropna(subset=['Req. date']).copy()
            opened['Tháng'] = opened['Req. date'].dt.strftime('%Y-%m')
            opened_counts = opened.groupby('Tháng').size().rename("Mở mới")
            
            # Đếm số lượng Hoàn thành theo tháng
            df_area['End date'] = pd.to_datetime(df_area['End date'], errors='coerce')
            closed = df_area[df_area["Test result"].isin(["Pass", "Fail"])].dropna(subset=['End date']).copy()
            closed['Tháng'] = closed['End date'].dt.strftime('%Y-%m')
            closed_counts = closed.groupby('Tháng').size().rename("Hoàn thành")
            
            # Gộp 2 bảng lại
            area_data = pd.concat([opened_counts, closed_counts], axis=1).fillna(0).reset_index()
            
            if not area_data.empty:
                fig_area = px.area(
                    area_data, 
                    x="Tháng", 
                    y=["Mở mới", "Hoàn thành"],
                    color_discrete_map={"Mở mới": "#dc3545", "Hoàn thành": "#28a745"} # Đỏ (Báo động nợ) vs Xanh (Giải quyết xong)
                )
                fig_area.update_layout(
                    margin=dict(t=15, b=15, l=15, r=15),
                    xaxis_title="", 
                    yaxis_title="Số lượng Request",
                    legend_title="Trạng thái"
                )
                st.plotly_chart(fig_area, use_container_width=True)
            else:
                st.info("Chưa đủ dữ liệu ngày tháng để vẽ Area Chart.")

    # ================= 5. KHU VỰC BẢNG TÓM TẮT (SHORTAGE ALERT - CÓ PHÂN TRANG) =================
    st.divider()
    st.markdown("""
    <style>
    .alert-header-v2-wrapper {
    /* Tạo khung bóng đổ xám nhạt ôm sát hình dạng vát góc */
    filter: drop-shadow(4px 4px 0px rgba(0, 0, 0, 0.2));
    margin-bottom: 25px;
    margin-top: 30px;
    }

    .alert-header-v2 {
        background-color: #EBE600;
        color: #000000;
        padding: 10px 25px; /* Điều chỉnh lại padding cho cân đối */
        font-size: 22px;
        font-weight: 800;
        /* Công thức vát góc trên-trái và dưới-phải (20px) */
        clip-path: polygon(20px 0, 100% 0, 100% calc(100% - 20px), calc(100% - 20px) 100%, 0 100%, 0 20px);
        margin-bottom: 20px;
        display: inline-flex; /* Đổi thành inline-flex để đi kèm với fit-content */
        align-items: center;
        gap: 10px;
        width: fit-content; /* CHÌA KHÓA: Ép chiều ngang vừa khít với nội dung */
    }
    </style>
    <div class="alert-header-v2-wrapper">
        <div class="alert-header-v2">
            <h2 style='text-align: center; color: #000000; background-color: #EBE600; padding: 10px;'>
                ⚠️ SHORTAGE ALERTS (URGENT ACTION REQUIRED)
            </h2>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if not df_power_tool.empty and "Gap" in df_power_tool.columns:
        # Lấy các model bị Shortage
        df_shortage = df_power_tool[df_power_tool["Gap"] > 0].copy()
        
        if not df_shortage.empty:
            # 1. ƯU TIÊN SẮP XẾP: Model nào bị ngâm Shortage lâu nhất sẽ bị đẩy lên đầu bảng để dí P.I.C
            if "Shortage days val" in df_shortage.columns:
                df_shortage = df_shortage.sort_values(by=["Shortage days val", "Gap"], ascending=[False, False])
            else:
                df_shortage = df_shortage.sort_values(by="Gap", ascending=False)
                
            # 2. BỔ SUNG CỘT SHORTAGE DAYS VÀO BẢNG HIỂN THỊ
            cols_to_show = ["ORT model", "Model name", "P.I.C", "Gap", "Shortage days", "Action required"]
            cols_exist = [col for col in cols_to_show if col in df_shortage.columns]
            
            # Chuẩn hóa bảng: Xóa index cũ, tạo cột Số thứ tự mới
            df_show = df_shortage[cols_exist].reset_index(drop=True)
            df_show.index = df_show.index + 1  
            
            total_items = len(df_show)

            # --- KHỞI TẠO BỘ NHỚ CHO PHÂN TRANG ---
            if "shortage_page" not in st.session_state:
                st.session_state.shortage_page = 1

            # --- GIAO DIỆN CHỌN SỐ LƯỢNG ITEM / TRANG ---
            import math
            col_limit, col_info_top = st.columns([2, 8])
            with col_limit:
                items_per_page = st.selectbox(
                    "Số dòng / trang:", 
                    options=[10, 20, 30, 40, 50], 
                    index=0, 
                    key="shortage_per_page"
                )
            
            total_pages = math.ceil(total_items / items_per_page)

            # Đảm bảo trang hiện tại không bị lỗi khi đổi số lượng item
            if st.session_state.shortage_page > total_pages:
                st.session_state.shortage_page = total_pages
            if st.session_state.shortage_page < 1:
                st.session_state.shortage_page = 1

            # --- CẮT DỮ LIỆU CHO TRANG HIỆN TẠI ---
            start_idx = (st.session_state.shortage_page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            df_page = df_show.iloc[start_idx:end_idx]

            # --- THIẾT KẾ BẢNG PANDAS STYLER ---
            styled_df = (
                df_page.style
                .set_properties(**{
                    'background-color': '#ffffff',
                    'color': '#000000',
                    'border': '1px solid #dddddd',
                    'padding': '10px',
                    'text-align': 'center',
                    'font-family': 'Arial, sans-serif'
                })
                .set_table_styles([
                    {'selector': 'th', 'props': [
                        ('background-color', '#000000'), 
                        ('color', '#EBE600'), 
                        ('font-weight', 'bold'),
                        ('font-size', '14px'),
                        ('text-align', 'center'),
                        ('border', '1px solid #dddddd'),
                        ('padding', '12px')
                    ]},
                    {'selector': 'tr:hover', 'props': [
                        ('background-color', '#f5f5f5')
                    ]}
                ])
                .map(lambda x: 'background-color: #ffe6e6; color: #cc0000; font-weight: bold;' if isinstance(x, (int, float)) and x > 0 else '', subset=['Gap'])
            )

            st.table(styled_df)

            # --- GIAO DIỆN NÚT CHUYỂN TRANG ---
            if total_pages > 1:
                col_first, col_prev, col_page_num, col_next, col_last = st.columns([1, 1, 2, 1, 1])

                with col_first:
                    if st.button("⏮️ Đầu", disabled=(st.session_state.shortage_page == 1), use_container_width=True):
                        st.session_state.shortage_page = 1
                        st.rerun()
                with col_prev:
                    if st.button("◀ Trước", disabled=(st.session_state.shortage_page == 1), use_container_width=True):
                        st.session_state.shortage_page -= 1
                        st.rerun()
                with col_page_num:
                    st.markdown(f"<div style='text-align: center; padding-top: 8px; font-weight: bold; font-size: 16px;'>Trang {st.session_state.shortage_page} / {total_pages}</div>", unsafe_allow_html=True)
                with col_next:
                    if st.button("Sau ▶", disabled=(st.session_state.shortage_page == total_pages), use_container_width=True):
                        st.session_state.shortage_page += 1
                        st.rerun()
                with col_last:
                    if st.button("Cuối ⏭️", disabled=(st.session_state.shortage_page == total_pages), use_container_width=True):
                        st.session_state.shortage_page = total_pages
                        st.rerun()
                        
        else:
            st.success("🎉 Tuyệt vời! Hiện tại hệ thống không ghi nhận Model nào bị thiếu mẫu.")
    else:
        st.info("Chưa có dữ liệu.")

    # ================= 6. KHU VỰC BẢNG S&T REQUEST CHƯA CLOSED =================
    st.divider()
    st.markdown("""
    <style>
    .alert-header-v2-wrapper {
    /* Tạo khung bóng đổ xám nhạt ôm sát hình dạng vát góc */
    filter: drop-shadow(4px 4px 0px rgba(0, 0, 0, 0.2));
    margin-bottom: 25px;
    margin-top: 30px;
    }
    .alert-header-v2 {
        background-color: #EBE600;
        color: #000000;
        padding: 10px 25px; /* Điều chỉnh lại padding cho cân đối */
        font-size: 22px;
        font-weight: 800;
        /* Công thức vát góc trên-trái và dưới-phải (20px) */
        clip-path: polygon(20px 0, 100% 0, 100% calc(100% - 20px), calc(100% - 20px) 100%, 0 100%, 0 20px);
        margin-bottom: 20px;
        display: inline-flex; /* Đổi thành inline-flex để đi kèm với fit-content */
        align-items: center;
        gap: 10px;
        width: fit-content; /* CHÌA KHÓA: Ép chiều ngang vừa khít với nội dung */
    }
    </style>
    <div class="alert-header-v2-wrapper">
        <div class="alert-header-v2">
            <h2 style='text-align: center; color: #000000; background-color: #EBE600; padding: 10px;'>
                📝 ACTIVE REQUESTS
            </h2>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if not df_st.empty and "Req. status" in df_st.columns:
        # 1. Lọc các request có trạng thái KHÁC "Closed" (loại bỏ chữ hoa/thường)
        df_st_active = df_st[df_st["Req. status"].astype(str).str.strip().str.lower() != "closed"].copy()
        
        if not df_st_active.empty:
            # Lấy toàn bộ các trường cần thiết để hiển thị lên bảng
            st_cols_to_show = [
                "Req. id", "Req. date", "TTI model", "ORT model", "Req. qty", 
                "SAM Job", "CB/F", "SCP/F", "DR/F", "Item Test", 
                "Start date", "End date", "Test result", "Req. duration", "Req. status"
            ]
            st_cols_exist = [col for col in st_cols_to_show if col in df_st_active.columns]
            
            # Sắp xếp theo ngày yêu cầu mới nhất lên đầu (nếu có cột ngày)
            if "Req. date" in df_st_active.columns:
                df_st_active = df_st_active.sort_values(by="Req. date", ascending=False)
                
            # Chuẩn hóa số thứ tự
            df_st_show = df_st_active[st_cols_exist].reset_index(drop=True)
            df_st_show.index = df_st_show.index + 1  
            
            total_st_items = len(df_st_show)

            # --- KHỞI TẠO BỘ NHỚ CHO PHÂN TRANG BẢNG S&T ---
            if "st_page" not in st.session_state:
                st.session_state.st_page = 1

            # --- GIAO DIỆN CHỌN SỐ LƯỢNG ITEM / TRANG ---
            col_st_limit, col_st_info = st.columns([2, 8])
            with col_st_limit:
                st_items_per_page = st.selectbox(
                    "Số dòng / trang (Request):", 
                    options=[10, 20, 30, 40, 50], 
                    index=0, 
                    key="st_per_page"
                )
            
            total_st_pages = math.ceil(total_st_items / st_items_per_page)

            if st.session_state.st_page > total_st_pages:
                st.session_state.st_page = total_st_pages
            if st.session_state.st_page < 1:
                st.session_state.st_page = 1

            # --- CẮT DỮ LIỆU CHO TRANG HIỆN TẠI ---
            st_start_idx = (st.session_state.st_page - 1) * st_items_per_page
            st_end_idx = st_start_idx + st_items_per_page
            df_st_page = df_st_show.iloc[st_start_idx:st_end_idx]

            # --- HÀM TÔ MÀU RIÊNG CHO CỘT TRẠNG THÁI ---
            def highlight_status(val):
                val_str = str(val).strip().lower()
                if val_str == "overdue":
                    return 'background-color: #ffe6e6; color: #cc0000; font-weight: bold;'
                elif val_str in ["open", "in testing"]:
                    return 'background-color: #fffacd; color: #b8860b; font-weight: bold;'
                return ''

            # --- THIẾT KẾ BẢNG PANDAS STYLER ---
            styled_st_df = (
                df_st_page.style
                .set_properties(**{
                    'background-color': '#ffffff',
                    'color': '#000000',
                    'border': '1px solid #dddddd',
                    'padding': '10px',
                    'text-align': 'center',
                    'font-family': 'Arial, sans-serif'
                })
                .set_table_styles([
                    {'selector': 'th', 'props': [
                        ('background-color', '#000000'), 
                        ('color', '#EBE600'), 
                        ('font-weight', 'bold'),
                        ('font-size', '14px'),
                        ('text-align', 'center'),
                        ('border', '1px solid #dddddd'),
                        ('padding', '12px')
                    ]},
                    {'selector': 'tr:hover', 'props': [
                        ('background-color', '#f5f5f5')
                    ]}
                ])
            )
            
            # Áp dụng logic tô màu nếu tồn tại cột Req. status
            if "Req. status" in df_st_page.columns:
                styled_st_df = styled_st_df.map(highlight_status, subset=["Req. status"])

            st.table(styled_st_df)

            # --- GIAO DIỆN NÚT CHUYỂN TRANG DÀNH RIÊNG CHO BẢNG S&T ---
            if total_st_pages > 1:
                st_col_first, st_col_prev, st_col_page_num, st_col_next, st_col_last = st.columns([1, 1, 2, 1, 1])

                with st_col_first:
                    if st.button("⏮️ Đầu", key="st_btn_first", disabled=(st.session_state.st_page == 1), use_container_width=True):
                        st.session_state.st_page = 1
                        st.rerun()
                with st_col_prev:
                    if st.button("◀ Trước", key="st_btn_prev", disabled=(st.session_state.st_page == 1), use_container_width=True):
                        st.session_state.st_page -= 1
                        st.rerun()
                with st_col_page_num:
                    st.markdown(f"<div style='text-align: center; padding-top: 8px; font-weight: bold; font-size: 16px;'>Trang {st.session_state.st_page} / {total_st_pages}</div>", unsafe_allow_html=True)
                with st_col_next:
                    if st.button("Sau ▶", key="st_btn_next", disabled=(st.session_state.st_page == total_st_pages), use_container_width=True):
                        st.session_state.st_page += 1
                        st.rerun()
                with st_col_last:
                    if st.button("Cuối ⏭️", key="st_btn_last", disabled=(st.session_state.st_page == total_st_pages), use_container_width=True):
                        st.session_state.st_page = total_st_pages
                        st.rerun()
                        
        else:
            st.success("🎉 Tuyệt vời! Hiện tại không có Request nào đang bị tồn đọng (Tất cả đều đã Closed).")
    else:
        st.info("Chưa có dữ liệu Request.")