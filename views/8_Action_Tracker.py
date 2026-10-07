import streamlit as st
import pandas as pd
import math
from database.db_helper import get_all_actions, get_8d_report_by_id
import streamlit.components.v1 as components

# =========================================================
# HÀM RESET TRANG KHI ĐỔI BỘ LỌC
# =========================================================
def reset_page():
    st.session_state.at_page = 1

# =========================================================
# TẠO POPUP A4 PHIÊN BẢN CHỈ XEM (READ-ONLY)
# =========================================================
@st.dialog("📄 8D REPORT DETAILS (READ-ONLY)", width="large")
def show_a4_popup_readonly(issue_id):
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
        </div>
    </body>
    </html>
    """
    components.html(html_content, height=750, scrolling=True)

# =========================================================
# HÀM ÉP MÀU CHO PANDAS HTML (XỬ LÝ HÀNG CANCELLED BỊ CHÌM)
# =========================================================
def highlight_action_status_html(row):
    status = str(row['Status']).strip().lower()
    
    base_cell_style = "border: 1px solid #ddd; padding: 10px; text-align: center; vertical-align: middle;"
    
    if status == 'cancelled':
        default_style = f"background-color: #f5f5f5; color: #a0a0a0; font-style: italic; {base_cell_style}"
    else:
        default_style = f"background-color: white; color: black; {base_cell_style}"
        
    styles = [default_style] * len(row)
    
    if 'Status' in row.index:
        status_idx = row.index.get_loc('Status')
        base_status_style = "text-align: center; font-weight: bold; border: 1px solid #ddd; padding: 10px; vertical-align: middle;"
        
        if status == 'cancelled':
            styles[status_idx] = f"background-color: #d9d9d9; color: #7a7a7a; font-style: italic; {base_status_style}"
        elif status == 'in progress' or status == 'inprocess':
            styles[status_idx] = f"background-color: #0056b3; color: white; {base_status_style}"
        elif status == 'open':
            styles[status_idx] = f"background-color: #ffc107; color: black; {base_status_style}"
        elif status == 'closed':
            styles[status_idx] = f"background-color: #28a745; color: white; {base_status_style}"
            
    return styles

# =========================================================
# GIAO DIỆN CHÍNH
# =========================================================
def render(df_power_tool=None):
    if "at_page" not in st.session_state:
        st.session_state.at_page = 1

    st.markdown("""
    <style>
    .module-header-wrapper { filter: drop-shadow(4px 4px 0px rgba(0, 0, 0, 0.2)); margin-bottom: 25px; margin-top: 10px; }
    .module-header { background-color: #EBE600; color: #000000; padding: 15px 25px; font-size: 35px; font-weight: 800; clip-path: polygon(25px 0, 100% 0, 100% calc(100% - 25px), calc(100% - 25px) 100%, 0 100%, 0 25px); text-transform: uppercase; }
    
    .table-shadow-wrapper {
        filter: drop-shadow(-1px 0px 0px #000) 
                drop-shadow(1px 0px 0px #000) 
                drop-shadow(0px -1px 0px #000) 
                drop-shadow(0px 1px 0px #000);
        margin-bottom: 20px;
    }
    
    .custom-table-container {
        clip-path: polygon(25px 0, 100% 0, 100% calc(100% - 25px), calc(100% - 25px) 100%, 0 100%, 0 25px);
        background-color: white;
        overflow-x: auto;
        width: 100%;
    }
    
    .custom-table-container table {
        width: 100% !important; 
        border-collapse: collapse;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<div class='module-header-wrapper'><div class='module-header'><h2 style='text-align: center; color: #000000; background-color: #EBE600; padding: 10px; margin: 0;'>🎯 ACTION TRACKER</h2></div></div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Track and manage the progress of all corrective actions (ICA & PCA)</p>", unsafe_allow_html=True)
    st.divider()

    actions_list = get_all_actions()

    if not actions_list:
        st.info("There are currently no actions in the system.")
    else:
        df_actions = pd.DataFrame(actions_list)
        if 'Due Date' in df_actions.columns:
            df_actions['Due Date'] = pd.to_datetime(df_actions['Due Date'], errors='coerce').dt.date
        
        # --- BỘ LỌC TỰ ĐỘNG TIẾNG ANH ---
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1:
            page_size_option = st.selectbox("Items per page:", [10, 20, 30, "All"], on_change=reset_page)
        with f_col2:
            owner_options = ["All"] + sorted(df_actions["Owner"].dropna().unique().tolist())
            owner_filter = st.selectbox("Filter by PIC", owner_options, on_change=reset_page)
        with f_col3:
            status_filter = st.selectbox("Filter by Status", ["All", "Open", "In Progress", "Closed", "Cancelled"], on_change=reset_page)
        with f_col4:
            type_filter = st.selectbox("Filter by Type", ["All", "ICA (D3)", "PCA (D5)"], on_change=reset_page)
            
        df_filtered = df_actions.copy()
        if owner_filter != "All": df_filtered = df_filtered[df_filtered["Owner"] == owner_filter]
        if status_filter != "All": df_filtered = df_filtered[df_filtered["Status"] == status_filter]
        if type_filter != "All": df_filtered = df_filtered[df_filtered["Action Type"] == type_filter]
        
        total_rows = len(df_filtered)

        # --- XỬ LÝ TOÁN HỌC PHÂN TRANG ---
        if page_size_option == "All":
            rows_per_page = total_rows if total_rows > 0 else 1
        else:
            rows_per_page = int(page_size_option)
            
        total_pages = math.ceil(total_rows / rows_per_page) if total_rows > 0 else 1
        
        if st.session_state.at_page > total_pages:
            st.session_state.at_page = total_pages
        elif st.session_state.at_page < 1:
            st.session_state.at_page = 1
            
        current_page = st.session_state.at_page
        
        start_idx = (current_page - 1) * rows_per_page
        end_idx = start_idx + rows_per_page
        df_page = df_filtered.iloc[start_idx:end_idx]

        # --- THANH TỔNG HỢP & MODULE XEM BÁO CÁO TIẾNG ANH ---
        st.markdown("<br>", unsafe_allow_html=True) 
        col_stat, col_sel, col_btn = st.columns([4, 4, 3])
        
        with col_stat:
            st.markdown(f"<div style='padding-top: 5px; font-size: 16px;'><b>Total actions:</b> <span style='color: black; background: #EBE600; padding: 3px 10px; border-radius: 5px;'>{total_rows}</span></div>", unsafe_allow_html=True)

        unique_reports = df_filtered.drop_duplicates(subset=['Report No.'])
        report_dict = dict(zip(unique_reports['Report No.'], unique_reports['issue_id']))
        
        with col_sel:
            if report_dict:
                selected_report = st.selectbox("Select report:", list(report_dict.keys()), label_visibility="collapsed")
            else:
                st.selectbox("Select report:", ["No data available"], disabled=True, label_visibility="collapsed")
                selected_report = None
                
        with col_btn:
            if report_dict and selected_report:
                if st.button("👁️ View This Report", type="primary", use_container_width=True):
                    show_a4_popup_readonly(report_dict[selected_report])
            else:
                st.button("👁️ View This Report", disabled=True, use_container_width=True)

        st.markdown("<div style='margin-bottom: 5px;'></div>", unsafe_allow_html=True)

        # --- RENDER BẢNG ---
        display_cols = ["Report No.", "Action Type", "Action Code", "Description", "Owner", "Due Date", "Status"]
        
        styled_df = df_page[display_cols].style.apply(highlight_action_status_html, axis=1)
        
        table_styles = [
            {'selector': 'thead th', 'props': [('background-color', 'black'), ('color', 'white'), ('font-weight', 'bold'), ('text-align', 'center'), ('padding', '12px'), ('border', '1px solid #555')]},
            {'selector': 'tbody td', 'props': [('padding', '10px'), ('border', '1px solid #ddd'), ('text-align', 'center'), ('vertical-align', 'middle')]}
        ]
        
        styled_df = styled_df.set_table_attributes('style="width: 100%; border-collapse: collapse; margin: 0;"')
        html_table = styled_df.set_table_styles(table_styles).hide(axis="index").to_html()
        
        final_html = f"<div class='table-shadow-wrapper'><div class='custom-table-container'>{html_table}</div></div>"
        st.markdown(final_html, unsafe_allow_html=True)
        
        # --- CỤM NÚT ĐIỀU HƯỚNG PHÂN TRANG TIẾNG ANH ---
        p_col1, p_col2, p_col3, p_col4, p_col5 = st.columns([1.5, 1.5, 4, 1.5, 1.5])
        
        with p_col1:
            if st.button("⏮ First", use_container_width=True, disabled=(current_page == 1)):
                st.session_state.at_page = 1
                st.rerun()
        with p_col2:
            if st.button("◀ Prev", use_container_width=True, disabled=(current_page == 1)):
                st.session_state.at_page -= 1
                st.rerun()
        with p_col3:
            st.markdown(f"<div style='text-align: center; padding-top: 5px; font-weight: bold;'>Page {current_page} of {total_pages}</div>", unsafe_allow_html=True)
        with p_col4:
            if st.button("Next ▶", use_container_width=True, disabled=(current_page == total_pages)):
                st.session_state.at_page += 1
                st.rerun()
        with p_col5:
            if st.button("Last ⏭", use_container_width=True, disabled=(current_page == total_pages)):
                st.session_state.at_page = total_pages
                st.rerun()