import streamlit as st
import pandas as pd
from datetime import date
from database.db_helper import get_st_requests, add_st_request, get_master_models, get_report_qty, get_setting_prefix, get_tier_rules
from logic.sku_converter import convert_tti_to_ort
from supabase import create_client
from database.db_helper import get_processed_power_tool_data


def render(df_shared=None):
    # Khởi tạo Supabase client cho các thao tác cập nhật trực tiếp
    @st.cache_resource
    def init_supabase():
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)

    supabase = init_supabase()

    st.markdown("""
<style>
.module-header-wrapper {
    /* Tạo khung bóng đổ xám nhạt ôm sát hình dạng vát góc */
    filter: drop-shadow(4px 4px 0px rgba(0, 0, 0, 0.2));
    margin-bottom: 25px;
    margin-top: 30px;
}

.module-header {
    background-color: #EBE600;
    color: #000000;
    padding: 15px 25px;
    font-size: 35px;
    font-weight: 800;
    /* Kiểu vát 2 góc đối diện */
    clip-path: polygon(25px 0, 100% 0, 100% calc(100% - 25px), calc(100% - 25px) 100%, 0 100%, 0 25px); 
    
    text-transform: uppercase;
}
</style>
<div class="module-header-wrapper">
    <div class="module-header">
    <h2 style='text-align: center; color: #000000; background-color: #EBE600; padding: 10px;'>
            🧪 SAMPLING & TESTING
</h2></div>
</div>
""", unsafe_allow_html=True)

    # ================= 1. FETCH DATA & TÍNH TOÁN GAP =================
    df_st_raw = get_st_requests()
    st.write(f"📊 Tổng số dòng thực tế lấy được từ Supabase: {len(df_st_raw)}")
    df_master_tool = get_master_models()
    df_prefix_raw = get_setting_prefix()
    df_report_raw = get_report_qty()
    df_tier_rules = get_tier_rules()

    # Chuẩn hóa tên cột cho ST requests
    if not df_st_raw.empty:
        df_st = df_st_raw.rename(columns={
            "req_id": "Req. id",
            "req_date": "Req. date",
            "tti_model": "TTI model",
            "ort_model": "ORT model",
            "req_qty": "Req. qty",
            "sam_job": "Sam job",
            "cb_f": "CB-F",
            "scp_f": "SCP-F",
            "dr_f": "DR-F",
            "item_test": "Item test",
            "start_date": "Start date",
            "end_date": "End date",
            "test_result": "Test result",
            "req_status": "Req. status",
            "req_duration": "Req. duration"
        })
        # THÊM 4 DÒNG NÀY ĐỂ TÍNH TOÁN ĐỘNG CHO TOÀN BỘ DỮ LIỆU CŨ LẪN MỚI:
        #temp_end = pd.to_datetime(df_st['End date'], errors='coerce')
        #temp_req = pd.to_datetime(df_st['Req. date'], errors='coerce')
        # Lấy End date - Req date. Nếu dòng nào chưa có End date (chưa test xong) thì tự động fill thành 0
        #df_st['Req. duration'] = (temp_end - temp_req).dt.days.fillna(0).astype(int)
    else:
        df_st = pd.DataFrame(columns=[
            "Req. id", "Req. date", "TTI model", "ORT model", "Req. qty",
            "Sam job", "CB-F", "SCP-F", "DR-F", "Item test",
            "Start date", "End date", "Test result", "Req. status", "Req. duration"
        ])

    st.session_state.df_st = df_st

    # Bảng Prefix setup
    if not df_prefix_raw.empty and "prefix" in df_prefix_raw.columns and "mapped" in df_prefix_raw.columns:
        df_prefix = df_prefix_raw[["prefix", "mapped"]].rename(columns={"prefix": "3 số đầu (Prefix)", "mapped": "Mã đổi (Mapped)"})
    else:
        df_prefix = pd.DataFrame([["011", "A1"]], columns=["3 số đầu (Prefix)", "Mã đổi (Mapped)"])

    # Tự động nạp dữ liệu Power Tool Gap nếu chưa có
    #if "df_master" not in st.session_state or st.session_state.df_master.empty:
    # ================= NẠP VÀ CẬP NHẬT LIÊN TỤC POWER TOOL GAP TỪ HÀM CHUẨN =================
    df_tool = get_processed_power_tool_data()
    
    # Lọc bỏ luôn các model Suspended để chúng không lọt vào danh sách Request
    if not df_tool.empty and "is_suspended" in df_tool.columns:
        df_tool = df_tool[~df_tool["is_suspended"].fillna(False).astype(bool)]
        
    st.session_state.df_master = df_tool

    # Tự động nạp dữ liệu Battery nếu chưa có
    if "df_master_battery" not in st.session_state or st.session_state.df_master_battery.empty:
        if not df_master_tool.empty and "product_type" in df_master_tool.columns:
            df_bat = df_master_tool[df_master_tool["product_type"] == "Battery"].copy()
            df_bat = df_bat.rename(columns={
                "ort_model": "ORT model",
                "model_name": "Model name",
                "category": "Category",
                "pic": "P.I.C"
            })
            
            if not df_report_raw.empty:
                bat_sums = df_report_raw.groupby("ort_model")["rec_qty"].sum().to_dict()
                df_bat["FG accum"] = df_bat["ORT model"].map(bat_sums).fillna(0).astype(int)
            else:
                df_bat["FG accum"] = 0
                
            st_requests_df = st.session_state.get("df_st", pd.DataFrame())
            active_ort_in_st = st_requests_df[st_requests_df["Req. status"] != "Closed"]["ORT model"].tolist() if not st_requests_df.empty else []
            
            def check_battery_action(row):
                ort = row["ORT model"]
                fg = row["FG accum"]
                if fg > 0 and ort not in active_ort_in_st:
                    return "Request Sample"
                return "Monitor"

            df_bat["Action required"] = df_bat.apply(check_battery_action, axis=1)
            st.session_state.df_master_battery = df_bat

    df_master = st.session_state.get("df_master", pd.DataFrame(columns=["ORT model", "Gap"]))
    df_master_battery = st.session_state.get("df_master_battery", pd.DataFrame(columns=["ORT model", "Action required"]))

    # ================= 2. MODAL GAP & REQUEST =================
    @st.dialog("Create Request from Shortage Models", width="large")
    def modal_gap_request():
        pending_sums = {}
        if not df_st.empty:
            pending_st = df_st[df_st["Req. status"] != "Closed"]
            pending_sums = pending_st.groupby("ORT model")["Req. qty"].sum().to_dict()
            
        gap_options = []
        real_gap_map = {}
        
        if not df_master.empty and "Gap" in df_master.columns:
            for _, row in df_master.iterrows():
                ort = row["ORT model"]
                master_gap = row["Gap"]
                pending_qty = pending_sums.get(ort, 0)
                real_gap = master_gap - pending_qty
                if real_gap > 0:
                    gap_options.append(ort)
                    real_gap_map[ort] = real_gap

        if not df_master_battery.empty and "Action required" in df_master_battery.columns:
            for _, row in df_master_battery.iterrows():
                ort = row["ORT model"]
                if row["Action required"] == "Request Sample":
                    gap_options.append(ort)
                    real_gap_map[ort] = "Document-based"

        if not gap_options:
            st.success("🎉 All Models (Tools & Batteries) have sufficient samples or are currently in testing!")
            return

        selected_ort = st.selectbox("Select ORT Model to Request", [""] + gap_options)
        
        if selected_ort:
            is_battery = selected_ort.startswith("130") and len(selected_ort) == 9
            
            # ========================================================
            # 1. KIỂM TRA TRẠNG THÁI SUSPENDED TỪ DATABASE
            is_suspended = False
            if not df_master_tool.empty and "is_suspended" in df_master_tool.columns:
                match = df_master_tool[df_master_tool["ort_model"] == selected_ort]
                if not match.empty:
                    is_suspended = bool(match["is_suspended"].fillna(False).values[0])

            # 2. HIỂN THỊ CẢNH BÁO NẾU MODEL ĐÃ NGƯNG HOẠT ĐỘNG
            if is_suspended:
                st.error(f"🛑 **CẢNH BÁO:** Model **{selected_ort}** đã được đưa vào diện **Suspended** (Ngưng sản xuất). Bạn không thể tạo Request mới!")
            # ========================================================

            if is_battery:
                st.info("💡 **Category: 🔋 Battery** | Sample Quantity: **Flexible entry per technical document**")
            else:
                current_real_gap = real_gap_map[selected_ort]
                st.info(f"💡 **Category: 🛠️ Power Tool** | Remaining Gap (minus active tests): **{int(current_real_gap)}**")
            
            st.divider()
            req_id = f"REQ-{len(df_st) + 1:04d}"
            
            col1, col2 = st.columns(2)
            with col1: st.text_input("Req. id (Auto)", value=req_id, disabled=True)
            with col2: req_date = st.date_input("Req. date", value=date.today(), disabled=True)
            
            tti_input = st.text_input("Enter TTI model (9 digits) for cross-check *", max_chars=9)
            
            ort_converted = ""
            if len(tti_input) >= 6:
                if is_battery:
                    ort_converted = tti_input 
                else:
                    ort_converted = convert_tti_to_ort(tti_input, df_prefix)
            
            if len(tti_input) >= 6:
                if ort_converted != selected_ort:
                    if is_battery:
                        st.error(f"❌ Warning: Battery TTI '{tti_input}' DOES NOT MATCH ORT Model '{selected_ort}'!")
                    else:
                        st.error(f"❌ Warning: Converted TTI '{ort_converted}' DOES NOT MATCH '{selected_ort}'!")
                else:
                    st.success("✅ ORT Model Matched!")
                    
            if is_battery:
                req_qty = st.number_input("Req. qty", min_value=1, step=1)
            else:
                # Chặn lỗi max_value = 0 nếu Real Gap bị âm/bằng 0 (Edge case protection)
                safe_max = int(current_real_gap) if int(current_real_gap) > 0 else 1
                req_qty = st.number_input("Req. qty", min_value=1, max_value=safe_max, step=1)
            
            # ========================================================
            # 3. KHÓA NÚT SAVE NẾU BỊ SUSPENDED HOẶC SAI TTI
            disable_save = (ort_converted != selected_ort) or is_suspended
            
            if st.button("Save Request", disabled=disable_save, type="primary"):
            # ========================================================
                new_row = {
                    "req_id": req_id,
                    "req_date": str(req_date),
                    "tti_model": tti_input,
                    "ort_model": selected_ort,
                    "req_qty": int(req_qty),
                    "sam_job": "",
                    "cb_f": "",
                    "scp_f": "",
                    "dr_f": "",
                    "item_test": "",
                    "start_date": str(req_date),
                    "end_date": str(req_date),
                    "test_result": "Pending",
                    "req_status": "In testing",
                    "req_duration": 0
                }
                add_st_request([new_row])
                st.success("✅ Request successfully saved to Cloud Database!")
                st.rerun()

    # ================= 3. MODAL EDIT REQUEST =================
    @st.dialog("Edit ST Request", width="large")
    def modal_edit_request(req_id):
        filtered_df = df_st[df_st['Req. id'] == req_id]
        if filtered_df.empty:
            st.error("Request not found.")
            return
        row = filtered_df.iloc[0]
        
        st.markdown(f"Editing Request: **{req_id}** (ORT: {row['ORT model']})")
        
        sam_job = st.text_input("Sam job", value=row["Sam job"] if pd.notna(row["Sam job"]) else "")
        cb_f = st.text_input("CB-F", value=row["CB-F"] if pd.notna(row["CB-F"]) else "", disabled=(not sam_job))
        scp_f = st.text_input("SCP-F", value=row["SCP-F"] if pd.notna(row["SCP-F"]) else "", disabled=(not cb_f))
        dr_f = st.text_input("DR-F", value=row["DR-F"] if pd.notna(row["DR-F"]) else "", disabled=(not scp_f))
        
        unlock_final = bool(dr_f)
        item_options = ["", "Use test", "Fixture test", "Other"]
        current_item = row["Item test"] if pd.notna(row["Item test"]) else ""
        item_idx = item_options.index(current_item) if current_item in item_options else 0
        
        item_test = st.selectbox("Item test", item_options, index=item_idx, disabled=not unlock_final)
        
        start_val = pd.to_datetime(row["Start date"]).date() if pd.notnull(row["Start date"]) and row["Start date"] != "" else date.today()
        end_val = pd.to_datetime(row["End date"]).date() if pd.notnull(row["End date"]) and row["End date"] != "" else None
        
        start_date = st.date_input("Start date", value=start_val, disabled=not unlock_final)
        end_date = st.date_input("End date", value=end_val, disabled=not unlock_final)
        
        res_options = ["", "Pass", "In testing", "Fail"]
        current_res = row["Test result"] if pd.notna(row["Test result"]) else ""
        res_idx = res_options.index(current_res) if current_res in res_options else 0
        
        test_result = st.selectbox("Test result", res_options, index=res_idx, disabled=not unlock_final)
        
        if st.button("Save Changes", type="primary"):
            status = "In testing"
            duration = 0
            
            # Khai báo lại req_date từ dữ liệu của dòng hiện tại
            req_date_val = pd.to_datetime(row["Req. date"]).date() if pd.notnull(row["Req. date"]) else None

            if test_result in ["Pass", "Fail"]:
                status = "Closed"
                # Tính duration dựa trên end_date và req_date
                if end_date and req_date_val:
                    duration = (end_date - req_date_val).days
            elif end_date and date.today() > end_date:
                status = "Overdue"

            update_data = {
                "sam_job": sam_job,
                "cb_f": cb_f,
                "scp_f": scp_f,
                "dr_f": dr_f,
                "item_test": item_test,
                "start_date": str(start_date) if start_date else None,
                "end_date": str(end_date) if end_date else None,
                "test_result": test_result if test_result else "Pending",
                "req_status": status,
                "req_duration": duration
            }
            
            try:
                supabase.table("st_requests").update(update_data).eq("req_id", req_id).execute()
                st.success("✅ Request updated successfully in Cloud Database!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error updating database: {e}")

    col_bt_st_1, col_bt_st_2 = st.columns([6, 1])
    with col_bt_st_1:
        if st.button("🚨 View Gap & Create Request", type="primary"):
            modal_gap_request()
    with col_bt_st_2:
        if st.button("🔄 Làm mới", key="btn_refresh_st", use_container_width=True):
            # Reset bộ nhớ về mặc định
            st.session_state.st_filters = {
                "search": "", "date": [], "ort": "", "tti": "", 
                "cbf": "", "scpf": "", "drf": "", 
                "item": "All", "res": "All", "status": "All"
            }
            st.rerun()

    # ================= 4. FILTERS & DISPLAY =================
    st.divider()

    # --- 1. TẠO BỘ NHỚ LƯU TRỮ CHO S&T ---
    if "st_filters" not in st.session_state:
        st.session_state.st_filters = {
            "search": "", "date": [], "ort": "", "tti": "", 
            "cbf": "", "scpf": "", "drf": "", 
            "item": "All", "res": "All", "status": "All"
        }

    # --- 2. BỐ TRÍ TIÊU ĐỀ VÀ NÚT REFRESH ---
    col_title, col_btn = st.columns([4, 1])
    st.markdown("""
    <style>
    .alert-header-v2-wrapper {
    /* Tạo khung bóng đổ xám nhạt ôm sát hình dạng vát góc */
    filter: drop-shadow(4px 4px 0px rgba(0, 0, 0, 0.2));
    margin-bottom: 10px;
    margin-top: 0px;
    }
    .alert-header-v2 {
        background-color: #EBE600;
        color: #000000;
        padding: 10px 25px; /* Điều chỉnh lại padding cho cân đối */
        font-size: 22px;
        font-weight: 800;
        /* Công thức vát góc trên-trái và dưới-phải (20px) */
        clip-path: polygon(20px 0, 100% 0, 100% calc(100% - 20px), calc(100% - 20px) 100%, 0 100%, 0 20px);
        margin-bottom: 1px;
        display: inline-flex; /* Đổi thành inline-flex để đi kèm với fit-content */
        align-items: center;
        gap: 10px;
        width: fit-content; /* CHÌA KHÓA: Ép chiều ngang vừa khít với nội dung */
    }
    </style>
    <div class="alert-header-v2-wrapper">
        <div class="alert-header-v2">
            <h4 style='text-align: center; color: #000000; background-color: #EBE600; padding: 5px;'>
                🔍 Filters
            </h4>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- 3. HIỂN THỊ WIDGET VỚI BỘ NHỚ ---
    with st.expander("Expand filters", expanded=True):
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        
        with col_f1:
            f_search = st.text_input("Global search...", value=st.session_state.st_filters["search"], key="st_search")
            st.session_state.st_filters["search"] = f_search
            
            f_date = st.date_input("Request date range", value=st.session_state.st_filters["date"], key="st_date")
            st.session_state.st_filters["date"] = f_date

            item_options = ["All", "Use test", "Fixture test", "Other"]
            item_idx = item_options.index(st.session_state.st_filters["item"]) if st.session_state.st_filters["item"] in item_options else 0
            f_item = st.selectbox("Item test", item_options, index=item_idx, key="st_item")
            st.session_state.st_filters["item"] = f_item
            
        with col_f2:
            f_ort = st.text_input("ORT model", value=st.session_state.st_filters["ort"], key="st_ort")
            st.session_state.st_filters["ort"] = f_ort
            
            f_tti = st.text_input("TTI model", value=st.session_state.st_filters["tti"], key="st_tti")
            st.session_state.st_filters["tti"] = f_tti
            
            f_cbf = st.text_input("CB-F", value=st.session_state.st_filters["cbf"], key="st_cbf")
            st.session_state.st_filters["cbf"] = f_cbf
            
        with col_f3:
            f_scpf = st.text_input("SCP-F", value=st.session_state.st_filters["scpf"], key="st_scpf")
            st.session_state.st_filters["scpf"] = f_scpf
            
            f_drf = st.text_input("DR-F", value=st.session_state.st_filters["drf"], key="st_drf")
            st.session_state.st_filters["drf"] = f_drf
            
        with col_f4:
            res_options = ["All", "Pass", "In testing", "Fail", "Pending"]
            res_idx = res_options.index(st.session_state.st_filters["res"]) if st.session_state.st_filters["res"] in res_options else 0
            f_res = st.selectbox("Test result", res_options, index=res_idx, key="st_res")
            st.session_state.st_filters["res"] = f_res
            
            status_options = ["All", "In testing", "Overdue", "Closed"]
            status_idx = status_options.index(st.session_state.st_filters["status"]) if st.session_state.st_filters["status"] in status_options else 0
            f_status = st.selectbox("Req. status", status_options, index=status_idx, key="st_status")
            st.session_state.st_filters["status"] = f_status

    # ================= 4. XỬ LÝ LOGIC LỌC =================
    df_show = df_st.copy()
    if f_search:
        mask = df_show.astype(str).apply(lambda x: x.str.contains(f_search, case=False)).any(axis=1)
        df_show = df_show[mask]

    if len(f_date) == 2:
        start_f, end_f = f_date
        valid_d = pd.to_datetime(df_show['Req. date'], errors='coerce')
        df_show = df_show[(valid_d.dt.date >= start_f) & (valid_d.dt.date <= end_f)]

    if f_ort: df_show = df_show[df_show["ORT model"].str.contains(f_ort, case=False, na=False)]
    if f_tti: df_show = df_show[df_show["TTI model"].str.contains(f_tti, case=False, na=False)]
    
    # (Nếu sau này bạn muốn lọc theo CB-F, SCP-F, DR-F thì có thể bổ sung điều kiện vào đây)
    
    if f_item != "All": df_show = df_show[df_show["Item test"] == f_item]
    if f_res != "All": df_show = df_show[df_show["Test result"] == f_res]
    if f_status != "All": df_show = df_show[df_show["Req. status"] == f_status]

    # ================= 5. LIST VIEW =================
    st.divider()
    st.markdown("""
    <style>
    .alert-header-v2-wrapper {
    /* Tạo khung bóng đổ xám nhạt ôm sát hình dạng vát góc */
    filter: drop-shadow(4px 4px 0px rgba(0, 0, 0, 0.2));
    margin-bottom: 10px;
    margin-top: 0px;
    }
    .alert-header-v2 {
        background-color: #EBE600;
        color: #000000;
        padding: 10px 25px; /* Điều chỉnh lại padding cho cân đối */
        font-size: 22px;
        font-weight: 800;
        /* Công thức vát góc trên-trái và dưới-phải (20px) */
        clip-path: polygon(20px 0, 100% 0, 100% calc(100% - 20px), calc(100% - 20px) 100%, 0 100%, 0 20px);
        margin-bottom: 1px;
        display: inline-flex; /* Đổi thành inline-flex để đi kèm với fit-content */
        align-items: center;
        gap: 10px;
        width: fit-content; /* CHÌA KHÓA: Ép chiều ngang vừa khít với nội dung */
    }
    </style>
    <div class="alert-header-v2-wrapper">
        <div class="alert-header-v2">
            <h4 style='text-align: center; color: #000000; background-color: #EBE600; padding: 5px;'>
                📋 Sampling & Testing Requests List
            </h4>
        </div>
    </div>
    """, unsafe_allow_html=True)

    columns_to_hide = ["created_at"]
    display_cols = [c for c in df_show.columns if c not in columns_to_hide]
    df_display = df_show[display_cols].copy()

    df_display.insert(0, "Edit", "✏️")
    df_display.insert(1, "No.", range(1, len(df_display) + 1))

    def highlight_result(val):
        if val == "Pass": return 'background-color: #d4edda; color: #155724'
        if val == "Fail": return 'background-color: #f8d7da; color: #721c24'
        if val == "In testing": return 'background-color: #fff3cd; color: #856404'
        return ''

    styled_df = df_display.style.map(highlight_result, subset=['Test result'])

    event = st.dataframe(
        styled_df, 
        width="stretch", 
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun",
        key="st_request_table"
    )

    selected_rows = event.selection.get("rows", [])
    if selected_rows:
        idx = selected_rows[0]
        selected_req_id = df_show.iloc[idx]["Req. id"]
        modal_edit_request(selected_req_id)