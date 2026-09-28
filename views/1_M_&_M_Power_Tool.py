import streamlit as st
import pandas as pd
from database.db_helper import add_master_model, get_setting_dropdowns

def render(df_power_tool):
    # ================= 1. TIÊU ĐỀ TRANG =================
    st.markdown("""
    <style>
    .module-header-wrapper {
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
        clip-path: polygon(25px 0, 100% 0, 100% calc(100% - 25px), calc(100% - 25px) 100%, 0 100%, 0 25px); 
        text-transform: uppercase;
    }
    </style>
    <div class="module-header-wrapper">
        <div class="module-header">
        <h2 style='text-align: center; color: #000000; background-color: #EBE600; padding: 10px; margin: 0;'>
                🛠️ POWER TOOLS LIST
        </h2></div>
    </div>
    """, unsafe_allow_html=True)

    # ================= 2. MODAL THÊM MODEL MỚI =================
    @st.dialog("Add New Model")
    def modal_add_model():

    
        # Ép góc vuông cho khung modal theo thiết kế cũ
        st.markdown("""<style> div[role="dialog"], div[data-testid="stDialog"], div[data-testid="stDialog"] button { border-radius: 0px !important; } </style>""", unsafe_allow_html=True)

        df_cat = get_setting_dropdowns("category")
        df_pic = get_setting_dropdowns("pic")
        df_mod = get_setting_dropdowns("model_name")
        
        list_categories = df_cat["value"].tolist() if not df_cat.empty else ["Standard", "Nailer", "Saw"]
        list_pics = df_pic["value"].tolist() if not df_pic.empty else ["Default PIC"]
        list_model_names = df_mod["value"].tolist() if not df_mod.empty else ["Model A"]

        # Form nhập liệu
        ort_model = st.text_input("ORT model *")
        model_name = st.selectbox("Model name *", options=list_model_names)
        category = st.selectbox("Category", options=list_categories)
        pic = st.selectbox("P.I.C (Person in Charge)", options=list_pics)
        
        if st.button("Save to Database", type="primary"):
            if ort_model and model_name:
                if not df_power_tool.empty and ort_model in df_power_tool["ORT model"].values:
                    st.error("❌ This ORT model already exists in the Database!")
                else:
                    new_data = {
                        "ort_model": ort_model,
                        "model_name": model_name,
                        "category": category,
                        "pic": pic,
                        "product_type": "Power Tool"
                    }
                    add_master_model([new_data])
                    st.success("✅ Power Tool model successfully saved to Cloud Database!")
                    # Dùng st.rerun() để app tự tải lại dữ liệu mới từ Database
                    st.rerun()
            else:
                st.error("⚠️ Please fill in all required fields (*).")

    # Nút gọi Modal
    col_btn_pt_1, col_btn_pt_2 = st.columns([6, 1]) # Chia cột để nút Add New Model nằm bên trái
    with col_btn_pt_1:
        if st.button("➕ Add New Model", type="primary"):
            modal_add_model()
    with col_btn_pt_2:
        if st.button("🔄 Làm mới", use_container_width=True):
            # Reset bộ nhớ về mặc định
            st.session_state.pt_filters = {
                "search": "", "date": [], "ort": "", "name": "", 
                "cat": "All", "pic": "", "action": "All", 
                "status": "All", "result": "All"
            }
            st.rerun()

    # ================= 3. BỘ LỌC (FILTERS) =================
    # Dùng luôn dữ liệu df_power_tool đã được app.py xử lý sẵn
    df_show = df_power_tool.copy()

    # THÊM MỚI: Chuẩn hóa tên cột từ database (chữ thường) sang UI (chữ hoa)
    rename_mapping = {
        "category": "Category",
        "model_name": "Model name",
        "pic": "P.I.C",
        "ort_model": "ORT model"
    }
    df_show = df_show.rename(columns=rename_mapping)

    st.divider()
    
    # --- 1. TẠO BỘ NHỚ LƯU TRỮ CHO POWER TOOL ---
    if "pt_filters" not in st.session_state:
        st.session_state.pt_filters = {
            "search": "", "date": [], "ort": "", "name": "", 
            "cat": "All", "pic": "", "action": "All", 
            "status": "All", "result": "All"
        }

    # --- 2. BỐ TRÍ TIÊU ĐỀ VÀ NÚT REFRESH ---
    col_title, col_btn = st.columns([4, 1]) # Chia cột để nút Refresh nằm bên phải tiêu đề
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
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        
        with col_f1:
            f_search = st.text_input("Search...", value=st.session_state.pt_filters["search"], key="pt_search")
            st.session_state.pt_filters["search"] = f_search
            
            f_date = st.date_input("Latest test date (From - To)", value=st.session_state.pt_filters["date"], key="pt_date")
            st.session_state.pt_filters["date"] = f_date
            
        with col_f2:
            f_ort = st.text_input("ORT model", value=st.session_state.pt_filters["ort"], key="pt_ort")
            st.session_state.pt_filters["ort"] = f_ort
            
            f_name = st.text_input("Model name", value=st.session_state.pt_filters["name"], key="pt_name")
            st.session_state.pt_filters["name"] = f_name
            
            list_cat = ["All"] + df_show["Category"].dropna().unique().tolist() if not df_show.empty else ["All"]
            cat_index = list_cat.index(st.session_state.pt_filters["cat"]) if st.session_state.pt_filters["cat"] in list_cat else 0
            f_cat = st.selectbox("Category", list_cat, index=cat_index, key="pt_cat")
            st.session_state.pt_filters["cat"] = f_cat
            
        with col_f3:
            f_pic = st.text_input("P.I.C", value=st.session_state.pt_filters["pic"], key="pt_pic")
            st.session_state.pt_filters["pic"] = f_pic
            
            action_options = ["All", "Monitor", "Request Sample"]
            action_index = action_options.index(st.session_state.pt_filters["action"]) if st.session_state.pt_filters["action"] in action_options else 0
            f_action = st.selectbox("Action required", action_options, index=action_index, key="pt_action")
            st.session_state.pt_filters["action"] = f_action
            
        with col_f4:
            status_options = ["All", "Sufficient", "Shortage"]
            status_index = status_options.index(st.session_state.pt_filters["status"]) if st.session_state.pt_filters["status"] in status_options else 0
            f_status = st.selectbox("Sample Status", status_options, index=status_index, key="pt_status")
            st.session_state.pt_filters["status"] = f_status
            
            result_options = ["All", "Pass", "Fail", "In testing", "Pending"]
            result_index = result_options.index(st.session_state.pt_filters["result"]) if st.session_state.pt_filters["result"] in result_options else 0
            f_result = st.selectbox("Latest test result", result_options, index=result_index, key="pt_result")
            st.session_state.pt_filters["result"] = f_result

    # ================= 4. XỬ LÝ LOGIC LỌC (Giữ nguyên) =================
    if not df_show.empty:
        if f_search:
            mask = df_show.astype(str).apply(lambda x: x.str.contains(f_search, case=False)).any(axis=1)
            df_show = df_show[mask]

        if len(f_date) == 2:
            start_d, end_d = f_date
            valid_dates = pd.to_datetime(df_show['Latest test date'], errors='coerce')
            date_mask = (valid_dates.dt.date >= start_d) & (valid_dates.dt.date <= end_d)
            df_show = df_show[date_mask | (df_show['Latest test date'] == "-")] 

        if f_ort: df_show = df_show[df_show["ORT model"].str.contains(f_ort, case=False, na=False)]
        if f_name: df_show = df_show[df_show["Model name"].str.contains(f_name, case=False, na=False)]
        if f_pic: df_show = df_show[df_show["P.I.C"].str.contains(f_pic, case=False, na=False)]
        if f_cat != "All": df_show = df_show[df_show["Category"] == f_cat]
        if f_action != "All": df_show = df_show[df_show["Action required"] == f_action]
        if f_status != "All": df_show = df_show[df_show["Sample Status"] == f_status]
        if f_result != "All": df_show = df_show[df_show["Latest result"] == f_result]

    # ================= 4. HIỂN THỊ BẢNG DỮ LIỆU CÓ MÀU SẮC =================
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
                📋 ORT Model List
            </h4>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not df_show.empty:
        columns_order = [
            "ORT model", "Model name", "Category", "P.I.C", 
            "FG accum", "Req.", "Avail.", "Gap", "Sample Status", 
            "Latest test date", "Latest result", "Next test qty", "Action required"
        ]
        # Lọc lấy các cột có tồn tại
        cols_exist = [col for col in columns_order if col in df_show.columns]
        df_show = df_show[cols_exist]

        def highlight_cells(val):
            if val == "Sufficient": return 'background-color: #d4edda; color: #155724'
            if val == "Shortage": return 'background-color: #f8d7da; color: #721c24'
            if val == "Pass": return 'background-color: #d4edda; color: #155724'
            if val == "Fail": return 'background-color: #f8d7da; color: #721c24'
            if val == "In testing": return 'background-color: #fff3cd; color: #856404'
            return ''

        # Bôi màu dựa trên cột
        styled_df = df_show.style.map(highlight_cells, subset=['Sample Status', 'Latest result'] if 'Sample Status' in df_show.columns and 'Latest result' in df_show.columns else None)
        
        st.dataframe(styled_df, width="stretch", hide_index=True, height=600)
    else:
        st.warning("⚠️ Không có dữ liệu hiển thị (hoặc không khớp với bộ lọc hiện tại).")