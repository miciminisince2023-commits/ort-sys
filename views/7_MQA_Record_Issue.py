import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_helper import save_8d_report, update_8d_report, get_mqa_list, get_8d_report_by_id, generate_ncr_no, get_setting_dropdowns
import textwrap
import streamlit.components.v1 as components
from logic.failure_logic import get_failure_mapping
from database.ui_helper import show_loader, hide_loader, set_goku_background
import numpy as np
from logic.sku_converter import convert_tti_to_ort
from database.db_helper import get_setting_prefix

# =========================================================
# CLEAR FORM STATE (PREVENT CACHING ISSUES)
# =========================================================
def clear_form_state():
    keys_to_clear = ["edit_issue_id", "data_loaded", "d1_row_count", "d3_row_count", "d4_row_count", "d5_row_count"]
    for k in list(st.session_state.keys()):
        if k in keys_to_clear or k.startswith(("h_", "d2_", "d1_", "d3_", "d4_", "d5_")):
            del st.session_state[k]

# =========================================================
# A4 REPORT POPUP
# =========================================================
@st.dialog("8D CORRECTIVE ACTION REPORT", width="large")
def show_a4_popup(issue_id):
    report_data = get_8d_report_by_id(issue_id)
    if not report_data:
        st.error("Report data not found.")
        return
        
    main = report_data["main"]
    d1 = report_data["d1"]
    d3 = report_data["d3"]
    d4 = report_data["d4"]
    d5 = report_data["d5"]
    
    ins = main.get('inspect_qty', 0)
    ng = main.get('ng_qty', 0)
    rate = f"{(ng/ins)*100:.2f}%" if ins > 0 else "0%"

    d1_html = "".join([f"<tr><td>{r.get('department','')}</td><td>{r.get('pic_name','')}</td><td>{r.get('role','')}</td></tr>" for r in d1])
    d3_html = "".join([f"<tr><td>{r.get('action_code','')}</td><td>{r.get('action_desc','')}</td><td>{r.get('owner','')}</td><td>{r.get('due_date','')}</td><td>{r.get('status','')}</td></tr>" for r in d3])
    d4_html = "".join([f"<tr><td>{r.get('root_cause','')}</td><td>{r.get('failure_analysis','')}</td><td>{r.get('issue_part','')}</td><td>{r.get('supplier','')}</td><td>{r.get('failure_code','')}</td><td>{r.get('failure_group','')}</td><td>{r.get('severity','')}</td></tr>" for r in d4])
    d5_html = "".join([f"<tr><td>{r.get('action_code','')}</td><td>{r.get('action_desc','')}</td><td>{r.get('owner','')}</td><td>{r.get('due_date','')}</td><td>{r.get('status','')}</td><td>{r.get('validate_status','')}</td><td>{r.get('validate_date','')}</td></tr>" for r in d5])
    
    report_link = main.get('analysis_report_link', '')
    link_html = f'<a href="{report_link}" target="_blank" style="color: #0066cc;">{report_link}</a>' if report_link else "N/A"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ margin: 0; padding: 10px; background-color: #f4f4f4; }}
        .a4-container {{ background-color: white; color: black; padding: 40px; font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; box-shadow: 0 0 10px rgba(0,0,0,0.1); border: 1px solid #ddd; max-width: 800px; margin: 0 auto; pointer-events: none; user-select: none; }}
        .a4-container a {{ pointer-events: auto; }} 
        .a4-title {{ text-align: center; font-size: 22px; font-weight: 900; margin-bottom: 20px; }}
        .a4-section {{ font-weight: bold; font-size: 15px; background-color: #f0f0f0; padding: 8px; margin-top: 20px; border-left: 5px solid #EBE600; text-transform: uppercase; }}
        .a4-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        .a4-table th, .a4-table td {{ border: 1px solid #555; padding: 8px; text-align: left; vertical-align: top; }}
        .a4-table td {{ word-break: break-word; }} 
        .a4-table th {{ background-color: #e0e0e0; white-space: nowrap; }} 
    </style>
    </head>
    <body>
        <div class="a4-container">
            <div class="a4-title">8D REPORT: {main.get('report_no', '')}</div>
            <div class="a4-section">General Information</div>
            <table class="a4-table">
                <tr><th>Issue Date</th><td>{main.get('issue_date', '')}</td><th>TTI Model</th><td>{main.get('tti_model', '')}</td></tr>
                <tr><th>Inspect Qty</th><td>{ins}</td><th>Defect Rate</th><td>{rate}</td></tr>
                <tr><th>Description</th><td colspan="3">{main.get('issue_description', '')}</td></tr>
            </table>
            <div class="a4-section">D1: Team Members</div>
            <table class="a4-table"><tr><th>Department</th><th>PIC Name</th><th>Role</th></tr>{d1_html}</table>
            <div class="a4-section">D3: Interim Containment Actions</div>
            <table class="a4-table"><tr><th>Code</th><th>Action Description</th><th>Owner</th><th>Due Date</th><th>Status</th></tr>{d3_html}</table>
            <div class="a4-section">D4: Root Cause Analysis</div>
            <table class="a4-table"><tr><th>Root Cause</th><th>Analysis</th><th>Issue Part</th><th>Supplier</th><th>F. Code</th><th>F. Group</th><th>Severity</th></tr>{d4_html}</table>
            <div class="a4-section">D5: Permanent Corrective Action & Verification</div>
            <table class="a4-table"><tr><th>Code</th><th>Action Description</th><th>Owner</th><th>Due Date</th><th>Status</th><th>Validate</th><th>Val. Date</th></tr>{d5_html}</table>
            <div class="a4-section">Analysis Report Link</div>
            <div style="padding: 10px; border: 1px solid #555; margin-top: 10px;">{link_html}</div>
            <p style="text-align: right; margin-top: 30px; font-style: italic;">Generated by ORT System</p>
        </div>
    </body>
    </html>
    """
    components.html(html_content, height=750, scrolling=True)

    if st.button("Edit This Report", use_container_width=True):
        clear_form_state()
        st.session_state.mqa_view_mode = "form"  
        st.session_state.edit_issue_id = issue_id  
        st.rerun()

def render(df_power_tool=None):
    set_goku_background()
    if "mqa_view_mode" not in st.session_state:
        st.session_state.mqa_view_mode = "list"

    if "mqa_page_size" not in st.session_state:
        st.session_state.mqa_page_size = 10
    if "mqa_current_page" not in st.session_state:
        st.session_state.mqa_current_page = 1

    # =========================================================
    # VIEW MODE 1: TRACKING LIST
    # =========================================================
    if st.session_state.mqa_view_mode == "list":
        run_id = show_loader(sub_text="Loading Tracking List...")
        st.markdown("""
<style>
.module-header-wrapper {
    filter: drop-shadow(4px 4px 0px rgba(0, 0, 0, 0.2));
    margin-bottom: 25px;
    margin-top: 30px;
}

.module-header {
    background-color: #000000;
    color: #FFFFFF;
    padding: 15px 25px;
    font-size: 35px;
    font-weight: 800; 
    text-transform: uppercase;
}
</style>
<div class="module-header-wrapper">
    <div class="module-header">
    <h2 style='text-align: center; color: #FFFFFF; background-color: #000000; padding: 0px;'>
            T R A C K I N G - L I S T
</h2></div>
</div>
""", unsafe_allow_html=True)

        col_title, col_btn = st.columns([8, 2])
        with col_title:
            st.markdown("<p style='color: gray;'>Monitor and manage the entire quality issue management system.</p>", unsafe_allow_html=True)
        with col_btn:
            if st.button("Record New Issue", type="primary", use_container_width=True):
                clear_form_state()
                st.session_state.mqa_view_mode = "form"
                st.rerun()
                
        # =======================================================
        # 1. BỘ LỌC DỮ LIỆU (FILTERS) SỬ DỤNG ST.FORM
        # =======================================================
        st.markdown("""
        <style>
        .stSelectbox label { font-weight: bold !important; color: #000000 !important; }
        /* Tùy biến nút Filter */
        .filter-btn-container {
            display: flex;
            align-items: flex-end;
            height: 100%;
            padding-bottom: 2px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown("<br><b>8D Report List</b>", unsafe_allow_html=True)
        issues_list = get_mqa_list()
        
        if not issues_list:
            st.markdown("<p style='text-align: center; color: gray;'>No reports found in the system.</p>", unsafe_allow_html=True)
        else:
            df_raw = pd.DataFrame(issues_list)
            
            # --- TÍNH TOÁN OPEN DURATION TRƯỚC KHI LỌC ---
            if 'date_opened' in df_raw.columns:
                valid_opened = pd.to_datetime(df_raw['date_opened'], errors='coerce').dt.normalize()
                end_dates = pd.Series(pd.Timestamp.now().normalize(), index=df_raw.index)
                
                if 'date_closed' in df_raw.columns and 'status' in df_raw.columns:
                    valid_closed = pd.to_datetime(df_raw['date_closed'], errors='coerce').dt.normalize()
                    closed_mask = df_raw['status'] == 'Closed'
                    end_dates = np.where(closed_mask & valid_closed.notna(), valid_closed, end_dates)
                    
                df_raw['Open duration'] = (pd.to_datetime(end_dates) - valid_opened).dt.days
            else:
                df_raw['Open duration'] = 0

            # --- RENAME VÀ CHUẨN BỊ BẢNG MAPPED ---
            rename_dict = {
                "report_no": "Report No.",  
                "date_opened": "Date opened",
                "date_closed": "Date closed",  
                "status": "Status",
                "issue_description": "Issue desc.",
                "mfg_source": "Mfg source",
                "sensor": "Sensor",
                "line": "Line",
                "shift": "Shift",
                "issue_date": "Issue date",
                "tti_model": "TTI Model",
                "customer_model": "Customer Model",
                "master_category": "Master category",
                "leader_mqa": "Leader: (MQA)",   
                "root_cause": "Root cause",      
                "severity": "Severity"           
            }
            df_mapped = df_raw.rename(columns=rename_dict)
            cols_to_show = ["Report No.", "Date opened", "Date closed", "Status", "Leader: (MQA)", "Issue desc.", "Mfg source", "Sensor", "Line", "Shift", "Issue date", "TTI Model", "Customer Model", "Master category", "Root cause", "Severity", "Open duration"]

            for col in cols_to_show:
                if col not in df_mapped.columns: df_mapped[col] = "N/A"

            def get_unique_list(df, col_name):
                if col_name in df.columns:
                    return ["All"] + sorted([str(x) for x in df[col_name].unique() if pd.notna(x) and str(x).strip() != ""])
                return ["All"]

            # --- RENDER BỘ LỌC TRONG FORM ĐỂ TRÁNH RERUN LIÊN TỤC ---
            with st.form("filter_form"):
                # Chia làm 7 cột: 6 cột cho Filters và 1 cột cuối cùng cho nút Filter
                f_col1, f_col2, f_col3, f_col4, f_col5, f_col6, f_btn = st.columns([1, 1, 1, 1, 1, 1, 0.8])
                
                with f_col1: 
                    f_leader = st.selectbox("Leader", get_unique_list(df_mapped, "Leader: (MQA)"))
                with f_col2: 
                    f_status = st.selectbox("Status", ["All", "Open", "In Progress", "Closed", "Cancelled"])
                with f_col3: 
                    f_mfg = st.selectbox("Mfg source", get_unique_list(df_mapped, "Mfg source"))
                with f_col4: 
                    f_sensor = st.selectbox("Sensor", get_unique_list(df_mapped, "Sensor"))
                with f_col5: 
                    f_master = st.selectbox("Master category", get_unique_list(df_mapped, "Master category"))
                with f_col6: 
                    f_root = st.selectbox("Root cause", get_unique_list(df_mapped, "Root cause"))
                    
                with f_btn:
                    # Khoảng đệm vô hình ép cứng chiều cao bằng đúng nhãn (label) của Selectbox
                    st.markdown("<div style='height: 27.5px;'></div>", unsafe_allow_html=True)
                    
                    # Nút submit của form
                    filter_submitted = st.form_submit_button("🔍 Filter", type="primary", use_container_width=True)

            # =======================================================
            # 2. LOGIC THỰC THI LỌC DỮ LIỆU
            # =======================================================
            df_display = df_mapped[cols_to_show].copy()

            # Lọc dữ liệu dựa trên lựa chọn (Chỉ kích hoạt giá trị mới khi nhấn nút Filter)
            if f_leader != "All":
                df_display = df_display[df_display["Leader: (MQA)"] == f_leader]
            if f_status != "All":
                df_display = df_display[df_display["Status"] == f_status]
            if f_mfg != "All":
                df_display = df_display[df_display["Mfg source"] == f_mfg]
            if f_sensor != "All":
                df_display = df_display[df_display["Sensor"] == f_sensor]
            if f_master != "All":
                df_display = df_display[df_display["Master category"] == f_master]
            if f_root != "All":
                df_display = df_display[df_display["Root cause"] == f_root]

            df_display.insert(0, "View", "View")
            df_display.insert(1, "No.", range(1, len(df_display) + 1))

            # =======================================================
            # 3. TÍNH TOÁN PHÂN TRANG DỰA TRÊN DỮ LIỆU ĐÃ LỌC
            # =======================================================
            if df_display.empty:
                st.info("No data matches the selected filters.")
            else:
                total_rows = len(df_display)
                total_pages = (total_rows - 1) // st.session_state.mqa_page_size + 1
                
                if st.session_state.mqa_current_page > total_pages: st.session_state.mqa_current_page = total_pages
                if st.session_state.mqa_current_page < 1: st.session_state.mqa_current_page = 1
                    
                start_idx = (st.session_state.mqa_current_page - 1) * st.session_state.mqa_page_size
                end_idx = start_idx + st.session_state.mqa_page_size
                df_paged = df_display.iloc[start_idx:end_idx]

                # =======================================================
                # 2. THANH CÔNG CỤ TRÊN CÙNG (CHỌN BÁO CÁO & SỐ DÒNG HIỂN THỊ)
                # =======================================================
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Chia cột cho dải công cụ trên cùng
                col_tot, c_limit, col_sel, col_btn = st.columns([4, 1.5, 1.5, 1.5])
                
                with col_tot:
                    st.markdown(f"<div style='margin-top: 5px; font-weight: bold; font-size: 16px;'>Total records: <span style='background-color: #EBE600; padding: 2px 8px; border-radius: 4px; color: black;'>{total_rows}</span></div>", unsafe_allow_html=True)
                
                with c_limit:
                    new_size = st.selectbox("Rows", options=[10, 20, 30, 40], index=[10, 20, 30, 40].index(st.session_state.mqa_page_size), label_visibility="collapsed")
                    if new_size != st.session_state.mqa_page_size:
                        st.session_state.mqa_page_size = new_size
                        st.session_state.mqa_current_page = 1
                        st.rerun()

                with col_sel:
                    report_list = df_display["Report No."].tolist()
                    selected_report = st.selectbox("Select Report", report_list, label_visibility="collapsed")

                with col_btn:
                    if st.button("View This Report", type="primary", use_container_width=True):
                        match_row = df_raw[df_raw["report_no"] == selected_report]
                        if not match_row.empty:
                            issue_id = match_row.iloc[0]["id"]
                            show_a4_popup(issue_id)

                # =======================================================
                # 3. DỰNG BẢNG HTML/CSS THUẦN CHUẨN DESIGN
                # =======================================================
                html_table = """
                <style>
                .mqa-border-box {
                    width: 100%;
                    background-color: #000000; 
                    padding: 1px; 
                    
                    margin-bottom: 15px;
                    margin-top: 5px;
                }
                .mqa-inner-box {
                    width: 100%;
                    background-color: white;
                    overflow-x: auto; 
                    
                }
                .mqa-custom-table {
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 13px;
                    text-align: center;
                    background-color: white;
                    white-space: nowrap; 
                }
                .mqa-custom-table th {
                    background-color: #000000;
                    color: white;
                    padding: 12px 15px;
                    border: 1px solid #333;
                    font-weight: 900;
                }
                .mqa-custom-table td {
                    padding: 10px 15px;
                    border: 1px solid #ddd;
                    color: #333;
                }
                .sev-critical { background-color: #cc0000 !important; color: white !important; font-weight: bold; }
                .sev-major { background-color: #ffaa00 !important; color: black !important; font-weight: bold; }
                .sev-minor { background-color: #f0f0f0 !important; color: black !important; }
                .duration-alert { color: red !important; font-weight: bold; }
                </style>
                <div class="mqa-border-box">
                    <div class="mqa-inner-box">
                        <table class="mqa-custom-table">
                            <thead>
                                <tr>
                                    <th>Report No.</th><th>Date opened</th><th>Date closed</th><th>Status</th><th>Leader (MQA)</th>
                                    <th>Issue desc.</th><th>Mfg source</th><th>Sensor</th>
                                    <th>Line</th><th>Shift</th><th>Issue date</th>
                                    <th>TTI Model</th><th>Customer Model</th><th>Master category</th>
                                    <th>Root cause</th><th>Severity</th><th>Open duration</th>
                                </tr>
                            </thead>
                            <tbody>
                """
                
                for _, row in df_paged.iterrows():
                    sev = str(row['Severity'])
                    if sev == "Critical": sev_class = "sev-critical"
                    elif sev == "Major": sev_class = "sev-major"
                    else: sev_class = "sev-minor"
                    
                    duration = row['Open duration']
                    dur_class = "duration-alert" if isinstance(duration, (int, float)) and duration > 14 else ""
                    
                    val_closed = row.get('Date closed')
                    if pd.isna(val_closed) or str(val_closed).strip() == "" or "NaT" in str(val_closed):
                        date_closed_str = "-"
                    else:
                        date_closed_str = str(val_closed)[:10] 
                    
                    status_val = str(row.get('Status', 'Open'))
                    if status_val == "Closed": status_color = "#28a745" 
                    elif status_val == "In Progress": status_color = "#fd7e14" 
                    elif status_val == "Cancelled": status_color = "#6c757d" 
                    else: status_color = "#dc3545" 
                    status_html = f"<span style='color: {status_color}; font-weight: bold;'>{status_val}</span>"

                    html_table += "<tr>"
                    html_table += f"<td style='font-weight: bold;'>{row['Report No.']}</td>"
                    html_table += f"<td>{row['Date opened']}</td>"
                    html_table += f"<td>{date_closed_str}</td>"
                    html_table += f"<td>{status_html}</td>"
                    html_table += f"<td>{row['Leader: (MQA)']}</td>"
                    html_table += f"<td>{row['Issue desc.']}</td><td>{row['Mfg source']}</td>"
                    html_table += f"<td>{row['Sensor']}</td><td>{row['Line']}</td>"
                    html_table += f"<td>{row['Shift']}</td><td>{row['Issue date']}</td>"
                    html_table += f"<td>{row['TTI Model']}</td><td>{row['Customer Model']}</td>"
                    html_table += f"<td>{row['Master category']}</td><td>{row['Root cause']}</td>"
                    html_table += f"<td class='{sev_class}'>{sev}</td>"
                    html_table += f"<td class='{dur_class}'>{duration}</td>"
                    html_table += "</tr>"
                
                html_table += "</tbody></table></div></div>"
                
                try:
                    st.html(html_table)
                except AttributeError:
                    st.write(html_table, unsafe_allow_html=True)

                # =======================================================
                # 4. THANH ĐIỀU HƯỚNG DƯỚI CÙNG (PHÂN TRANG)
                # =======================================================
                c_space1, c_first, c_prev, c_info, c_next, c_last, c_space2 = st.columns([1, 1.5, 1.5, 2, 1.5, 1.5, 1])
                
                with c_first:
                    if st.button("First", disabled=(st.session_state.mqa_current_page == 1), use_container_width=True):
                        st.session_state.mqa_current_page = 1
                        st.rerun()
                with c_prev:
                    if st.button("Prev", disabled=(st.session_state.mqa_current_page == 1), use_container_width=True):
                        st.session_state.mqa_current_page -= 1
                        st.rerun()
                with c_info:
                    st.markdown(f"<div style='text-align: center; margin-top: 5px; font-weight: 900;'>Page {st.session_state.mqa_current_page} of {total_pages}</div>", unsafe_allow_html=True)
                with c_next:
                    if st.button("Next", disabled=(st.session_state.mqa_current_page == total_pages), use_container_width=True):
                        st.session_state.mqa_current_page += 1
                        st.rerun()
                with c_last:
                    if st.button("Last", disabled=(st.session_state.mqa_current_page == total_pages), use_container_width=True):
                        st.session_state.mqa_current_page = total_pages
                        st.rerun()
        
        hide_loader(run_id=run_id)

    # =========================================================
    # VIEW MODE 2: RECORD ISSUE FORM
    # =========================================================
    elif st.session_state.mqa_view_mode == "form":
        
        col_back, _ = st.columns([2, 8])
        with col_back:
            if st.button("Back to Tracking List", use_container_width=True):
                clear_form_state()
                st.session_state.mqa_view_mode = "list"
                st.rerun()

        # --- DATA PREPARATION FOR EDIT MODE ---
        is_edit_mode = "edit_issue_id" in st.session_state
        if is_edit_mode and "data_loaded" not in st.session_state:
            old_data = get_8d_report_by_id(st.session_state.edit_issue_id)
            if old_data:
                main = old_data.get("main", {})
                
                def parse_date(d_str):
                    try: return datetime.strptime(str(d_str)[:10], '%Y-%m-%d').date()
                    except: return datetime.now().date()

                st.session_state.h_status = main.get("status", "Open")
                st.session_state.h_report_no = main.get("report_no", "")
                st.session_state.h_date_opened = parse_date(main.get("date_opened", ""))
                st.session_state.d2_desc = main.get("issue_description", "")
                st.session_state.d2_region = main.get("region", "Region 1")
                st.session_state.d2_source = main.get("mfg_source", "Source A")
                st.session_state.d2_sensor = main.get("sensor", "None")
                st.session_state.d2_line = main.get("line", "Line 1")
                st.session_state.d2_shift = main.get("shift", "Shift 1")
                st.session_state.d2_ins_qty = int(main.get("inspect_qty", 0))
                st.session_state.d2_ng_qty = int(main.get("ng_qty", 0))
                st.session_state.d2_tti_model = main.get("tti_model", "")
                st.session_state.d2_cus_model = main.get("customer_model", "")
                st.session_state.d2_brand = main.get("brand", "RYOBI")
                st.session_state.d2_master_cat = main.get("master_category", "Category A")
                st.session_state.d2_prod_cat = main.get("product_category", "Product 1")
                st.session_state.d2_issue_date = parse_date(main.get("issue_date", ""))
                st.session_state.d4_report_link = main.get("analysis_report_link", "")

                d1 = old_data.get("d1", [])
                st.session_state.d1_row_count = len(d1) if d1 else 1
                for i, row in enumerate(d1):
                    st.session_state[f"d1_dept_{i}"] = row.get("department", "MQA")
                    st.session_state[f"d1_pic_{i}"] = row.get("pic_name", "Unassigned")
                    st.session_state[f"d1_role_{i}"] = row.get("role", "Member")

                d3 = old_data.get("d3", [])
                st.session_state.d3_row_count = len(d3) if d3 else 1
                for i, row in enumerate(d3):
                    st.session_state[f"d3_code_{i}"] = row.get("action_code", f"ICA-{i+1:02d}")
                    st.session_state[f"d3_action_{i}"] = row.get("action_desc", "")
                    st.session_state[f"d3_owner_{i}"] = row.get("owner", "Unassigned")
                    st.session_state[f"d3_date_{i}"] = parse_date(row.get("due_date", ""))
                    st.session_state[f"d3_status_{i}"] = row.get("status", "Open")
                    st.session_state[f"d3_justification_{i}"] = row.get("justification", "")

                d4 = old_data.get("d4", [])
                st.session_state.d4_row_count = len(d4) if d4 else 1
                for i, row in enumerate(d4):
                    st.session_state[f"d4_rc_{i}"] = row.get("root_cause", "Man")
                    st.session_state[f"d4_analysis_{i}"] = row.get("failure_analysis", "")
                    st.session_state[f"d4_part_{i}"] = row.get("issue_part", "")
                    st.session_state[f"d4_sup_{i}"] = row.get("supplier", "")
                    st.session_state[f"d4_fc_{i}"] = row.get("failure_code", "FC-001")
                    st.session_state[f"d4_fg_{i}"] = row.get("failure_group", "Electrical")
                    st.session_state[f"d4_mode_{i}"] = row.get("failure_mode", "")
                    st.session_state[f"d4_sev_{i}"] = row.get("severity", "Minor")

                d5 = old_data.get("d5", [])
                st.session_state.d5_row_count = len(d5) if d5 else 1
                for i, row in enumerate(d5):
                    st.session_state[f"d5_code_{i}"] = row.get("action_code", f"PCA-{i+1:02d}")
                    st.session_state[f"d5_action_{i}"] = row.get("action_desc", "")
                    st.session_state[f"d5_owner_{i}"] = row.get("owner", "Unassigned")
                    st.session_state[f"d5_date_{i}"] = parse_date(row.get("due_date", ""))
                    st.session_state[f"d5_status_{i}"] = row.get("status", "Open")
                    st.session_state[f"d5_val_status_{i}"] = row.get("validate_status", "Pending")
                    st.session_state[f"d5_val_date_{i}"] = parse_date(row.get("validate_date", ""))
                    st.session_state[f"d5_justification_{i}"] = row.get("justification", "")
                
            st.session_state.data_loaded = True 
            st.rerun()

        st.markdown("""
        <style>
        .module-header-wrapper { filter: drop-shadow(4px 4px 0px rgba(0, 0, 0, 0.2)); margin-bottom: 25px; margin-top: 10px; }
        .module-header { background-color: #000000; color: #FFFFFF; padding: 15px 25px; font-size: 35px; font-weight: 800; text-transform: uppercase; }
        </style>
        <div class="module-header-wrapper"><div class="module-header">
        <h2 style='text-align: center; color: #FFFFFF; background-color: #000000; padding: 0px; margin: 0;'>R E C O R D - I S S U E</h2>
        </div></div>
        """, unsafe_allow_html=True)
        
        with st.form("mqa_form"):
            # KHAI BÁO TABS NGAY BÊN TRONG FORM
            tab_gen, tab_d2, tab_d3, tab_d4, tab_d5 = st.tabs([
                "GENERAL & D1", 
                "D2: DTP", 
                "D3: ICA", 
                "D4: RCA", 
                "D5: PCA"
            ])
            
            # --- 1. HEADER ---
            with tab_gen:
                st.markdown("### GENERAL INFORMATION")
                col1, col2, col3 = st.columns([1.5, 1.5, 1])
                with col1:
                    if "h_report_no" not in st.session_state or not st.session_state.h_report_no:
                        st.session_state.h_report_no = generate_ncr_no()
                    st.text_input("Report No.", key="h_report_no", disabled=True)
                with col2:
                    if "h_date_opened" not in st.session_state:
                        st.session_state.h_date_opened = datetime.now().date()
                    st.date_input("Date opened", key="h_date_opened")
                with col3:
                    if "h_status" not in st.session_state:
                        st.session_state.h_status = "Open"
                    st.selectbox("Status", ["Open", "In Progress", "Closed", "Cancelled"], key="h_status")

            # --- 2. D1: FTT ---
                st.markdown("### D1: FTT (Form The Team)")
                st.markdown("**Team Members:**")
                
                if "d1_row_count" not in st.session_state:
                    st.session_state.d1_row_count = 2
                    default_depts = ["MQA","OQC"]
                    for i, dept in enumerate(default_depts):
                        st.session_state[f"d1_dept_{i}"] = dept
                        st.session_state[f"d1_role_{i}"] = "Leader" if dept == "MQA" else "Member"
                        st.session_state[f"d1_pic_{i}"] = "Unassigned" 
                    
                dept_list = ["IPQC", "OQC", "MQA", "PE", "ME", "SQE", "PDN", "APE", "QE", "NPI", "PC", "MC", "MPS", "MPM"]
                role_list = ["Leader", "Member", "Observer"]
                
                df_pic = get_setting_dropdowns("pic")
                if not df_pic.empty:
                    pic_list = ["Unassigned"] + df_pic["value"].tolist()
                else:
                    pic_list = ["Unassigned"]

                st.markdown('<div class="d1-static-table">', unsafe_allow_html=True)
                h_col1, h_col2, h_col3 = st.columns([1.5, 2.5, 1.5])
                with h_col1: st.markdown("**Department**")
                with h_col2: st.markdown("**PIC Name**")
                with h_col3: st.markdown("**Role**")
                st.markdown("<hr style='margin-top: 0px; margin-bottom: 10px;'>", unsafe_allow_html=True)

                for i in range(st.session_state.d1_row_count):
                    col1, col2, col3 = st.columns([1.5, 2.5, 1.5])
                    with col1: st.selectbox("Dept", dept_list, key=f"d1_dept_{i}", label_visibility="collapsed")
                    with col2: st.selectbox("PIC", pic_list, key=f"d1_pic_{i}", label_visibility="collapsed")
                    with col3: st.selectbox("Role", role_list, key=f"d1_role_{i}", label_visibility="collapsed")
                        
                st.markdown('</div>', unsafe_allow_html=True)

                # ĐƯA NÚT D1 VÀO ĐÂY
                btn_col1, btn_col2, _ = st.columns([1.5, 1.5, 5])
                with btn_col1:
                    if st.form_submit_button("Add Member", use_container_width=True):
                        st.session_state.d1_row_count += 1
                        st.rerun()
                with btn_col2:
                    if st.form_submit_button("Remove Member", use_container_width=True) and st.session_state.d1_row_count > 1:
                        st.session_state.d1_row_count -= 1
                        st.rerun()

            # --- 3. D2: DTP ---
            with tab_d2:
                st.markdown("### D2: DTP (Define The Problem)")
                st.markdown("**Problem Definition:**")
                st.text_area("Issue Description", placeholder="Enter the issue description...", height=100, key="d2_desc")
                st.markdown("<hr style='margin-top: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)
                
                df_region = get_setting_dropdowns("region")
                if not df_region.empty:
                    region_list = df_region["value"].tolist()
                else:
                    region_list = ["Unassigned"]

                df_mfg = get_setting_dropdowns("mfg_source")
                if not df_mfg.empty:
                    mfg_list = df_mfg["value"].tolist()
                else:
                    mfg_list = ["Unassigned"]

                df_sensor = get_setting_dropdowns("sensor")
                if not df_sensor.empty:
                    sensor_list = df_sensor["value"].tolist()
                else:
                    sensor_list = ["None"] 

                df_line = get_setting_dropdowns("line")
                if not df_line.empty:
                    line_list = df_line["value"].tolist()
                else:
                    line_list = ["Unassigned"] 

                df_category = get_setting_dropdowns("category")
                if not df_category.empty:
                    category_list = df_category["value"].tolist()
                else:
                    category_list = ["Unassigned"]

                df_model = get_setting_dropdowns("model_name")
                if not df_model.empty:
                    product_name_list = df_model["value"].tolist()
                else:
                    product_name_list = ["Unassigned"]

                df_brand = get_setting_dropdowns("brand")
                if not df_brand.empty:
                    brand_list = df_brand["value"].tolist()
                else:
                    brand_list = ["RYOBI", "Milwaukee", "RIDGID", "Hoover"] 

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.selectbox("Region", region_list, key="d2_region")
                    st.selectbox("Mfg Source", mfg_list, key="d2_source")
                    st.selectbox("Sensor", sensor_list, key="d2_sensor")
                    st.selectbox("Line", line_list, key="d2_line")
                    st.selectbox("Shift", ["Day", "Night"], key="d2_shift")
                    
                with col2:
                    inspect_qty = st.number_input("Inspect qty", min_value=0, step=1, key="d2_ins_qty")
                    ng_qty = st.number_input("NG qty", min_value=0, step=1, key="d2_ng_qty")
                    defect_rate = (ng_qty / inspect_qty * 100) if inspect_qty > 0 else 0.0
                    st.text_input("Defect rate", value=f"{defect_rate:.2f} %", disabled=True)
                    
                    tti_input = st.text_input("TTI Model", placeholder="Enter TTI Model (e.g., 011321001)", key="d2_tti_model")
                    
                    ort_model_val = ""
                    if tti_input:
                        df_prefix = get_setting_prefix()
                        ort_model_val = convert_tti_to_ort(tti_input, df_prefix)
                    
                    st.text_input("ORT Model (Auto)", value=ort_model_val, key="d2_ort_model", disabled=True)
                    
                    st.text_input("Customer Model", placeholder="Enter Customer Model", key="d2_cus_model")
                    
                with col3:
                    st.selectbox("Master Category", category_list, key="d2_master_cat")
                    st.selectbox("Product name", product_name_list, key="d2_prod_cat")
                    if "d2_issue_date" not in st.session_state: st.session_state.d2_issue_date = datetime.now().date()
                    st.date_input("Issue Date", key="d2_issue_date")
                    st.selectbox("Brand", brand_list, key="d2_brand")

            # --- 4. D3: ICR ---
                with tab_d3:
                    st.markdown("### D3: Interim Containment Actions")
                    if "d3_row_count" not in st.session_state: st.session_state.d3_row_count = 1
                    
                    df_pic = get_setting_dropdowns("pic")
                    if not df_pic.empty:
                        owner_list = ["Unassigned"] + df_pic["value"].tolist()
                    else:
                        owner_list = ["Unassigned"]
                    
                    status_list = ["Open", "In Progress", "Closed", "Cancelled"]

                    st.markdown('<div class="d3-static-table">', unsafe_allow_html=True)
                    h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([1, 3, 1.5, 1.5, 1])
                    with h_col1: st.markdown("**Code**")
                    with h_col2: st.markdown("**Action**")
                    with h_col3: st.markdown("**Owner**")
                    with h_col4: st.markdown("**Due date**")
                    with h_col5: st.markdown("**Status**")
                    st.markdown("<hr style='margin-top: 0px; margin-bottom: 10px;'>", unsafe_allow_html=True)

                    for i in range(st.session_state.d3_row_count):
                        c1, c2, c3, c4, c5 = st.columns([1, 3, 1.5, 1.5, 1])
                        with c1: 
                            if f"d3_code_{i}" not in st.session_state: st.session_state[f"d3_code_{i}"] = f"ICA-{i+1:02d}"
                            st.text_input("Code", key=f"d3_code_{i}", disabled=True, label_visibility="collapsed")
                        with c2: st.text_input("Action", placeholder="Describe action...", key=f"d3_action_{i}", label_visibility="collapsed")
                        with c3: st.selectbox("Owner", owner_list, key=f"d3_owner_{i}", label_visibility="collapsed")
                        with c4: 
                            if f"d3_date_{i}" not in st.session_state: st.session_state[f"d3_date_{i}"] = datetime.now().date()
                            st.date_input("Due date", key=f"d3_date_{i}", label_visibility="collapsed")
                        with c5: 
                            current_status = st.selectbox("Status", status_list, key=f"d3_status_{i}", label_visibility="collapsed")
                        
                        if current_status == "Cancelled":
                            st.text_input(f"Justification for ICA-{i+1:02d}", placeholder="Please provide mandatory justification...", key=f"d3_justification_{i}")
                            
                    st.markdown('</div>', unsafe_allow_html=True)

                    # ĐƯA NÚT D3 VÀO ĐÂY
                    btn_col1, btn_col2, _ = st.columns([1.5, 1.5, 5])
                    with btn_col1:
                        if st.form_submit_button("Add Action (D3)", use_container_width=True):
                            st.session_state.d3_row_count += 1
                            st.rerun()
                    with btn_col2:
                        if st.form_submit_button("Remove Action (D3)", use_container_width=True) and st.session_state.d3_row_count > 0:
                            st.session_state.d3_row_count -= 1
                            st.rerun()

            # --- 5. D4: RCA ---
            with tab_d4:
                st.markdown("### D4: Root Cause Analysis")
                if "d4_row_count" not in st.session_state: st.session_state.d4_row_count = 1
                
                rc_list = ["Man", "Machine", "Material", "Method", "Design", "Under investigation"]
                sev_list = ["Critical", "Major", "Minor"]

                failure_mapping = get_failure_mapping()

                st.markdown('<div class="d4-static-table">', unsafe_allow_html=True)
                col_widths = [1.2, 2.5, 1.2, 1.2, 1.2, 1.2, 1.2, 1.0]
                h_cols = st.columns(col_widths)
                
                with h_cols[0]: st.markdown("**Root cause**")
                with h_cols[1]: st.markdown("**Failure Analysis**")
                with h_cols[2]: st.markdown("**Issue part**")
                with h_cols[3]: st.markdown("**Supplier**")
                with h_cols[4]: st.markdown("**Failure Code**")
                with h_cols[5]: st.markdown("**Failure Group**")
                with h_cols[6]: st.markdown("**Failure Mode**")
                with h_cols[7]: st.markdown("**Severity**")
                st.markdown("<hr style='margin-top: 0px; margin-bottom: 10px;'>", unsafe_allow_html=True)

                for i in range(st.session_state.d4_row_count):
                    c = st.columns(col_widths)
                    
                    with c[0]: 
                        current_rc = st.selectbox("Root cause", rc_list, key=f"d4_rc_{i}", label_visibility="collapsed")
                    
                    mapping_data = failure_mapping.get(current_rc, failure_mapping["Under investigation"])
                    current_fg = mapping_data["group"]
                    fc_list = list(mapping_data["codes"].keys())
                    
                    with c[1]: 
                        st.text_input("Analysis", placeholder="Brief analysis...", key=f"d4_analysis_{i}", label_visibility="collapsed")
                    
                    is_locked = (current_rc != "Material")
                    with c[2]: 
                        st.text_input("Issue part", placeholder="Enter part..." if not is_locked else "Locked...", key=f"d4_part_{i}", disabled=is_locked, label_visibility="collapsed")
                    with c[3]: 
                        st.text_input("Supplier", placeholder="Enter supplier..." if not is_locked else "Locked...", key=f"d4_sup_{i}", disabled=is_locked, label_visibility="collapsed")
                    
                    with c[4]: 
                        current_fc = st.selectbox("Failure Code", fc_list, index=None, placeholder="Select...", key=f"d4_fc_{i}", label_visibility="collapsed")
                    
                    with c[5]: 
                        st.selectbox("Failure Group", [current_fg], key=f"d4_fg_{i}", disabled=True, label_visibility="collapsed")
                    
                    with c[6]: 
                        current_mode = mapping_data["codes"].get(current_fc, "") if current_fc else ""
                        st.session_state[f"d4_mode_{i}"] = current_mode
                        st.text_input("Failure Mode", placeholder="Auto...", key=f"d4_mode_{i}", disabled=True, label_visibility="collapsed")
                        
                    with c[7]: 
                        st.selectbox("Severity", sev_list, key=f"d4_sev_{i}", label_visibility="collapsed")
                        
                st.markdown('</div>', unsafe_allow_html=True)

                st.markdown("<hr style='margin-top: 15px; margin-bottom: 15px;'>", unsafe_allow_html=True)
                st.text_input("Analysis Report (Link)", placeholder="Paste OneDrive link here...", key="d4_report_link")

                # ĐƯA NÚT D4 VÀO ĐÂY
                btn_col1, btn_col2, _ = st.columns([1.5, 1.5, 5])
                with btn_col1:
                    if st.form_submit_button("Add Root Cause", use_container_width=True):
                        st.session_state.d4_row_count += 1
                        st.rerun()
                with btn_col2:
                    if st.form_submit_button("Remove Root Cause", use_container_width=True) and st.session_state.d4_row_count > 1:
                        st.session_state.d4_row_count -= 1
                        st.rerun()

            # --- 6. D5: PCR & VCA ---
            with tab_d5:
                st.markdown("### D5: Permanent Corrective Action & Verification")
                if "d5_row_count" not in st.session_state: st.session_state.d5_row_count = 1
                
                df_pic = get_setting_dropdowns("pic")
                if not df_pic.empty:
                    owner_list = ["Unassigned"] + df_pic["value"].tolist()
                else:
                    owner_list = ["Unassigned"]
                
                status_list = ["Open", "In Progress", "Closed", "Cancelled"]
                validate_list = ["Pending", "Pass", "Fail"] 

                st.markdown('<div class="d5-static-table">', unsafe_allow_html=True)
                col_widths = [0.8, 2.5, 1.2, 1.0, 1.0, 1.0, 1.0]
                h_cols = st.columns(col_widths)
                
                with h_cols[0]: st.markdown("**Code**")
                with h_cols[1]: st.markdown("**Action (PCR)**")
                with h_cols[2]: st.markdown("**Owner**")
                with h_cols[3]: st.markdown("**Due date**")
                with h_cols[4]: st.markdown("**Status**")
                with h_cols[5]: st.markdown("**Validate**")
                with h_cols[6]: st.markdown("**Val. Date**")
                st.markdown("<hr style='margin-top: 0px; margin-bottom: 10px;'>", unsafe_allow_html=True)

                for i in range(st.session_state.d5_row_count):
                    c = st.columns(col_widths)
                    with c[0]: 
                        if f"d5_code_{i}" not in st.session_state: st.session_state[f"d5_code_{i}"] = f"PCA-{i+1:02d}"
                        st.text_input("Code", key=f"d5_code_{i}", disabled=True, label_visibility="collapsed")
                    with c[1]: st.text_input("Action", placeholder="Describe permanent action...", key=f"d5_action_{i}", label_visibility="collapsed")
                    with c[2]: st.selectbox("Owner", owner_list, key=f"d5_owner_{i}", label_visibility="collapsed")
                    with c[3]: 
                        if f"d5_date_{i}" not in st.session_state: st.session_state[f"d5_date_{i}"] = datetime.now().date()
                        st.date_input("Due date", key=f"d5_date_{i}", label_visibility="collapsed")
                    with c[4]: current_status = st.selectbox("Status", status_list, key=f"d5_status_{i}", label_visibility="collapsed")
                    with c[5]: st.selectbox("Validate", validate_list, key=f"d5_val_status_{i}", label_visibility="collapsed")
                    with c[6]: 
                        if f"d5_val_date_{i}" not in st.session_state: st.session_state[f"d5_val_date_{i}"] = datetime.now().date()
                        st.date_input("Val. Date", key=f"d5_val_date_{i}", label_visibility="collapsed")
                    
                    if current_status == "Cancelled":
                        st.text_input(f"Justification for PCA-{i+1:02d}", placeholder="Please provide mandatory justification...", key=f"d5_justification_{i}")
                        
                st.markdown('</div>', unsafe_allow_html=True)

                # ĐƯA NÚT D5 VÀO ĐÂY
                btn_col1, btn_col2, _ = st.columns([1.5, 1.5, 5])
                with btn_col1:
                    if st.form_submit_button("Add Action (D5)", use_container_width=True):
                        st.session_state.d5_row_count += 1
                        st.rerun()
                with btn_col2:
                    if st.form_submit_button("Remove Action (D5)", use_container_width=True) and st.session_state.d5_row_count > 0:
                        st.session_state.d5_row_count -= 1
                        st.rerun()

            # =========================================================
            # LOGIC VALIDATE: CHECK MANDATORY FIELDS BEFORE SAVING
            # =========================================================
            s = st.session_state
            missing_fields = []
            
            if not s.get("d2_desc", "").strip(): missing_fields.append("Issue Description (D2)")
            if not s.get("d2_tti_model", "").strip(): missing_fields.append("TTI Model (D2)")
            if not s.get("d2_cus_model", "").strip(): missing_fields.append("Customer Model (D2)")
            
            for i in range(s.get("d1_row_count", 1)):
                if s.get(f"d1_pic_{i}") == "Unassigned":
                    missing_fields.append(f"PIC Name (D1 - Row {i+1})")
            
            for i in range(s.get("d3_row_count", 1)):
                if not s.get(f"d3_action_{i}", "").strip():
                    missing_fields.append(f"Action (D3 - Row {i+1})")
            
            for i in range(s.get("d4_row_count", 1)):
                if not s.get(f"d4_analysis_{i}", "").strip():
                    missing_fields.append(f"Analysis (D4 - Row {i+1})")
                if not s.get(f"d4_fc_{i}"): 
                    missing_fields.append(f"Failure Code (D4 - Row {i+1})")
            
            for i in range(s.get("d5_row_count", 1)):
                if not s.get(f"d5_action_{i}", "").strip():
                    missing_fields.append(f"Action (D5 - Row {i+1})")

            is_disabled = len(missing_fields) > 0
            
            if is_disabled:
                hover_reason = "PLEASE FILL IN THE FOLLOWING MANDATORY FIELDS:\n\n- " + "\n- ".join(missing_fields)
            else:
                hover_reason = "All fields are valid. Click to save the report!"

            st.markdown("<hr style='margin-top: 30px; margin-bottom: 20px;'>", unsafe_allow_html=True)

            # --- 7. BUTTON SAVE / UPDATE ---
            btn_label = "UPDATE ISSUE REPORT" if is_edit_mode else "SAVE NEW ISSUE REPORT"

            submitted = st.form_submit_button(btn_label, type="primary", disabled=is_disabled, help=hover_reason)

            if submitted:
                run_id = show_loader("Processing data...")
                
                s = st.session_state
                
                current_date_str = str(datetime.now().date())
                closed_date_val = current_date_str if s.h_status == "Closed" else None

                main_data = {
                    "report_no": s.h_report_no,
                    "date_opened": str(s.h_date_opened),
                    "issue_description": s.d2_desc,
                    "region": s.d2_region,
                    "mfg_source": s.d2_source,
                    "sensor": s.d2_sensor,
                    "line": s.d2_line,
                    "shift": s.d2_shift,
                    "inspect_qty": s.d2_ins_qty,
                    "ng_qty": s.d2_ng_qty,
                    "tti_model": s.d2_tti_model,
                    "customer_model": s.d2_cus_model,
                    "brand": s.d2_brand,
                    "master_category": s.d2_master_cat,
                    "product_category": s.d2_prod_cat,
                    "issue_date": str(s.d2_issue_date),
                    "analysis_report_link": s.get("d4_report_link", ""),
                    "status": s.h_status,
                    "date_closed": closed_date_val,
                    "ort_model": s.get("d2_ort_model", "")
                }
    
                d1_list = [{"department": s.get(f"d1_dept_{i}"), "pic_name": s.get(f"d1_pic_{i}"), "role": s.get(f"d1_role_{i}")} for i in range(s.d1_row_count)]
                d3_list = [{"action_code": s.get(f"d3_code_{i}"), "action_desc": s.get(f"d3_action_{i}"), "owner": s.get(f"d3_owner_{i}"), "due_date": str(s.get(f"d3_date_{i}")), "status": s.get(f"d3_status_{i}"), "justification": s.get(f"d3_justification_{i}", "")} for i in range(s.d3_row_count)]
                d4_list = [{"root_cause": s.get(f"d4_rc_{i}"), "failure_analysis": s.get(f"d4_analysis_{i}"), "issue_part": s.get(f"d4_part_{i}", ""), "supplier": s.get(f"d4_sup_{i}", ""), "failure_code": s.get(f"d4_fc_{i}"), "failure_group": s.get(f"d4_fg_{i}"), "failure_mode": s.get(f"d4_mode_{i}", ""), "severity": s.get(f"d4_sev_{i}")} for i in range(s.d4_row_count)]
                d5_list = [{"action_code": s.get(f"d5_code_{i}"), "action_desc": s.get(f"d5_action_{i}"), "owner": s.get(f"d5_owner_{i}"), "due_date": str(s.get(f"d5_date_{i}")), "status": s.get(f"d5_status_{i}"), "validate_status": s.get(f"d5_val_status_{i}"), "validate_date": str(s.get(f"d5_val_date_{i}")), "justification": s.get(f"d5_justification_{i}", "")} for i in range(s.d5_row_count)]

                if is_edit_mode:
                    success, msg = update_8d_report(s.edit_issue_id, main_data, d1_list, d3_list, d4_list, d5_list)
                else:
                    success, msg = save_8d_report(main_data, d1_list, d3_list, d4_list, d5_list)
                
                hide_loader(run_id=run_id)

                if success:
                    st.success(f"Processing successful! (Supabase ID: {msg})")
                    clear_form_state()
                    st.session_state.mqa_view_mode = "list"
                    st.rerun()
                else:
                    st.error(f"Error processing report: {msg}")
