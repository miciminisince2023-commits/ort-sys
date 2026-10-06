import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database.db_helper import get_report_qty, add_report_qty, get_master_models, get_setting_prefix
from logic.sku_converter import convert_tti_to_ort

def render(df_shared=None):
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
    <h2 style='text-align: center; color: #000000; background-color: #EBE600; padding: 10px;'>
            📦 PRODUCTION - REPORT QTY
</h2></div>
</div>
""", unsafe_allow_html=True)

    # ================= 2. FETCH DATA TỪ DATABASE =================
    df_prefix_raw = get_setting_prefix()
    if not df_prefix_raw.empty and "prefix" in df_prefix_raw.columns and "mapped" in df_prefix_raw.columns:
        df_prefix = df_prefix_raw[["prefix", "mapped"]].rename(columns={"prefix": "Prefix (3 digits)", "mapped": "Mapped Code"})
    else:
        df_prefix = pd.DataFrame([["011", "A1"]], columns=["Prefix (3 digits)", "Mapped Code"])

    # CẬP NHẬT: Lấy danh sách toàn bộ Model và phân loại Active / Suspended
    df_master = get_master_models()
    if not df_master.empty:
        valid_ort_models = set(df_master["ort_model"].astype(str).str.strip().str.upper())
        if "is_suspended" in df_master.columns:
            suspended_models = set(df_master[df_master["is_suspended"] == True]["ort_model"].astype(str).str.strip().str.upper())
        else:
            suspended_models = set()
    else:
        valid_ort_models = set()
        suspended_models = set()

    # ================= 3. MODAL: SINGLE REPORT =================
    @st.dialog("Add Production Report (Single)", width="large")
    def modal_single_report():
        st.markdown("💡 **Auto-conversion Rule:** Enter the TTI Model. The system will automatically convert and lock the correct ORT Model.")
        
        rec_date = st.date_input("Received Date (Rec. date)", value=date.today())
        tti_input = st.text_input("Enter TTI Model (9 digits) *", max_chars=9, placeholder="e.g. 011123456 or 130123456")
        
        auto_ort = ""
        is_suspended = False
        
        if len(tti_input) >= 3:
            if tti_input.startswith("130") and len(tti_input) == 9:
                auto_ort = tti_input 
            else:
                auto_ort = convert_tti_to_ort(tti_input, df_prefix)
            
            # CẬP NHẬT: Kiểm tra và hiển thị lỗi tức thì nếu thuộc diện Suspended
            if auto_ort and auto_ort.upper() in suspended_models:
                is_suspended = True
                st.error(f"🛑 **ERROR:** Model **{auto_ort}** is **Suspended** (End-of-life). Cannot report Qty for this model!")

        st.text_input("ORT Model (Auto-converted) *", value=auto_ort, disabled=True, help="Automatically mapped via prefix conversion or battery rule.")
        rec_qty = st.number_input("Received Quantity (Rec. qty) *", min_value=1, step=1, value=1000)
        
        st.divider()
        # CẬP NHẬT: Khóa cứng nút Save nếu model bị Suspended
        if st.button("Save Report", type="primary", use_container_width=True, disabled=is_suspended):
            if tti_input and auto_ort and rec_qty:
                new_record = {
                    "ort_model": auto_ort,
                    "tti_model": tti_input,
                    "rec_date": str(rec_date),
                    "rec_qty": int(rec_qty)
                }
                add_report_qty([new_record])
                st.success("✅ Production report successfully saved to Cloud Database!")
                st.rerun()
            else:
                st.error("⚠️ Please enter a valid TTI model so the system can automatically resolve the ORT model.")

    # ================= 4. MODAL: BULK REPORT =================
    @st.dialog("Bulk Add / Edit Production Reports", width="large")
    def modal_bulk_report():
        st.markdown("💡 **Interactive Bulk Paste:** Just paste your **Rec. date**, **TTI model**, and **Rec. qty**.")
        
        if "df_bulk_temp" not in st.session_state:
            st.session_state.df_bulk_temp = pd.DataFrame(
                [[str(date.today()), "", 1000]], 
                columns=["Rec. date", "TTI model", "Rec. qty"]
            )
            
        edited_bulk = st.data_editor(
            st.session_state.df_bulk_temp,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="bulk_report_editor"
        )
        
        st.divider()
        if st.button("Save All Reports", type="primary", use_container_width=True):
            try:
                records_to_add = []
                suspended_found = [] # CẬP NHẬT: Danh sách chứa các model lỗi
                
                for _, row in edited_bulk.iterrows():
                    tti = str(row["TTI model"]).strip()
                    r_date = str(row["Rec. date"]).strip()
                    qty = row["Rec. qty"]
                    
                    if tti and qty > 0:
                        if tti.startswith("130") and len(tti) == 9:
                            calculated_ort = tti
                        else:
                            calculated_ort = convert_tti_to_ort(tti, df_prefix)
                            
                        # CẬP NHẬT: Thu thập các model bị Suspended
                        if calculated_ort and calculated_ort.upper() in suspended_models:
                            suspended_found.append(f"TTI: **{tti}** ➡️ ORT: **{calculated_ort}**")
                            continue
                            
                        records_to_add.append({
                            "ort_model": calculated_ort,
                            "tti_model": tti,
                            "rec_date": r_date if r_date else str(date.today()),
                            "rec_qty": int(qty)
                        })
                
                # CẬP NHẬT: Chặn không cho lưu và in ra danh sách lỗi
                if suspended_found:
                    st.error("🛑 **SYSTEM REJECTED:** Suspended models detected in your list. Please remove these rows to continue:")
                    for item in suspended_found:
                        st.warning(item)
                else:
                    if records_to_add:
                        add_report_qty(records_to_add)
                        st.success(f"✅ Successfully saved {len(records_to_add)} report records to Cloud Database!")
                        del st.session_state.df_bulk_temp
                        st.rerun()
                    else:
                        st.error("⚠️ No valid rows to save. Please check your data.")
            except Exception as e:
                st.error(f"❌ Error saving bulk data: {e}")

    # ================= 4.5. MODAL: UPLOAD EXCEL (SAFE TEST MODE) =================
    @st.dialog("Upload Excel - Smart Validation", width="large")
    def modal_upload_excel():
        st.markdown("💡 **Upload Excel:** The system will automatically scan, convert TTI to ORT, and classify valid/invalid data.")
        
        if "upload_scanned" not in st.session_state:
            st.session_state.upload_scanned = False
            st.session_state.valid_rows = []
            st.session_state.invalid_rows = []

        uploaded_file = st.file_uploader("Select Excel file (Supports .xlsx, .xls)", type=["xlsx", "xls"])
        if not uploaded_file:
            st.session_state.upload_scanned = False

        if uploaded_file:
            try:
                df_raw = pd.read_excel(uploaded_file)
            except Exception as e:
                st.error(f"❌ Cannot read file. Error: {e}")
                return
            
            cols = df_raw.columns.tolist()
            col1, col2, col3 = st.columns(3)
            with col1: date_col = st.selectbox("Date Column", cols, index=0)
            with col2: tti_col = st.selectbox("TTI Model Column", cols, index=1 if len(cols) > 1 else 0)
            with col3: qty_col = st.selectbox("Quantity Column", cols, index=2 if len(cols) > 2 else 0)

            if st.button("🔍 Scan & Analyze Data", type="primary", use_container_width=True):
                valid_rows = []
                invalid_rows = []

                for index, row in df_raw.iterrows():
                    raw_date = row[date_col]
                    raw_tti = str(row[tti_col]).strip().upper()
                    raw_qty = row[qty_col]
                    
                    error_reasons = []
                    ort_converted = ""

                    try:
                        qty = int(pd.to_numeric(raw_qty))
                        if qty <= 0: error_reasons.append("Quantity <= 0")
                    except:
                        error_reasons.append("Quantity is not a number")
                        qty = 0

                    try:
                        rec_date = pd.to_datetime(raw_date).date()
                    except:
                        error_reasons.append("Invalid date format")
                        rec_date = date.today()

                    if len(raw_tti) >= 3:
                        if raw_tti.startswith("130") and len(raw_tti) == 9:
                            ort_converted = raw_tti
                        else:
                            ort_converted = convert_tti_to_ort(raw_tti, df_prefix)
                    else:
                        error_reasons.append("TTI model is too short")

                    if not ort_converted:
                        error_reasons.append("Invalid Prefix")
                    elif ort_converted not in valid_ort_models:
                        error_reasons.append(f"ORT Model ({ort_converted}) does not exist")
                    # CẬP NHẬT: Đẩy trực tiếp vào danh sách lỗi nếu Suspended
                    elif ort_converted in suspended_models:
                        error_reasons.append("🛑 Model đã bị Suspended")

                    if len(error_reasons) == 0:
                        valid_rows.append({
                            "ort_model": ort_converted,
                            "tti_model": raw_tti,
                            "rec_date": str(rec_date),
                            "rec_qty": qty
                        })
                    else:
                        invalid_rows.append({
                            "Excel Row": index + 2,
                            "Rec. date": str(rec_date),
                            "TTI model": raw_tti,
                            "Rec. qty": raw_qty,
                            "Error Reason": " | ".join(error_reasons)
                        })

                st.session_state.valid_rows = valid_rows
                st.session_state.invalid_rows = invalid_rows
                st.session_state.upload_scanned = True

            if st.session_state.upload_scanned:
                st.divider()
                valid_rows = st.session_state.valid_rows
                invalid_rows = st.session_state.invalid_rows

                if invalid_rows:
                    st.error(f"⚠️ Detected {len(invalid_rows)} invalid rows!")
                    st.markdown("🛠️ **Quick Fix:** Double-click on a cell to edit (Date, Model, Quantity). Data will not be lost when you type.")
                    
                    df_invalid = pd.DataFrame(invalid_rows)
                    edited_invalid_df = st.data_editor(
                        df_invalid, 
                        use_container_width=True, 
                        hide_index=True,
                        key="editor_invalid_rows"
                    )
                    
                    col_fix1, col_fix2 = st.columns(2)
                    with col_fix1:
                        if st.button("🔄 Scan again the edited rows", use_container_width=True):
                            new_valid = []
                            still_invalid = []
                            
                            df_master_refresh = get_master_models()
                            if not df_master_refresh.empty:
                                valid_ort_models_refresh = set(df_master_refresh["ort_model"].astype(str).str.strip().str.upper())
                                suspended_models_refresh = set(df_master_refresh[df_master_refresh["is_suspended"] == True]["ort_model"].astype(str).str.strip().str.upper()) if "is_suspended" in df_master_refresh.columns else set()
                            else:
                                valid_ort_models_refresh = set()
                                suspended_models_refresh = set()
                            
                            for idx, row in edited_invalid_df.iterrows():
                                raw_tti = str(row["TTI model"]).strip().upper()
                                raw_qty = row["Rec. qty"]
                                raw_date = row["Rec. date"]
                                row_idx = row["Dòng Excel"]
                                
                                error_reasons = []
                                ort_converted = ""
                                
                                try:
                                    qty = int(pd.to_numeric(raw_qty))
                                    if qty <= 0: error_reasons.append("Quantity <= 0")
                                except:
                                    error_reasons.append("Quantity is not a number")
                                    qty = 0
                                
                                try:
                                    rec_date = pd.to_datetime(raw_date).date()
                                except:
                                    error_reasons.append("Invalid date format")
                                    rec_date = date.today()
                                    
                                if len(raw_tti) >= 3:
                                    if raw_tti.startswith("130") and len(raw_tti) == 9:
                                        ort_converted = raw_tti
                                    else:
                                        ort_converted = convert_tti_to_ort(raw_tti, df_prefix)
                                else:
                                    error_reasons.append("TTI model is too short")
                                    
                                if not ort_converted:
                                    error_reasons.append("Invalid Prefix")
                                elif ort_converted not in valid_ort_models_refresh:
                                    error_reasons.append("ORT Model does not exist")
                                # CẬP NHẬT: Quét lại kiểm tra Suspended
                                elif ort_converted in suspended_models_refresh:
                                    error_reasons.append("🛑 Model has been Suspended")
                                    
                                if len(error_reasons) == 0:
                                    new_valid.append({
                                        "ort_model": ort_converted,
                                        "tti_model": raw_tti,
                                        "rec_date": str(rec_date),
                                        "rec_qty": qty
                                    })
                                else:
                                    still_invalid.append({
                                        "Excel Row": row_idx,
                                        "Rec. date": str(rec_date),
                                        "TTI model": raw_tti,
                                        "Rec. qty": raw_qty,
                                        "Error Reason": " | ".join(error_reasons)
                                    })
                                    
                            st.session_state.valid_rows.extend(new_valid)
                            st.session_state.invalid_rows = still_invalid
                            st.rerun()
                            
                    with col_fix2:
                        import io
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            df_invalid.to_excel(writer, index=False, sheet_name='Lỗi')
                        st.download_button("⬇️ Download error list", buffer.getvalue(), "Loi.xlsx", use_container_width=True)
                else:
                    st.success("🎉 100% of raw data is valid and mapped correctly.")

                if valid_rows:
                    st.divider()
                    st.success(f"✅ {len(valid_rows)} valid rows ready to be added to the system.")
                    st.dataframe(pd.DataFrame(valid_rows), use_container_width=True, hide_index=True)
                    
                    if st.button("💾 Confirm & Save to Database", type="primary"):
                        add_report_qty(valid_rows)
                        st.success("✅ Successfully saved!")
                        st.balloons()
                        
                        st.session_state.upload_scanned = False
                        st.session_state.valid_rows = []
                        st.session_state.invalid_rows = []
                        st.rerun()

    # ================= 5. GIAO DIỆN CHÍNH =================
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns([2, 2, 2, 2, 1]) 
    with col_m1:
        if st.button("➕ Single Add", type="primary", use_container_width=True):
            modal_single_report()
    with col_m2:
        if st.button("➕➕➕ Bulk Add", type="secondary", use_container_width=True):
            modal_bulk_report()
    with col_m3:
        if st.button("📥 Upload Excel", type="secondary", use_container_width=True):
            modal_upload_excel()
    with col_m4:
        pass
    with col_m5:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.session_state.rep_filters = {
                "start_date": date.today() - timedelta(days=30),
                "end_date": date.today(),
                "search": "",
                "ort": ""
            }
            st.rerun()

    if "rep_filters" not in st.session_state:
        st.session_state.rep_filters = {
            "start_date": date.today() - timedelta(days=30),
            "end_date": date.today(),
            "search": "",
            "ort": ""
        }

    st.divider()
    col_title, col_btn = st.columns([4, 1])
    st.markdown("""
    <style>
    .alert-header-v2-wrapper {
    filter: drop-shadow(4px 4px 0px rgba(0, 0, 0, 0.2));
    margin-bottom: 10px;
    margin-top: 0px;
    }
    .alert-header-v2 {
        background-color: #EBE600;
        color: #000000;
        padding: 10px 25px; 
        font-size: 22px;
        font-weight: 800;
        clip-path: polygon(20px 0, 100% 0, 100% calc(100% - 20px), calc(100% - 20px) 100%, 0 100%, 0 20px);
        margin-bottom: 1px;
        display: inline-flex; 
        align-items: center;
        gap: 10px;
        width: fit-content; 
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

    col_date1, col_date2 = st.columns(2)
    with col_date1:
        start_date = st.date_input("From Date:", value=st.session_state.rep_filters["start_date"], key="rep_start_date")
        st.session_state.rep_filters["start_date"] = start_date
    with col_date2:
        end_date = st.date_input("To Date:", value=st.session_state.rep_filters["end_date"], key="rep_end_date")
        st.session_state.rep_filters["end_date"] = end_date

    df_report = get_report_qty(start_date, end_date)

    if not df_report.empty:
        db_columns = ["ort_model", "tti_model", "rec_date", "rec_qty"]
        existing_cols = [col for col in db_columns if col in df_report.columns]
        df_display = df_report[existing_cols].rename(columns={
            "ort_model": "ORT model",
            "tti_model": "TTI model",
            "rec_date": "Rec. date",
            "rec_qty": "Rec. qty"
        })
    else:
        df_display = pd.DataFrame(columns=["ORT model", "TTI model", "Rec. date", "Rec. qty"])

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        search_query = st.text_input("Search reports...", value=st.session_state.rep_filters["search"], key="rep_search")
        st.session_state.rep_filters["search"] = search_query
    with col_f2:
        filter_ort = st.text_input("Filter by ORT model", value=st.session_state.rep_filters["ort"], key="rep_ort")
        st.session_state.rep_filters["ort"] = filter_ort

    if not df_display.empty:
        if search_query:
            mask = df_display.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
            df_display = df_display[mask]
        if filter_ort:
            df_display = df_display[df_display["ORT model"].str.contains(filter_ort, case=False, na=False)]

    if not df_display.empty:
        df_display.insert(0, "No.", range(1, len(df_display) + 1))
        st.caption(f"Displaying **{len(df_display)}** records in the selected date range.")
        st.dataframe(df_display, use_container_width=True, hide_index=True, height=500)
    else:
        st.info("ℹ️ No production reports found in the selected date range.")