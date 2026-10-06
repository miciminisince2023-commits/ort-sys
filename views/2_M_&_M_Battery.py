import streamlit as st
import pandas as pd
from database.db_helper import (
    get_master_models, 
    add_master_model, 
    get_report_qty, 
    get_st_requests,
    get_setting_dropdowns
)

# Khai báo biến đầu vào có giá trị mặc định để không bị lỗi khi app.py truyền df_power_tool vào
def render(df_shared=None):
    # ================= 1. TIÊU ĐỀ TRANG =================
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
            🔋 BATTERIES LIST
</h2></div>
</div>
""", unsafe_allow_html=True)

    # ================= 2. KÉO DỮ LIỆU RIÊNG CHO BATTERY =================
    df_all_models = get_master_models()

    if not df_all_models.empty and "product_type" in df_all_models.columns:
        df_battery = df_all_models[df_all_models["product_type"] == "Battery"].copy()
        df_battery = df_battery.rename(columns={
            "ort_model": "ORT model",
            "model_name": "Model name",
            "category": "Category",
            "pic": "P.I.C"
        })
    else:
        df_battery = pd.DataFrame(columns=["ORT model", "Model name", "Category", "P.I.C", "product_type"])

    # ================= 3. MODAL THÊM MODEL MỚI =================
    @st.dialog("Add New Battery Model")
    def modal_add_battery():
        st.info("💡 **Battery Rule:** Must be exactly 9 digits and start with '130' (No conversion needed).")
        st.markdown("""<style> div[role="dialog"], div[data-testid="stDialog"], div[data-testid="stDialog"] button { border-radius: 0px !important; } </style>""", unsafe_allow_html=True)

        df_pic = get_setting_dropdowns("pic")
        df_mod = get_setting_dropdowns("model_name")
        
        list_pics = df_pic["value"].tolist() if not df_pic.empty else ["Default PIC"]
        list_model_names = df_mod["value"].tolist() if not df_mod.empty else ["Model A"]

        ort_model = st.text_input("Battery Code (9 digits, starts with '130') *", max_chars=9)
        model_name = st.selectbox("Model name *", options=list_model_names)
        pic = st.selectbox("P.I.C (Person in Charge)", options=list_pics)
        
        if st.button("Save to Database", type="primary"):
            if ort_model and model_name:
                if len(ort_model) == 9 and ort_model.startswith("130"):
                    if not df_all_models.empty and ort_model in df_all_models["ort_model"].values:
                        st.error("❌ This Battery Code already exists in the Database!")
                    else:
                        new_data = {
                            "ort_model": ort_model,
                            "model_name": model_name,
                            "category": "Battery",
                            "pic": pic,
                            "product_type": "Battery"
                        }
                        add_master_model([new_data])
                        st.success("✅ Battery model successfully saved to Cloud Database!")
                        st.rerun()
                else:
                    st.error("❌ Invalid Code! Must be exactly 9 digits and start with '130'.")
            else:
                st.error("⚠️ Please fill in all required fields (*).")

    
    col_btn_bp_1, col_btn_bp_2 = st.columns([6, 1])
    with col_btn_bp_1:
        if st.button("➕ Add New Battery", type="primary"):
            modal_add_battery()
    with col_btn_bp_2:
        # Thêm key cho nút để không trùng với nút ở tab Power Tool
        if st.button("🔄 Làm mới", key="btn_refresh_bat", use_container_width=True):
            st.session_state.bat_filters = {
                "search": "", "ort": "", "name": "", 
                "pic": "", "action": "All", "result": "All"
            }
            st.rerun()
    

    # ================= 4. TÍNH TOÁN DỮ LIỆU (FG ACCUM & METRICS) =================
    df_show = df_battery.copy()
    df_report = get_report_qty()
    
    if not df_report.empty and "ort_model" in df_report.columns and "rec_qty" in df_report.columns:
        df_report["rec_qty"] = pd.to_numeric(df_report["rec_qty"], errors="coerce").fillna(0)
        fg_sums = df_report.groupby("ort_model")["rec_qty"].sum().to_dict()
        df_show["FG accum"] = df_show["ORT model"].map(fg_sums).fillna(0).astype(int)
    else:
        df_show["FG accum"] = 0

    df_st = get_st_requests()
    if not df_st.empty and "req_status" in df_st.columns:
        closed_st = df_st[df_st["req_status"] == "Closed"]
        avail_sums = closed_st.groupby("ort_model")["req_qty"].sum().to_dict()
        df_show["Avail."] = df_show["ORT model"].map(avail_sums).fillna(0).astype(int)
        
        latest_st = df_st.sort_values(by="req_id").drop_duplicates(subset=["ort_model"], keep="last")
        latest_date_map = latest_st.set_index("ort_model")["start_date"].to_dict()
        latest_result_map = latest_st.set_index("ort_model")["test_result"].to_dict()
        
        df_show["Latest test year"] = df_show["ORT model"].map(latest_date_map).fillna("-")
        df_show["Latest test result"] = df_show["ORT model"].map(latest_result_map).apply(
            lambda x: x if pd.notna(x) and x != "" else "Pending"
        )
    else:
        df_show["Avail."] = 0
        df_show["Latest test year"] = "-"
        df_show["Latest test result"] = "Pending"

    # Tính hạng (Rank) và hành động (Action)
    if not df_show.empty:
        df_show["Rank"] = df_show["FG accum"].rank(ascending=False, method="min")
        
        def determine_battery_action(row):
            if row["Rank"] > 10 or row["FG accum"] <= 0:
                return "Monitor"
            latest_res = row["Latest test result"]
            if latest_res in ["Pass", "In testing"]:
                return "Monitor"
            return "Request Sample"

        df_show["Action required"] = df_show.apply(determine_battery_action, axis=1)
    else:
        df_show["Action required"] = "Monitor"

    def highlight_action(val):
        if val == "Request Sample": return 'background-color: #f8d7da; color: #721c24'
        if val == "Monitor": return 'background-color: #d4edda; color: #155724'
        return ''

    # ================= 5. BỘ LỌC (FILTERS) =================
    st.divider()

    # --- 1. TẠO BỘ NHỚ LƯU TRỮ CHO BATTERY ---
    if "bat_filters" not in st.session_state:
        st.session_state.bat_filters = {
            "search": "", "ort": "", "name": "", 
            "pic": "", "action": "All", "result": "All"
        }

    # --- 2. BỐ TRÍ TIÊU ĐỀ VÀ NÚT REFRESH ---
    col_title, col_btn = st.columns([4, 1])
    with col_title:
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
        #st.subheader("🔍 Filters")

    # --- 3. HIỂN THỊ WIDGET VỚI BỘ NHỚ ---
    with st.expander("Expand filters", expanded=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            f_search = st.text_input("Search...", value=st.session_state.bat_filters["search"], key="bat_search")
            st.session_state.bat_filters["search"] = f_search
            
            f_ort = st.text_input("ORT model (Battery code)", value=st.session_state.bat_filters["ort"], key="bat_ort")
            st.session_state.bat_filters["ort"] = f_ort
            
        with col_f2:
            f_name = st.text_input("Model name", value=st.session_state.bat_filters["name"], key="bat_name")
            st.session_state.bat_filters["name"] = f_name
            
            f_pic = st.text_input("P.I.C", value=st.session_state.bat_filters["pic"], key="bat_pic")
            st.session_state.bat_filters["pic"] = f_pic
            
        with col_f3:
            action_options = ["All", "Monitor", "Request Sample"]
            action_index = action_options.index(st.session_state.bat_filters["action"]) if st.session_state.bat_filters["action"] in action_options else 0
            f_action = st.selectbox("Action required", action_options, index=action_index, key="bat_action")
            st.session_state.bat_filters["action"] = f_action
            
            result_options = ["All", "Pass", "Fail", "In testing", "Pending"]
            result_index = result_options.index(st.session_state.bat_filters["result"]) if st.session_state.bat_filters["result"] in result_options else 0
            f_result = st.selectbox("Latest test result", result_options, index=result_index, key="bat_result")
            st.session_state.bat_filters["result"] = f_result

    # ================= 4. XỬ LÝ LOGIC LỌC =================
    df_all_show = df_show.copy()

    if not df_all_show.empty:
        if f_search:
            mask = df_all_show.astype(str).apply(lambda x: x.str.contains(f_search, case=False)).any(axis=1)
            df_all_show = df_all_show[mask]

        if f_ort: df_all_show = df_all_show[df_all_show["ORT model"].str.contains(f_ort, case=False, na=False)]
        if f_name: df_all_show = df_all_show[df_all_show["Model name"].str.contains(f_name, case=False, na=False)]
        if f_pic: df_all_show = df_all_show[df_all_show["P.I.C"].str.contains(f_pic, case=False, na=False)]
        if f_action != "All": df_all_show = df_all_show[df_all_show["Action required"] == f_action]
        if f_result != "All": df_all_show = df_all_show[df_all_show["Latest test result"] == f_result]

    # ================= 6. HIỂN THỊ DỮ LIỆU TOP 10 =================
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
                🏆 Annual Top 10 Battery Testing Candidates
            </h4>
        </div>
    </div>
    """, unsafe_allow_html=True)

    columns_order = [
        "ORT model", "Model name", "P.I.C", 
        "FG accum", "Avail.", "Latest test year", 
        "Latest test result", "Action required"
    ]

    if not df_show.empty:
        df_top10 = df_show[columns_order].sort_values(by="FG accum", ascending=False).reset_index(drop=True)
        df_top10.insert(0, "No.", range(1, len(df_top10) + 1))
        
        styled_battery = df_top10.style.map(highlight_action, subset=['Action required'])
        st.dataframe(styled_battery, width="stretch", hide_index=True)
    else:
        st.info("ℹ️ No battery models available in the database yet.")

    # ================= 7. HIỂN THỊ TOÀN BỘ DANH SÁCH =================
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
                📋 All Battery Models List
            </h4>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not df_all_show.empty:
        df_table_all = df_all_show[columns_order].reset_index(drop=True)
        styled_all = df_table_all.style.map(highlight_action, subset=['Action required'])
        st.dataframe(styled_all, width="stretch", hide_index=True)
    else:
        st.info("ℹ️ No matching records found.")