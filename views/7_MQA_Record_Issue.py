import streamlit as st
import pandas as pd
from datetime import datetime
from database.db_helper import save_8d_report, update_8d_report, get_mqa_list, get_8d_report_by_id, generate_ncr_no
import textwrap
import streamlit.components.v1 as components

# =========================================================
# HÀM DỌN DẸP BỘ NHỚ (TRÁNH LỖI FORM TRỐNG HOẶC LƯU NHẦM DỮ LIỆU CŨ)
# =========================================================
def clear_form_state():
    keys_to_clear = ["edit_issue_id", "data_loaded", "d1_row_count", "d3_row_count", "d4_row_count", "d5_row_count"]
    for k in list(st.session_state.keys()):
        if k in keys_to_clear or k.startswith(("h_", "d2_", "d1_", "d3_", "d4_", "d5_")):
            del st.session_state[k]

# =========================================================
# HÀM TẠO POPUP A4
# =========================================================
@st.dialog("📄 8D CORRECTIVE ACTION REPORT", width="large")
def show_a4_popup(issue_id):
    report_data = get_8d_report_by_id(issue_id)
    if not report_data:
        st.error("Không tìm thấy dữ liệu báo cáo.")
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
        .a4-table th, .a4-table td {{ border: 1px solid #555; padding: 8px; text-align: left; word-break: break-word; }}
        .a4-table th {{ background-color: #e0e0e0; }}
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

    # NÚT EDIT (KÈM DỌN DẸP BỘ NHỚ TRƯỚC KHI CHUYỂN SANG FORM)
    if st.button("✏️ Edit This Report", use_container_width=True):
        clear_form_state()
        st.session_state.mqa_view_mode = "form"  
        st.session_state.edit_issue_id = issue_id  
        st.rerun()

def render(df_power_tool=None):
    if "mqa_view_mode" not in st.session_state:
        st.session_state.mqa_view_mode = "list"

    # =========================================================
    # CHẾ ĐỘ 1: MÀN HÌNH DANH SÁCH (TRACKING LIST)
    # =========================================================
    if st.session_state.mqa_view_mode == "list":
        st.markdown("<h2 style='color: #EBE600;'>📊 MQA TRACKING LIST</h2>", unsafe_allow_html=True)
        col_title, col_btn = st.columns([8, 2])
        with col_title:
            st.markdown("<p style='color: gray;'>Giám sát và quản lý toàn bộ hệ thống sự cố chất lượng</p>", unsafe_allow_html=True)
        with col_btn:
            if st.button("➕ Record New Issue", type="primary", use_container_width=True):
                clear_form_state()
                st.session_state.mqa_view_mode = "form"
                st.rerun()
                
        st.divider()
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1: st.selectbox("Status", ["All", "Open", "Closed"])
        with f_col2: st.date_input("Date Range", [])
        with f_col3: st.selectbox("Model", ["All", "Model A", "Model B"])
        with f_col4: st.selectbox("Owner (PIC)", ["All", "Richard", "John Doe"])
        
        st.markdown("<br><b>Danh sách Báo cáo 8D</b>", unsafe_allow_html=True)
        issues_list = get_mqa_list()
        
        if not issues_list:
            st.markdown("<p style='text-align: center; color: gray;'>Chưa có báo cáo nào trong hệ thống.</p>", unsafe_allow_html=True)
        else:
            df_raw = pd.DataFrame(issues_list)
            if 'date_opened' in df_raw.columns:
                valid_dates = pd.to_datetime(df_raw['date_opened'], errors='coerce')
                df_raw['Open duration'] = (pd.Timestamp.now().normalize() - valid_dates.dt.normalize()).dt.days
            else:
                df_raw['Open duration'] = 0

            rename_dict = {
                "report_no": "Report No.",  
                "date_opened": "Date opened",
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
            cols_to_show = ["Report No.", "Date opened", "Leader: (MQA)", "Issue desc.", "Mfg source", "Sensor", "Line", "Shift", "Issue date", "TTI Model", "Customer Model", "Master category", "Root cause", "Severity", "Open duration"]

            for col in cols_to_show:
                if col not in df_mapped.columns: df_mapped[col] = "N/A"

            df_display = df_mapped[cols_to_show].copy()
            df_display.insert(0, "View", "👁️")
            df_display.insert(1, "No.", range(1, len(df_display) + 1))

            event = st.dataframe(df_display, use_container_width=True, hide_index=True, selection_mode="single-row", on_select="rerun", key="mqa_tracking_table")
            selected_rows = event.selection.get("rows", [])
            if selected_rows:
                idx = selected_rows[0]
                selected_issue_id = df_raw.iloc[idx]["id"] 
                show_a4_popup(selected_issue_id)
                
    # =========================================================
    # CHẾ ĐỘ 2: MÀN HÌNH NHẬP LIỆU (RECORD ISSUE FORM)
    # =========================================================
    elif st.session_state.mqa_view_mode == "form":
        
        col_back, _ = st.columns([2, 8])
        with col_back:
            if st.button("⬅️ Back to Tracking List", use_container_width=True):
                clear_form_state()
                st.session_state.mqa_view_mode = "list"
                st.rerun()

        # --- LOGIC BƠM DỮ LIỆU ĐÃ ĐƯỢC CHUẨN HÓA ---
        is_edit_mode = "edit_issue_id" in st.session_state
        if is_edit_mode and "data_loaded" not in st.session_state:
            old_data = get_8d_report_by_id(st.session_state.edit_issue_id)
            if old_data:
                main = old_data.get("main", {})
                
                # Trả về chuẩn Date object để tránh lỗi Streamlit date_input
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
        .module-header { background-color: #EBE600; color: #000000; padding: 15px 25px; font-size: 35px; font-weight: 800; clip-path: polygon(25px 0, 100% 0, 100% calc(100% - 25px), calc(100% - 25px) 100%, 0 100%, 0 25px); text-transform: uppercase; }
        </style>
        <div class="module-header-wrapper"><div class="module-header">
        <h2 style='text-align: center; color: #000000; background-color: #EBE600; padding: 10px; margin: 0;'>⚡ RECORD ISSUE</h2>
        </div></div>
        """, unsafe_allow_html=True)
        st.divider()

        # --- 1. HEADER ---
        with st.expander("⚡️ HEADER: GENERAL INFORMATION", expanded=True):
            # Chia làm 3 cột để nhét thêm Status
            col1, col2, col3 = st.columns([1.5, 1.5, 1])
            with col1:
                # Nếu là tạo mới và chưa có mã, gọi hàm sinh mã tự động
                if "h_report_no" not in st.session_state or not st.session_state.h_report_no:
                    st.session_state.h_report_no = generate_ncr_no()
                # Khóa cứng (disabled=True) không cho sửa
                st.text_input("Report No.", key="h_report_no", disabled=True)
            with col2:
                if "h_date_opened" not in st.session_state:
                    st.session_state.h_date_opened = datetime.now().date()
                st.date_input("Date opened", key="h_date_opened")
            with col3:
                # Thêm trường Status
                if "h_status" not in st.session_state:
                    st.session_state.h_status = "Open"
                st.selectbox("Status", ["Open", "In Progress", "Closed", "Cancelled"], key="h_status")

        # --- 2. D1: FTT ---
        with st.expander("⚡️ D1: FTT (Form The Team)", expanded=True):
            st.markdown("**Team Members:**")
            
            if "d1_row_count" not in st.session_state:
                st.session_state.d1_row_count = 5
                default_depts = ["MQA", "PE", "ME", "SQE", "PDN"]
                for i, dept in enumerate(default_depts):
                    st.session_state[f"d1_dept_{i}"] = dept
                    st.session_state[f"d1_role_{i}"] = "Leader" if dept == "MQA" else "Member"
                    st.session_state[f"d1_pic_{i}"] = "Unassigned" 
                
            dept_list = ["IPQC", "OQC", "MQA", "PE", "ME", "SQE", "PDN", "APE", "QE", "NPI", "PC", "MC", "MPS", "MPM"]
            role_list = ["Leader", "Member", "Observer"]
            pic_list = ["Unassigned", "Richard", "John Doe", "Jane Smith"]

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
            btn_col1, btn_col2, _ = st.columns([1.5, 1.5, 3])
            with btn_col1:
                if st.button("➕ Add Member", use_container_width=True):
                    st.session_state.d1_row_count += 1
                    st.rerun()
            with btn_col2:
                if st.button("➖ Remove Last Row", use_container_width=True) and st.session_state.d1_row_count > 1:
                    st.session_state.d1_row_count -= 1
                    st.rerun()

        # --- 3. D2: DTP ---
        with st.expander("⚡️ D2: DTP (Define The Problem)", expanded=True):
            st.markdown("**Problem Definition:**")
            st.text_area("Issue Description", placeholder="Enter the issue description...", height=100, key="d2_desc")
            st.markdown("<hr style='margin-top: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.selectbox("Region", ["Region 1", "Region 2", "Region 3"], key="d2_region")
                st.selectbox("Mfg Source", ["Source A", "Source B", "Source C"], key="d2_source")
                st.selectbox("Sensor", ["Sensor 1", "Sensor 2", "None"], key="d2_sensor")
                st.selectbox("Line", ["Line 1", "Line 2", "Line 3", "Line 4"], key="d2_line")
                st.selectbox("Shift", ["Shift 1", "Shift 2", "Shift 3"], key="d2_shift")
                
            with col2:
                inspect_qty = st.number_input("Inspect qty", min_value=0, step=1, key="d2_ins_qty")
                ng_qty = st.number_input("NG qty", min_value=0, step=1, key="d2_ng_qty")
                defect_rate = (ng_qty / inspect_qty * 100) if inspect_qty > 0 else 0.0
                st.text_input("Defect rate", value=f"{defect_rate:.2f} %", disabled=True)
                st.text_input("TTI Model", placeholder="Enter TTI Model", key="d2_tti_model")
                st.text_input("Customer Model", placeholder="Enter Customer Model", key="d2_cus_model")
                
            with col3:
                st.selectbox("Master Category", ["Category A", "Category B"], key="d2_master_cat")
                st.selectbox("Product Categories", ["Product 1", "Product 2", "Product 3"], key="d2_prod_cat")
                if "d2_issue_date" not in st.session_state: st.session_state.d2_issue_date = datetime.now().date()
                st.date_input("Issue Date", key="d2_issue_date")
                st.selectbox("Brand", ["RYOBI", "Milwaukee", "RIDGID", "Hoover"], key="d2_brand")

        # --- 4. D3: ICR ---
        with st.expander("⚡️ D3: Interim Containment Actions", expanded=True):
            if "d3_row_count" not in st.session_state: st.session_state.d3_row_count = 1
            owner_list = ["Unassigned", "Richard", "John Doe", "Jane Smith"]
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
                    st.text_input(f"Justification for ICA-{i+1:02d}", placeholder="⚠️️ Please provide mandatory justification...", key=f"d3_justification_{i}")
                    
            st.markdown('</div>', unsafe_allow_html=True)
            btn_col1, btn_col2, _ = st.columns([1.5, 1.5, 5])
            with btn_col1:
                if st.button("➕ Add Action", key="btn_add_d3", use_container_width=True):
                    st.session_state.d3_row_count += 1
                    st.rerun()
            with btn_col2:
                if st.button("➖ Remove Last", key="btn_rem_d3", use_container_width=True) and st.session_state.d3_row_count > 0:
                    st.session_state.d3_row_count -= 1
                    st.rerun()

        # --- 5. D4: RCA ---
        with st.expander("⚡️ D4: Root Cause Analysis", expanded=True):
            if "d4_row_count" not in st.session_state: st.session_state.d4_row_count = 1
            rc_list = ["Man", "Machine", "Material", "Method", "Measurement", "Environment"]
            fc_list = ["FC-001", "FC-002", "FC-003"]
            fg_list = ["Electrical", "Mechanical", "Cosmetic", "Software"]
            sev_list = ["Critical", "Major", "Minor"]

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
                with c[0]: st.selectbox("Root cause", rc_list, key=f"d4_rc_{i}", label_visibility="collapsed")
                with c[1]: st.text_input("Analysis", placeholder="Brief analysis...", key=f"d4_analysis_{i}", label_visibility="collapsed")
                with c[2]: st.text_input("Issue part", placeholder="Auto...", key=f"d4_part_{i}", disabled=True, label_visibility="collapsed")
                with c[3]: st.text_input("Supplier", placeholder="Auto...", key=f"d4_sup_{i}", disabled=True, label_visibility="collapsed")
                with c[4]: st.selectbox("Failure Code", fc_list, key=f"d4_fc_{i}", label_visibility="collapsed")
                with c[5]: st.selectbox("Failure Group", fg_list, key=f"d4_fg_{i}", label_visibility="collapsed")
                with c[6]: st.text_input("Failure Mode", placeholder="Auto...", key=f"d4_mode_{i}", disabled=True, label_visibility="collapsed")
                with c[7]: st.selectbox("Severity", sev_list, key=f"d4_sev_{i}", label_visibility="collapsed")
                    
            st.markdown('</div>', unsafe_allow_html=True)
            btn_col1, btn_col2, _ = st.columns([1.5, 1.5, 5])
            with btn_col1:
                if st.button("➕ Add Root Cause", key="btn_add_d4", use_container_width=True):
                    st.session_state.d4_row_count += 1
                    st.rerun()
            with btn_col2:
                if st.button("➖ Remove Last", key="btn_rem_d4", use_container_width=True) and st.session_state.d4_row_count > 1:
                    st.session_state.d4_row_count -= 1
                    st.rerun()

            st.markdown("<hr style='margin-top: 15px; margin-bottom: 15px;'>", unsafe_allow_html=True)
            st.text_input("Analysis Report (Link)", placeholder="Paste OneDrive link here...", key="d4_report_link")

        # --- 6. D5: PCR & VCA ---
        with st.expander("⚡️ D5: Permanent Corrective Action & Verification", expanded=True):
            if "d5_row_count" not in st.session_state: st.session_state.d5_row_count = 1
            owner_list = ["Unassigned", "Richard", "John Doe", "Jane Smith"]
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
                    st.text_input(f"Justification for PCA-{i+1:02d}", placeholder="⚠️ Please provide mandatory justification...", key=f"d5_justification_{i}")
                    
            st.markdown('</div>', unsafe_allow_html=True)
            btn_col1, btn_col2, _ = st.columns([1.5, 1.5, 5])
            with btn_col1:
                if st.button("➕ Add Action", key="btn_add_d5", use_container_width=True):
                    st.session_state.d5_row_count += 1
                    st.rerun()
            with btn_col2:
                if st.button("➖ Remove Last", key="btn_rem_d5", use_container_width=True) and st.session_state.d5_row_count > 0:
                    st.session_state.d5_row_count -= 1
                    st.rerun()

        # --- 7. NÚT LƯU BÁO CÁO VÀ GỌI API ---
        st.markdown("<br>", unsafe_allow_html=True)
        btn_label = "🔄 UPDATE ISSUE REPORT" if is_edit_mode else "💾 SAVE NEW ISSUE REPORT"
        
        if st.button(btn_label, type="primary", use_container_width=True):
            with st.spinner("Đang xử lý dữ liệu..."):
                s = st.session_state
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
                    "status": s.h_status
                }
                d1_list = [{"department": s.get(f"d1_dept_{i}"), "pic_name": s.get(f"d1_pic_{i}"), "role": s.get(f"d1_role_{i}")} for i in range(s.d1_row_count)]
                d3_list = [{"action_code": s.get(f"d3_code_{i}"), "action_desc": s.get(f"d3_action_{i}"), "owner": s.get(f"d3_owner_{i}"), "due_date": str(s.get(f"d3_date_{i}")), "status": s.get(f"d3_status_{i}"), "justification": s.get(f"d3_justification_{i}", "")} for i in range(s.d3_row_count)]
                d4_list = [{"root_cause": s.get(f"d4_rc_{i}"), "failure_analysis": s.get(f"d4_analysis_{i}"), "issue_part": s.get(f"d4_part_{i}", ""), "supplier": s.get(f"d4_sup_{i}", ""), "failure_code": s.get(f"d4_fc_{i}"), "failure_group": s.get(f"d4_fg_{i}"), "failure_mode": s.get(f"d4_mode_{i}", ""), "severity": s.get(f"d4_sev_{i}")} for i in range(s.d4_row_count)]
                d5_list = [{"action_code": s.get(f"d5_code_{i}"), "action_desc": s.get(f"d5_action_{i}"), "owner": s.get(f"d5_owner_{i}"), "due_date": str(s.get(f"d5_date_{i}")), "status": s.get(f"d5_status_{i}"), "validate_status": s.get(f"d5_val_status_{i}"), "validate_date": str(s.get(f"d5_val_date_{i}")), "justification": s.get(f"d5_justification_{i}", "")} for i in range(s.d5_row_count)]

                if is_edit_mode:
                    success, msg = update_8d_report(s.edit_issue_id, main_data, d1_list, d3_list, d4_list, d5_list)
                else:
                    success, msg = save_8d_report(main_data, d1_list, d3_list, d4_list, d5_list)
                
                if success:
                    st.success(f"✅ Đã xử lý thành công! (Supabase ID: {msg})")
                    clear_form_state()
                    st.session_state.mqa_view_mode = "list"
                    st.rerun()
                else:
                    st.error(f"❌ Lỗi khi xử lý báo cáo: {msg}")