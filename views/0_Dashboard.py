import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import math 
from datetime import date, timedelta
import plotly.express as px
import plotly.graph_objects as go

# 1. Import đúng tên hàm từ db_helper
try:
    from database.db_helper import get_st_requests, get_report_qty
except ImportError:
    pass

def render(df_power_tool):
    # ========================================================
    # Ép lọc: Ẩn toàn bộ model đã bị đánh dấu Suspended
    if "is_suspended" in df_power_tool.columns:
        df_power_tool = df_power_tool[~df_power_tool["is_suspended"].astype(bool)]
    # ========================================================
    # ================= 0. KHU VỰC CẢNH BÁO THIẾU DỮ LIỆU (SMART ALERT) =================
    today = date.today()
    yesterday = today - timedelta(days=1)
    missing_dates = []
    
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
                missing_dates.append(yesterday.strftime("%b %d %Y (Chưa có dữ liệu hợp lệ)"))
        else:
            missing_dates.append(yesterday.strftime("%b %d %Y (Database trống)"))
            
    except Exception as e:
        st.error(f"Lỗi quét ngày: {e}")

    @st.dialog("📣 CẢNH BÁO: QUÊN NHẬP REPORT QTY", width="small")
    def modal_missing_alert(dates):
        st.error("Hệ thống phát hiện chưa có báo cáo sản lượng cho các ngày sau:")
        for d in dates:
            st.markdown(f"- **{d}**")
        st.caption("💡 Vui lòng nhập bổ sung để Dashboard tính toán FG Accum và Gap chính xác nhất.")
        if st.button("Đã hiểu & Đóng", use_container_width=True):
            st.rerun()

    if missing_dates:
        num_missing = len(missing_dates)
        button_text = f"📢Tokuda ({num_missing})"

        st.markdown("""
        <span class="alert-btn-wrapper"></span>
        <style>
        div[data-testid="block-container"] {
            position: relative;
        }
        div[data-testid="stElementContainer"]:has(.alert-btn-wrapper) + div[data-testid="stElementContainer"] button {
            position: absolute !important;
            top: -70px !important;
            left: 25px !important;
            z-index: 999999 !important;
            animation: ring_phone 1s infinite;
            background-color: #ffcccc !important;
            border: 2px solid #cc0000 !important;
            color: #cc0000 !important;
            border-radius: 20px !important;
            height: 40px !important;
            padding: 0px 15px !important;
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
        
        alert_clicked = st.button(button_text, help="Click để xem chi tiết các ngày thiếu Report")
    else:
        alert_clicked = False

    if "dashboard_alert_shown" not in st.session_state:
        st.session_state.dashboard_alert_shown = False

    if missing_dates and not st.session_state.dashboard_alert_shown:
        st.session_state.dashboard_alert_shown = True
        modal_missing_alert(missing_dates)

    if alert_clicked and missing_dates:
        modal_missing_alert(missing_dates)

    # ================= 1. CHUẨN BỊ DỮ LIỆU BỔ SUNG =================
    try:
        df_st_raw = get_st_requests()
        
        if not df_st_raw.empty:
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

    if shortage_models > 0:
        shortage_style = "color: red; background-color: pink; animation: blinkAlert 1s infinite;"
    else:
        shortage_style = "color: #000000;"
        
    active_reqs = len(df_st[df_st["Req. status"].isin(["Open", "In testing"])]) if not df_st.empty and "Req. status" in df_st.columns else 0
    overdue_reqs = len(df_st[df_st["Req. status"] == "Overdue"]) if not df_st.empty and "Req. status" in df_st.columns else 0

    # ================= 3. GIAO DIỆN CHỈ SỐ NHANH =================
    st.markdown(f"""
    <style>
    .ort-header-wrapper {{
        filter: drop-shadow(4px 4px 0px rgba(0, 0, 0, 0.15));
        margin-bottom: 25px;
        margin-top: 30px;
    }}
    .ort-header {{
        background-color: #EBE600;
        color: #000000;
        padding: 2px 25px;
        font-size: 50px;
        font-weight: 800;
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
                👽 M A S T E R - D A S H B O A R D 👽
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

    # ================= 4. KHU VỰC BIỂU ĐỒ (DASHBOARD) =================
    
    st.markdown("""
    <style>
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border: 3px solid #000000 !important;
        border-radius: 0px !important;
        clip-path: polygon(25px 0, 100% 0, 100% calc(100% - 25px), calc(100% - 25px) 100%, 0 100%, 0 25px) !important;
        background-color: #ffffff !important;
        padding: 0px !important;
        overflow: hidden !important; 
        margin-bottom: 30px !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] > div,
    div[data-testid="stVerticalBlockBorderWrapper"] > div > div[data-testid="stVerticalBlock"] {
        padding: 0px !important;
        gap: 0px !important;
        width: 100% !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] .element-container:first-child {
        margin-bottom: 0px !important;
    }
    .industrial-header-title {
        background-color: #000000 !important; 
        color: #ffffff !important;
        padding: 15px 20px !important; 
        font-size: 16px !important;
        font-weight: 900 !important; 
        text-align: center !important;
        text-transform: uppercase !important; 
        margin: 0px !important;
        border-bottom: 3px solid #000000 !important;
        display: block !important;
        width: 100% !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] .stPlotlyChart {
        padding: 15px 20px 5px 20px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if not df_st.empty and "Req. date" in df_st.columns:
        df_chart = df_st.copy()
        df_chart['Req. date'] = pd.to_datetime(df_chart['Req. date'], errors='coerce')
        df_chart = df_chart.dropna(subset=['Req. date'])
        
        if not df_chart.empty:
            df_chart['Year'] = df_chart['Req. date'].dt.year
            df_chart['Month'] = df_chart['Req. date'].dt.strftime('%Y-%m')
            
            target_col = 'ORT model' if 'ORT model' in df_chart.columns else df_chart.columns[0]
            def classify_category(val):
                return "Battery" if str(val).strip().startswith("130") else "Power Tool"
            df_chart['Category'] = df_chart[target_col].apply(classify_category)
            
            current_year = date.today().year
            available_years = sorted(df_chart['Year'].unique().tolist(), reverse=True)
            default_years = [current_year] if current_year in available_years else available_years
            
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                selected_years = st.multiselect("🐦‍⬛Filter by Year:", options=available_years, default=default_years)
            with col_f2:
                available_months = sorted(df_chart['Month'].unique().tolist())
                selected_months = st.multiselect("🐈‍⬛Filter by Month:", options=available_months, default=available_months)
            
            if selected_years:
                df_chart = df_chart[df_chart['Year'].isin(selected_years)]
            if selected_months:
                df_chart = df_chart[df_chart['Month'].isin(selected_months)]
            
            if not df_chart.empty:
                # BỘ JAVASCRIPT THÔNG MINH CHO NÚT COPY / DOWNLOAD
                export_js = """
                <script>
                function dataURItoBlob(dataURI) {
                    var byteString = atob(dataURI.split(',')[1]);
                    var mimeString = dataURI.split(',')[0].split(':')[1].split(';')[0];
                    var ab = new ArrayBuffer(byteString.length);
                    var ia = new Uint8Array(ab);
                    for (var i = 0; i < byteString.length; i++) { ia[i] = byteString.charCodeAt(i); }
                    return new Blob([ab], {type: mimeString});
                }

                function exportChart(btn, chartName) {
                    var originalText = btn.innerHTML;
                    btn.innerHTML = "⏳...";
                    var wrapper = btn.parentElement.nextElementSibling;
                    var plotDiv = wrapper.querySelector('.plotly-graph-div');
                    
                    if (!plotDiv) {
                        btn.innerHTML = "❌";
                        setTimeout(function() { btn.innerHTML = originalText; }, 2000);
                        return;
                    }

                    // Xuất ảnh lõi biểu đồ độ phân giải cao 1400x700
                    Plotly.toImage(plotDiv, {format: 'png', width: 1400, height: 700})
                        .then(function(dataUrl) {
                            var blob = dataURItoBlob(dataUrl);
                            if (navigator.clipboard && window.ClipboardItem) {
                                navigator.clipboard.write([
                                    new ClipboardItem({ 'image/png': blob })
                                ]).then(function() {
                                    btn.innerHTML = "✅ COPIED";
                                    setTimeout(function() { btn.innerHTML = originalText; }, 2000);
                                }).catch(function(err) {
                                    // Fallback tải về nếu bị chặn
                                    Plotly.downloadImage(plotDiv, {format: 'png', width: 1400, height: 700, filename: chartName});
                                    btn.innerHTML = "⬇️ SAVED";
                                    setTimeout(function() { btn.innerHTML = originalText; }, 2000);
                                });
                            } else {
                                Plotly.downloadImage(plotDiv, {format: 'png', width: 1400, height: 700, filename: chartName});
                                btn.innerHTML = "⬇️ SAVED";
                                setTimeout(function() { btn.innerHTML = originalText; }, 2000);
                            }
                        })
                        .catch(function(err) {
                            btn.innerHTML = "❌ FAILED";
                            setTimeout(function() { btn.innerHTML = originalText; }, 2000);
                        });
                }
                </script>
                """
                # =========================================================
                # KHAI BÁO HÀNG 1 
                # =========================================================
                row1_col1, row1_col2 = st.columns(2)
                
                with row1_col1:
                    qty_col = 'Req. qty' if 'Req. qty' in df_chart.columns else None
                    if qty_col:
                        df_chart[qty_col] = pd.to_numeric(df_chart[qty_col], errors='coerce').fillna(1)
                    else:
                        df_chart['Req. qty'] = 1
                        qty_col = 'Req. qty'
                    
                    pivot_df = df_chart.groupby(['Month', 'Category'])[qty_col].sum().unstack(fill_value=0).reset_index()
                    for cat in ["Battery", "Power Tool"]:
                        if cat not in pivot_df.columns: pivot_df[cat] = 0
                    pivot_df['Total'] = pivot_df["Battery"] + pivot_df["Power Tool"]
                    pivot_df['Total_Text'] = pivot_df['Total'].apply(lambda x: f"<b>{x}</b>")

                    fig_combo = go.Figure()
                    fig_combo.add_trace(go.Bar(
                        x=pivot_df['Month'], y=pivot_df['Battery'], name='Battery', marker_color='#000000',
                        hovertemplate='<b>Battery</b><br>%{x}: %{y}<extra></extra>'
                    ))
                    fig_combo.add_trace(go.Bar(
                        x=pivot_df['Month'], y=pivot_df['Power Tool'], name='Power Tool', marker_color='#EBE600',
                        hovertemplate='<b>Power Tool</b><br>%{x}: %{y}<extra></extra>',
                        hoverlabel=dict(font=dict(color='#000000'), bgcolor='#ffffff') 
                    ))
                    fig_combo.add_trace(go.Scatter(
                        x=pivot_df['Month'], y=pivot_df['Total'], name='Total', mode='lines+markers+text', 
                        text=pivot_df['Total_Text'], textposition='top center', 
                        textfont=dict(size=14, color='#dc3545'), line=dict(color='#dc3545', width=3),
                        marker=dict(size=8), cliponaxis=False,
                        hovertemplate='<b>Total</b><br>%{x}: %{y}<extra></extra>'
                    ))
                    
                    fig_combo.update_layout(
                        barmode='group', height=450, 
                        margin=dict(t=40, b=15, l=15, r=15), # Chỉnh l=15 (tự động dãn)
                        xaxis_title="", yaxis_title="Sample Quantity",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                        yaxis=dict(gridcolor='#e5e5e5', automargin=True) # Thêm automargin
                    )
                    
                    # Thêm 'responsive': True vào cấu hình xuất HTML
                    plot_html = fig_combo.to_html(full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False, 'responsive': True})
                    html_card = f"""
                    <div style="background-color: #000000; padding: 2px; clip-path: polygon(20px 0, calc(100% - 20px) 0, 100% 20px, 100% calc(100% - 20px), calc(100% - 20px) 100%, 20px 100%, 0 calc(100% - 20px), 0 20px); width: 100%; box-sizing: border-box; font-family: Arial, sans-serif;">
                        <div style="background-color: #ffffff; clip-path: polygon(19px 0, calc(100% - 19px) 0, 100% 19px, 100% calc(100% - 19px), calc(100% - 19px) 100%, 19px 100%, 0 calc(100% - 19px), 0 19px); width: 100%; height: 100%; box-sizing: border-box;">
                            <div style="background-color: #000000; color: #ffffff; padding: 15px; text-align: center; font-weight: 900; font-size: 16px; text-transform: uppercase; border-bottom: 2px solid #000000; position: relative;">
                                💀💀💀 MONTHLY TEST SAMPLE VOLUME 💀💀💀
                                <button onclick="exportChart(this, 'Sample_Volume')" style="position: absolute; right: 15px; top: 50%; transform: translateY(-50%); background-color: #EBE600; color: #000000; border: none; padding: 6px 12px; font-weight: 900; cursor: pointer; border-radius: 4px; font-size: 12px;">
                                    💾 COPY
                                </button>
                            </div>
                            <div style="padding: 10px;">{plot_html}</div>
                        </div>
                    </div>
                    {export_js}
                    """
                    components.html(html_card, height=550)

                with row1_col2:
                    df_pf = df_chart[df_chart["Test result"].isin(["Pass", "Fail"])].copy()
                    if not df_pf.empty:
                        pf_pivot = df_pf.groupby(['Month', 'Test result']).size().unstack(fill_value=0).reset_index()
                        for cat in ["Pass", "Fail"]:
                            if cat not in pf_pivot.columns: pf_pivot[cat] = 0
                        
                        pf_pivot['Total_PF'] = pf_pivot['Pass'] + pf_pivot['Fail']
                        pf_pivot['Pass_Text'] = pf_pivot.apply(lambda x: f"<b>{(x['Pass']/x['Total_PF']*100):.1f}%</b>" if x['Total_PF'] > 0 and x['Pass'] > 0 else "", axis=1)
                        pf_pivot['Fail_Text'] = pf_pivot.apply(lambda x: f"<b>{(x['Fail']/x['Total_PF']*100):.1f}%</b>" if x['Total_PF'] > 0 and x['Fail'] > 0 else "", axis=1)
                        
                        fig_pf = go.Figure()
                        fig_pf.add_trace(go.Bar(
                            x=pf_pivot['Month'], y=pf_pivot['Pass'], name='Pass', marker_color='#28a745',
                            text=pf_pivot['Pass_Text'], textposition='inside', insidetextanchor='end', textfont=dict(color='white', size=14),
                            hovertemplate='<b>Pass</b><br>%{x}: %{y} samples<extra></extra>' 
                        ))
                        fig_pf.add_trace(go.Bar(
                            x=pf_pivot['Month'], y=pf_pivot['Fail'], name='Fail', marker_color='#dc3545',
                            text=pf_pivot['Fail_Text'], textposition='inside', insidetextanchor='end', textfont=dict(color='white', size=14),
                            hovertemplate='<b>Fail</b><br>%{x}: %{y} samples<extra></extra>' 
                        ))
                        
                        fig_pf.update_layout(
                            barmode='stack', barnorm='percent', height=450, 
                            margin=dict(t=40, b=15, l=15, r=15), # Chỉnh l=15 (tự động dãn)
                            xaxis_title="", yaxis_title="Percentage (%)",
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                            yaxis=dict(gridcolor='#e5e5e5', ticksuffix="%", automargin=True) # Thêm automargin
                        )
                        
                        # Thêm 'responsive': True
                        plot_html_pf = fig_pf.to_html(full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False, 'responsive': True})
                        html_card_pf = f"""
                        <div style="background-color: #000000; padding: 2px; clip-path: polygon(20px 0, calc(100% - 20px) 0, 100% 20px, 100% calc(100% - 20px), calc(100% - 20px) 100%, 20px 100%, 0 calc(100% - 20px), 0 20px); width: 100%; box-sizing: border-box; font-family: Arial, sans-serif;">
                            <div style="background-color: #ffffff; clip-path: polygon(19px 0, calc(100% - 19px) 0, 100% 19px, 100% calc(100% - 19px), calc(100% - 19px) 100%, 19px 100%, 0 calc(100% - 19px), 0 19px); width: 100%; height: 100%; box-sizing: border-box;">
                                <div style="background-color: #000000; color: #ffffff; padding: 15px; text-align: center; font-weight: 900; font-size: 16px; text-transform: uppercase; border-bottom: 2px solid #000000; position: relative;">
                                    ☠️☠️☠️ PASS / FAIL PERCENTAGE TREND (100% STACKED) ☠️☠️☠️
                                    <button onclick="exportChart(this, 'PassFail_Trend')" style="position: absolute; right: 15px; top: 50%; transform: translateY(-50%); background-color: #EBE600; color: #000000; border: none; padding: 6px 12px; font-weight: 900; cursor: pointer; border-radius: 4px; font-size: 12px;">
                                        💾 COPY
                                    </button>
                                </div>
                                <div style="padding: 10px;">{plot_html_pf}</div>
                            </div>
                        </div>
                        {export_js}
                        """
                        components.html(html_card_pf, height=550)
                    else:
                        st.info("No Pass/Fail test results available for the selected period.")

                # =========================================================
                # KHAI BÁO HÀNG 2 
                # =========================================================
                row2_col1, row2_col2 = st.columns(2)
                
                with row2_col1:
                    if not df_st.empty and "Req. status" in df_st.columns:
                        def clean_status(s):
                            val = str(s).strip().lower()
                            if val == "open": return "Open"
                            if val == "in testing": return "In testing"
                            if val == "overdue": return "Overdue"
                            return None
                            
                        df_backlog = df_st.copy()
                        df_backlog['Clean_Status'] = df_backlog['Req. status'].apply(clean_status)
                        df_backlog = df_backlog.dropna(subset=['Clean_Status'])
                        
                        if not df_backlog.empty:
                            target_col_backlog = 'ORT model' if 'ORT model' in df_backlog.columns else df_backlog.columns[0]
                            backlog_pivot = df_backlog.groupby([target_col_backlog, 'Clean_Status']).size().unstack(fill_value=0)
                            for stat in ["Open", "In testing", "Overdue"]:
                                if stat not in backlog_pivot.columns: backlog_pivot[stat] = 0
                                    
                            backlog_pivot['Total_Backlog'] = backlog_pivot["Open"] + backlog_pivot["In testing"] + backlog_pivot["Overdue"]
                            backlog_pivot = backlog_pivot.sort_values(by='Total_Backlog', ascending=True).tail(15).reset_index()
                            
                            backlog_pivot['Open_Text'] = backlog_pivot['Open'].apply(lambda x: f"<b>{x}</b>" if x > 0 else "")
                            backlog_pivot['InTest_Text'] = backlog_pivot['In testing'].apply(lambda x: f"<b>{x}</b>" if x > 0 else "")
                            backlog_pivot['Overdue_Text'] = backlog_pivot['Overdue'].apply(lambda x: f"<b>{x}</b>" if x > 0 else "")

                            fig_backlog = go.Figure()
                            fig_backlog.add_trace(go.Bar(
                                y=backlog_pivot[target_col_backlog], x=backlog_pivot['Open'], name='Open', 
                                orientation='h', marker_color='#6c757d',
                                text=backlog_pivot['Open_Text'], textposition='inside', insidetextanchor='end', textfont=dict(color='white', size=13),
                                hovertemplate='<b>Open</b><br>%{y}: %{x} requests<extra></extra>'
                            ))
                            fig_backlog.add_trace(go.Bar(
                                y=backlog_pivot[target_col_backlog], x=backlog_pivot['In testing'], name='In testing', 
                                orientation='h', marker_color='#EBE600',
                                text=backlog_pivot['InTest_Text'], textposition='inside', insidetextanchor='end', textfont=dict(color='#000000', size=13),
                                hovertemplate='<b>In testing</b><br>%{y}: %{x} requests<extra></extra>'
                            ))
                            fig_backlog.add_trace(go.Bar(
                                y=backlog_pivot[target_col_backlog], x=backlog_pivot['Overdue'], name='Overdue', 
                                orientation='h', marker_color='#dc3545',
                                text=backlog_pivot['Overdue_Text'], textposition='inside', insidetextanchor='end', textfont=dict(color='white', size=13),
                                hovertemplate='<b>Overdue</b><br>%{y}: %{x} requests<extra></extra>'
                            ))
                            
                            fig_backlog.update_layout(
                                barmode='stack', height=500, 
                                margin=dict(t=40, b=40, l=15, r=15), # Xóa cứng l=150 để tự dãn theo zoom
                                xaxis_title="Request Quantity", yaxis_title="",
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                                xaxis=dict(gridcolor='#e5e5e5', automargin=True),
                                yaxis=dict(automargin=True) # Bật tính năng tự động đo lường độ dài của chữ ORT Model
                            )
                            
                            # Thêm 'responsive': True
                            plot_html_backlog = fig_backlog.to_html(full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False, 'responsive': True})
                            html_card_backlog = f"""
                            <div style="background-color: #000000; padding: 2px; clip-path: polygon(20px 0, calc(100% - 20px) 0, 100% 20px, 100% calc(100% - 20px), calc(100% - 20px) 100%, 20px 100%, 0 calc(100% - 20px), 0 20px); width: 100%; box-sizing: border-box; font-family: Arial, sans-serif;">
                                <div style="background-color: #ffffff; clip-path: polygon(19px 0, calc(100% - 19px) 0, 100% 19px, 100% calc(100% - 19px), calc(100% - 19px) 100%, 19px 100%, 0 calc(100% - 19px), 0 19px); width: 100%; height: 100%; box-sizing: border-box;">
                                    <div style="background-color: #000000; color: #ffffff; padding: 15px; text-align: center; font-weight: 900; font-size: 16px; text-transform: uppercase; border-bottom: 2px solid #000000; position: relative;">
                                        🩻🩻🩻 ACTIVE REQUESTS BACKLOG BY MODEL (TOP 15) 🩻🩻🩻
                                        <button onclick="exportChart(this, 'Active_Backlog')" style="position: absolute; right: 15px; top: 50%; transform: translateY(-50%); background-color: #EBE600; color: #000000; border: none; padding: 6px 12px; font-weight: 900; cursor: pointer; border-radius: 4px; font-size: 12px;">
                                            💾 COPY
                                        </button>
                                    </div>
                                    <div style="padding: 10px;">{plot_html_backlog}</div>
                                </div>
                            </div>
                            {export_js}
                            """
                            components.html(html_card_backlog, height=600)

                with row2_col2:
                    if not df_power_tool.empty and "Sample Status" in df_power_tool.columns:
                        total_mdl = len(df_power_tool)
                        shortage_mdl = len(df_power_tool[df_power_tool["Sample Status"] == "Shortage"])
                        shortage_ratio = (shortage_mdl / total_mdl * 100) if total_mdl > 0 else 0
                        
                        fig_gauge = go.Figure(go.Indicator(
                            mode = "gauge+number", value = shortage_ratio,
                            number = {'suffix': "%", 'valueformat': ".1f", 'font': {'size': 50, 'color': '#dc3545', 'weight': 'bold'}},
                            title = {'text': f"Total Models: {total_mdl} | Shortage: {shortage_mdl}", 'font': {'size': 14, 'color': '#6c757d'}},
                            domain = {'x': [0, 1], 'y': [0, 1]},
                            gauge = {
                                'axis': {'range': [0, 100], 'tickwidth': 2, 'tickcolor': "black"},
                                'bar': {'color': "#dc3545", 'thickness': 0.75}, 
                                'bgcolor': "white", 'borderwidth': 2, 'bordercolor': "#000000",
                                'steps': [
                                    {'range': [0, 5], 'color': "#d4edda"},
                                    {'range': [5, 15], 'color': "#fff3cd"},
                                    {'range': [15, 100], 'color': "#f8d7da"}
                                ],
                            }
                        ))
                        
                        fig_gauge.update_layout(
                            height=500, margin=dict(t=100, b=20, l=15, r=15),
                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
                        )
                        
                        # Thêm 'responsive': True
                        plot_html_gauge = fig_gauge.to_html(full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False, 'responsive': True})
                        html_card_gauge = f"""
                        <div style="background-color: #000000; padding: 2px; clip-path: polygon(20px 0, calc(100% - 20px) 0, 100% 20px, 100% calc(100% - 20px), calc(100% - 20px) 100%, 20px 100%, 0 calc(100% - 20px), 0 20px); width: 100%; box-sizing: border-box; font-family: Arial, sans-serif;">
                            <div style="background-color: #ffffff; clip-path: polygon(19px 0, calc(100% - 19px) 0, 100% 19px, 100% calc(100% - 19px), calc(100% - 19px) 100%, 19px 100%, 0 calc(100% - 19px), 0 19px); width: 100%; height: 100%; box-sizing: border-box;">
                                <div style="background-color: #000000; color: #ffffff; padding: 15px; text-align: center; font-weight: 900; font-size: 16px; text-transform: uppercase; border-bottom: 2px solid #000000; position: relative;">
                                    👻👻👻 SHORTAGE RISK INDICATOR 👻👻👻
                                    <button onclick="exportChart(this, 'Shortage_Gauge')" style="position: absolute; right: 15px; top: 50%; transform: translateY(-50%); background-color: #EBE600; color: #000000; border: none; padding: 6px 12px; font-weight: 900; cursor: pointer; border-radius: 4px; font-size: 12px;">
                                        💾 COPY
                                    </button>
                                </div>
                                <div style="padding: 10px;">{plot_html_gauge}</div>
                            </div>
                        </div>
                        {export_js}
                        """
                        components.html(html_card_gauge, height=600)

            else:
                st.info("No data available for the selected filters.")
        else:
            st.info("No valid date data found.")
    else:
        st.info("Missing 'Req. date' column.")

    # ================= 5. KHU VỰC BẢNG TÓM TẮT (SHORTAGE ALERT - CÓ PHÂN TRANG) =================
    
    st.markdown("""
    <style>
    .alert-header-v2-wrapper {
        filter: drop-shadow(4px 4px 0px rgba(0, 0, 0, 0.2));
        margin-bottom: 25px;
        margin-top: 30px;
    }
    .alert-header-v2 {
        background-color: #EBE600;
        color: #000000;
        padding: 10px 25px;
        font-size: 22px;
        font-weight: 800;
        clip-path: polygon(20px 0, 100% 0, 100% calc(100% - 20px), calc(100% - 20px) 100%, 0 100%, 0 20px);
        margin-bottom: 20px;
        display: block;
        align-items: center;
        gap: 10px;
        width: 100%;
    }
    </style>
    <div class="alert-header-v2-wrapper">
        <div class="alert-header-v2">
            <h2 style='text-align: center; color: #000000; background-color: #EBE600; padding: 10px;'>
                ☢️☢️☢️ SHORTAGE ALERTS (URGENT ACTION REQUIRED) ☢️☢️☢️
            </h2>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if not df_power_tool.empty and "Gap" in df_power_tool.columns:
        df_shortage = df_power_tool[df_power_tool["Gap"] > 0].copy()
        
        if not df_shortage.empty:
            if "shortage_page" not in st.session_state:
                st.session_state.shortage_page = 1

            col_limit, col_filt1, col_filt2 = st.columns([2, 4, 4])
            
            with col_limit:
                items_per_page = st.selectbox(
                    "Rows / page:", 
                    options=[10, 20, 30, 40, 50], 
                    index=0, 
                    key="shortage_per_page"
                )
                
            with col_filt1:
                search_shortage = st.text_input("🔍 Search ORT Model or P.I.C...", key="dash_shortage_search")
                
            with col_filt2:
                action_options = ["All"] + df_shortage["Action required"].dropna().unique().tolist() if "Action required" in df_shortage.columns else ["All"]
                action_filter = st.selectbox("Filter by Action Required", action_options, key="dash_shortage_action")

            if search_shortage:
                mask = df_shortage.astype(str).apply(lambda x: x.str.contains(search_shortage, case=False)).any(axis=1)
                df_shortage = df_shortage[mask]
            
            if action_filter != "All":
                df_shortage = df_shortage[df_shortage["Action required"] == action_filter]
                
            if search_shortage or action_filter != "All":
                st.session_state.shortage_page = 1

            if "Shortage days val" in df_shortage.columns:
                df_shortage = df_shortage.sort_values(by=["Shortage days val", "Gap"], ascending=[False, False])
            else:
                df_shortage = df_shortage.sort_values(by="Gap", ascending=False)
                
            cols_to_show = ["ORT model", "Model name", "P.I.C", "Gap", "Shortage days", "Action required"]
            cols_exist = [col for col in cols_to_show if col in df_shortage.columns]
            
            df_show = df_shortage[cols_exist].reset_index(drop=True)
            df_show.index = df_show.index + 1  
            
            total_items = len(df_show)
            total_pages = math.ceil(total_items / items_per_page) if total_items > 0 else 1

            if st.session_state.shortage_page > total_pages:
                st.session_state.shortage_page = total_pages
            if st.session_state.shortage_page < 1:
                st.session_state.shortage_page = 1

            start_idx = (st.session_state.shortage_page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            df_page = df_show.iloc[start_idx:end_idx]

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

            if total_pages > 1:
                col_first, col_prev, col_page_num, col_next, col_last = st.columns([1, 1, 2, 1, 1])

                with col_first:
                    if st.button("⏮️ First", disabled=(st.session_state.shortage_page == 1), use_container_width=True):
                        st.session_state.shortage_page = 1
                        st.rerun()
                with col_prev:
                    if st.button("◀ Prev", disabled=(st.session_state.shortage_page == 1), use_container_width=True):
                        st.session_state.shortage_page -= 1
                        st.rerun()
                with col_page_num:
                    st.markdown(f"<div style='text-align: center; padding-top: 8px; font-weight: bold; font-size: 16px;'>Page {st.session_state.shortage_page} / {total_pages}</div>", unsafe_allow_html=True)
                with col_next:
                    if st.button("Next ▶", disabled=(st.session_state.shortage_page == total_pages), use_container_width=True):
                        st.session_state.shortage_page += 1
                        st.rerun()
                with col_last:
                    if st.button("Last ⏭️", disabled=(st.session_state.shortage_page == total_pages), use_container_width=True):
                        st.session_state.shortage_page = total_pages
                        st.rerun()
                        
        else:
            st.success("🎉 Great! No models are currently experiencing shortages.")
    else:
        st.info("No data available.")

    # ================= 6. KHU VỰC BẢNG S&T REQUEST CHƯA CLOSED =================
    st.markdown("""
    <style>
    .alert-header-v2-wrapper {
        filter: drop-shadow(4px 4px 0px rgba(0, 0, 0, 0.2));
        margin-bottom: 25px;
        margin-top: 30px;
    }
    .alert-header-v2 {
        background-color: #EBE600;
        color: #000000;
        padding: 10px 25px;
        font-size: 22px;
        font-weight: 800;
        clip-path: polygon(20px 0, 100% 0, 100% calc(100% - 20px), calc(100% - 20px) 100%, 0 100%, 0 20px);
        margin-bottom: 20px;
        display: block;
        align-items: center;
        gap: 10px;
        width: 100%;
    }
    </style>
    <div class="alert-header-v2-wrapper">
        <div class="alert-header-v2">
            <h2 style='text-align: center; color: #000000; background-color: #EBE600; padding: 10px;'>
                ☣️☣️☣️ ACTIVE REQUESTS ☣️☣️☣️
            </h2>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if not df_st.empty and "Req. status" in df_st.columns:
        df_st_active = df_st[df_st["Req. status"].astype(str).str.strip().str.lower() != "closed"].copy()
        
        if not df_st_active.empty:
            if "st_page" not in st.session_state:
                st.session_state.st_page = 1

            st_col_limit, st_col_filt1, st_col_filt2 = st.columns([2, 4, 4])
            
            with st_col_limit:
                st_items_per_page = st.selectbox(
                    "Rows / page (Request):", 
                    options=[10, 20, 30, 40, 50], 
                    index=0, 
                    key="st_per_page"
                )
                
            with st_col_filt1:
                search_st = st.text_input("🔍 Search ORT/TTI Model or SAM Job...", key="dash_st_search")
                
            with st_col_filt2:
                st_status_options = ["All"] + df_st_active["Req. status"].dropna().unique().tolist() if "Req. status" in df_st_active.columns else ["All"]
                st_status_filter = st.selectbox("Filter by Status", st_status_options, key="dash_st_status")

            if search_st:
                mask = df_st_active.astype(str).apply(lambda x: x.str.contains(search_st, case=False)).any(axis=1)
                df_st_active = df_st_active[mask]
            
            if st_status_filter != "All":
                df_st_active = df_st_active[df_st_active["Req. status"] == st_status_filter]
                
            if search_st or st_status_filter != "All":
                st.session_state.st_page = 1

            st_cols_to_show = [
                "Req. id", "Req. date", "TTI model", "ORT model", "Req. qty", 
                "SAM Job", "CB/F", "SCP/F", "DR/F", "Item Test", 
                "Start date", "End date", "Test result", "Req. duration", "Req. status"
            ]
            st_cols_exist = [col for col in st_cols_to_show if col in df_st_active.columns]
            
            if "Req. date" in df_st_active.columns:
                df_st_active = df_st_active.sort_values(by="Req. date", ascending=False)
                
            df_st_show = df_st_active[st_cols_exist].reset_index(drop=True)
            df_st_show.index = df_st_show.index + 1  
            
            total_st_items = len(df_st_show)
            total_st_pages = math.ceil(total_st_items / st_items_per_page) if total_st_items > 0 else 1

            if st.session_state.st_page > total_st_pages:
                st.session_state.st_page = total_st_pages
            if st.session_state.st_page < 1:
                st.session_state.st_page = 1

            st_start_idx = (st.session_state.st_page - 1) * st_items_per_page
            st_end_idx = st_start_idx + st_items_per_page
            df_st_page = df_st_show.iloc[st_start_idx:st_end_idx]

            def highlight_status(val):
                val_str = str(val).strip().lower()
                if val_str == "overdue":
                    return 'background-color: #ffe6e6; color: #cc0000; font-weight: bold;'
                elif val_str in ["open", "in testing"]:
                    return 'background-color: #fffacd; color: #b8860b; font-weight: bold;'
                return ''

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
            
            if "Req. status" in df_st_page.columns:
                styled_st_df = styled_st_df.map(highlight_status, subset=["Req. status"])

            st.table(styled_st_df)

            if total_st_pages > 1:
                st_col_first, st_col_prev, st_col_page_num, st_col_next, st_col_last = st.columns([1, 1, 2, 1, 1])

                with st_col_first:
                    if st.button("⏮️ First", key="st_btn_first", disabled=(st.session_state.st_page == 1), use_container_width=True):
                        st.session_state.st_page = 1
                        st.rerun()
                with st_col_prev:
                    if st.button("◀ Prev", key="st_btn_prev", disabled=(st.session_state.st_page == 1), use_container_width=True):
                        st.session_state.st_page -= 1
                        st.rerun()
                with st_col_page_num:
                    st.markdown(f"<div style='text-align: center; padding-top: 8px; font-weight: bold; font-size: 16px;'>Page {st.session_state.st_page} / {total_st_pages}</div>", unsafe_allow_html=True)
                with st_col_next:
                    if st.button("Next ▶", key="st_btn_next", disabled=(st.session_state.st_page == total_st_pages), use_container_width=True):
                        st.session_state.st_page += 1
                        st.rerun()
                with st_col_last:
                    if st.button("Last ⏭️", key="st_btn_last", disabled=(st.session_state.st_page == total_st_pages), use_container_width=True):
                        st.session_state.st_page = total_st_pages
                        st.rerun()
                        
        else:
            st.success("🎉 Excellent! No pending requests found (All are Closed).")
    else:
        st.info("No Request data available.")