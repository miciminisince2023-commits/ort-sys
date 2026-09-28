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
            📦 PRODUCTION - REPORT QTY
</h2></div>
</div>
""", unsafe_allow_html=True)

    # ================= 2. FETCH DATA TỪ DATABASE =================
    # Kéo bảng quy tắc Prefix để tự động quy đổi TTI -> ORT
    df_prefix_raw = get_setting_prefix()
    if not df_prefix_raw.empty and "prefix" in df_prefix_raw.columns and "mapped" in df_prefix_raw.columns:
        df_prefix = df_prefix_raw[["prefix", "mapped"]].rename(columns={"prefix": "3 số đầu (Prefix)", "mapped": "Mã đổi (Mapped)"})
    else:
        df_prefix = pd.DataFrame([["011", "A1"]], columns=["3 số đầu (Prefix)", "Mã đổi (Mapped)"])

    # ================= 3. MODAL: SINGLE REPORT =================
    @st.dialog("Add Production Report (Single)", width="large")
    def modal_single_report():
        st.markdown("💡 **Auto-conversion Rule:** Enter the TTI Model. The system will automatically convert and lock the correct ORT Model.")
        
        rec_date = st.date_input("Received Date (Rec. date)", value=date.today())
        tti_input = st.text_input("Enter TTI Model (9 digits) *", max_chars=9, placeholder="e.g. 011123456 or 130123456")
        
        # Logic tự động quy đổi ORT Model từ TTI Model
        auto_ort = ""
        if len(tti_input) >= 3:
            if tti_input.startswith("130") and len(tti_input) == 9:
                auto_ort = tti_input 
            else:
                auto_ort = convert_tti_to_ort(tti_input, df_prefix)

        st.text_input("ORT Model (Auto-converted) *", value=auto_ort, disabled=True, help="Automatically mapped via prefix conversion or battery rule.")
        rec_qty = st.number_input("Received Quantity (Rec. qty) *", min_value=1, step=1, value=1000)
        
        st.divider()
        if st.button("Save Report", type="primary", use_container_width=True):
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
        st.markdown("💡 **Interactive Bulk Paste:** Just paste your **Rec. date**, **TTI model**, and **Rec. qty**. The system will automatically map the ORT model in the background.")
        
        if "df_bulk_temp" not in st.session_state:
            st.session_state.df_bulk_temp = pd.DataFrame(
                [[str(date.today()), "", 1000]], 
                columns=["Rec. date", "TTI model", "Rec. qty"]
            )
            
        st.caption("Instructions: Paste rows or type directly. System handles ORT conversion automatically.")
        
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
                for _, row in edited_bulk.iterrows():
                    tti = str(row["TTI model"]).strip()
                    r_date = str(row["Rec. date"]).strip()
                    qty = row["Rec. qty"]
                    
                    if tti and qty > 0:
                        # Tự động quy đổi ORT ngầm phía sau
                        if tti.startswith("130") and len(tti) == 9:
                            calculated_ort = tti
                        else:
                            calculated_ort = convert_tti_to_ort(tti, df_prefix)
                            
                        records_to_add.append({
                            "ort_model": calculated_ort,
                            "tti_model": tti,
                            "rec_date": r_date if r_date else str(date.today()),
                            "rec_qty": int(qty)
                        })
                
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
        st.markdown("💡 **Tải lên file Excel:** Hệ thống sẽ tự động quét, quy đổi TTI sang ORT và phân loại dữ liệu hợp lệ/lỗi.")
        
        # 1. KHỞI TẠO BỘ NHỚ LƯU KẾT QUẢ QUÉT
        if "upload_scanned" not in st.session_state:
            st.session_state.upload_scanned = False
            st.session_state.valid_rows = []
            st.session_state.invalid_rows = []

        df_master = get_master_models()
        valid_ort_models = set(df_master["ort_model"].astype(str).str.strip().str.upper()) if not df_master.empty else set()
        
        # Xóa bộ nhớ nếu người dùng tắt file / chọn file mới
        uploaded_file = st.file_uploader("Chọn file Excel (Hỗ trợ .xlsx, .xls)", type=["xlsx", "xls"])
        if not uploaded_file:
            st.session_state.upload_scanned = False

        if uploaded_file:
            try:
                df_raw = pd.read_excel(uploaded_file)
            except Exception as e:
                st.error(f"❌ Không thể đọc file. Lỗi: {e}")
                return
            
            cols = df_raw.columns.tolist()
            col1, col2, col3 = st.columns(3)
            with col1: date_col = st.selectbox("Cột Ngày", cols, index=0)
            with col2: tti_col = st.selectbox("Cột Mã TTI", cols, index=1 if len(cols) > 1 else 0)
            with col3: qty_col = st.selectbox("Cột Số lượng", cols, index=2 if len(cols) > 2 else 0)

            # ================= CẬP NHẬT: XỬ LÝ LOGIC QUÉT =================
            if st.button("🔍 Quét & Phân tích Dữ liệu", type="primary", use_container_width=True):
                valid_rows = []
                invalid_rows = []

                for index, row in df_raw.iterrows():
                    raw_date = row[date_col]
                    raw_tti = str(row[tti_col]).strip().upper()
                    raw_qty = row[qty_col]
                    
                    error_reasons = []
                    ort_converted = ""

                    # Quét Số lượng
                    try:
                        qty = int(pd.to_numeric(raw_qty))
                        if qty <= 0: error_reasons.append("Số lượng <= 0")
                    except:
                        error_reasons.append("Số lượng không phải số")
                        qty = 0

                    # Quét Ngày
                    try:
                        rec_date = pd.to_datetime(raw_date).date()
                    except:
                        error_reasons.append("Sai định dạng ngày")
                        rec_date = date.today()

                    # Quét TTI & ORT
                    if len(raw_tti) >= 3:
                        if raw_tti.startswith("130") and len(raw_tti) == 9:
                            ort_converted = raw_tti
                        else:
                            ort_converted = convert_tti_to_ort(raw_tti, df_prefix)
                    else:
                        error_reasons.append("Mã TTI quá ngắn")

                    if not ort_converted:
                        error_reasons.append("Sai Prefix")
                    elif ort_converted not in valid_ort_models:
                        error_reasons.append(f"Mã ORT ({ort_converted}) không tồn tại")

                    # Phân loại
                    if len(error_reasons) == 0:
                        valid_rows.append({
                            "ort_model": ort_converted,
                            "tti_model": raw_tti,
                            "rec_date": str(rec_date),
                            "rec_qty": qty
                        })
                    else:
                        invalid_rows.append({
                            "Dòng Excel": index + 2,
                            "Rec. date": str(rec_date), # FIX: Giữ lại ngày gốc
                            "TTI model": raw_tti,
                            "Rec. qty": raw_qty,
                            "Lý do lỗi": " | ".join(error_reasons)
                        })

                st.session_state.valid_rows = valid_rows
                st.session_state.invalid_rows = invalid_rows
                st.session_state.upload_scanned = True

            # ================= CẬP NHẬT: HIỂN THỊ KẾT QUẢ & QUÉT LẠI =================
            if st.session_state.upload_scanned:
                st.divider()
                valid_rows = st.session_state.valid_rows
                invalid_rows = st.session_state.invalid_rows

                if invalid_rows:
                    st.error(f"⚠️ Phát hiện {len(invalid_rows)} dòng lỗi!")
                    st.markdown("🛠️ **Sửa nhanh:** Nhấp đúp vào ô để sửa (Ngày, Mã, Số lượng). Dữ liệu sẽ không bị mất khi bạn gõ.")
                    
                    df_invalid = pd.DataFrame(invalid_rows)
                    edited_invalid_df = st.data_editor(
                        df_invalid, 
                        use_container_width=True, 
                        hide_index=True,
                        key="editor_invalid_rows"
                    )
                    
                    col_fix1, col_fix2 = st.columns(2)
                    with col_fix1:
                        if st.button("🔄 Quét lại các dòng đã sửa", use_container_width=True):
                            new_valid = []
                            still_invalid = []
                            
                            # Cải tiến: Khởi tạo list an toàn
                            df_master_refresh = get_master_models()
                            valid_ort_models_refresh = set(df_master_refresh["ort_model"].astype(str).str.strip().str.upper()) if not df_master_refresh.empty else set()
                            
                            for idx, row in edited_invalid_df.iterrows():
                                raw_tti = str(row["TTI model"]).strip().upper()
                                raw_qty = row["Rec. qty"]
                                raw_date = row["Rec. date"] # FIX: Lấy lại ngày vừa chỉnh sửa
                                row_idx = row["Dòng Excel"]
                                
                                error_reasons = []
                                ort_converted = ""
                                
                                # Kiểm tra Số lượng
                                try:
                                    qty = int(pd.to_numeric(raw_qty))
                                    if qty <= 0: error_reasons.append("Số lượng <= 0")
                                except:
                                    error_reasons.append("Số lượng không phải số")
                                    qty = 0
                                
                                # Kiểm tra Ngày
                                try:
                                    rec_date = pd.to_datetime(raw_date).date()
                                except:
                                    error_reasons.append("Sai định dạng ngày")
                                    rec_date = date.today()
                                    
                                # Kiểm tra TTI & ORT
                                if len(raw_tti) >= 3:
                                    if raw_tti.startswith("130") and len(raw_tti) == 9:
                                        ort_converted = raw_tti
                                    else:
                                        ort_converted = convert_tti_to_ort(raw_tti, df_prefix)
                                else:
                                    error_reasons.append("Mã TTI quá ngắn")
                                    
                                if not ort_converted:
                                    error_reasons.append("Sai Prefix")
                                elif ort_converted not in valid_ort_models_refresh:
                                    error_reasons.append("Mã ORT không tồn tại")
                                    
                                # Phân loại lại
                                if len(error_reasons) == 0:
                                    new_valid.append({
                                        "ort_model": ort_converted,
                                        "tti_model": raw_tti,
                                        "rec_date": str(rec_date), # FIX: Trả lại ngày chính xác
                                        "rec_qty": qty
                                    })
                                else:
                                    still_invalid.append({
                                        "Dòng Excel": row_idx,
                                        "Rec. date": str(rec_date),
                                        "TTI model": raw_tti,
                                        "Rec. qty": raw_qty,
                                        "Lý do lỗi": " | ".join(error_reasons)
                                    })
                                    
                            st.session_state.valid_rows.extend(new_valid)
                            st.session_state.invalid_rows = still_invalid
                            #st.rerun()
                            
                    with col_fix2:
                        import io
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            df_invalid.to_excel(writer, index=False, sheet_name='Lỗi')
                        st.download_button("⬇️ Tải danh sách lỗi", buffer.getvalue(), "Loi.xlsx", use_container_width=True)
                else:
                    st.success("🎉 100% dữ liệu thô đều hợp lệ và khớp mã.")

                if valid_rows:
                    st.divider()
                    st.success(f"✅ {len(valid_rows)} dòng hợp lệ sẵn sàng đưa vào hệ thống.")
                    st.dataframe(pd.DataFrame(valid_rows), use_container_width=True, hide_index=True)
                    
                    if st.button("💾 Xác nhận Lưu vào Database", type="primary"):
                        # XÓA DẤU THĂNG KHI CHẠY THẬT
                        add_report_qty(valid_rows)
                        st.success("✅ Đã lưu thành công!")
                        st.balloons()
                        
                        # FIX: Dọn dẹp sạch sẽ Session State sau khi lưu
                        st.session_state.upload_scanned = False
                        st.session_state.valid_rows = []
                        st.session_state.invalid_rows = []
                        st.rerun()

    # ================= 5. GIAO DIỆN CHÍNH =================
    # Đổi tỷ lệ chia cột từ [2, 2, 6] thành [2, 2, 2, 2, 1] để có chỗ cho nút Upload
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns([2, 2, 2, 2, 1]) 
    with col_m1:
        if st.button("➕ Single Add", type="primary", use_container_width=True):
            modal_single_report()
    with col_m2:
        if st.button("➕➕➕ Bulk Add", type="secondary", use_container_width=True):
            modal_bulk_report()
    with col_m3:
        # Gọi nút Upload mới
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

   # --- 1. TẠO BỘ NHỚ LƯU TRỮ CHO REPORT QTY ---
    # Đảm bảo bạn đã import thư viện ở đầu file: from datetime import date, timedelta
    if "rep_filters" not in st.session_state:
        st.session_state.rep_filters = {
            "start_date": date.today() - timedelta(days=30),
            "end_date": date.today(),
            "search": "",
            "ort": ""
        }

    # --- 2. BỐ TRÍ TIÊU ĐỀ VÀ NÚT REFRESH ---
    st.divider()
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

    # --- 3. KHUNG BỘ LỌC THỜI GIAN (Có gắn bộ nhớ) ---
    col_date1, col_date2 = st.columns(2)
    with col_date1:
        start_date = st.date_input("From Date:", value=st.session_state.rep_filters["start_date"], key="rep_start_date")
        st.session_state.rep_filters["start_date"] = start_date
    with col_date2:
        end_date = st.date_input("To Date:", value=st.session_state.rep_filters["end_date"], key="rep_end_date")
        st.session_state.rep_filters["end_date"] = end_date

    # Lấy dữ liệu với tham số ngày đã chọn
    df_report = get_report_qty(start_date, end_date)

    # Chuẩn hóa tên cột ngay lập tức để chuẩn bị cho bộ lọc
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

    # --- 4. KHUNG TÌM KIẾM VÀ LỌC TEXT (Có gắn bộ nhớ) ---
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        search_query = st.text_input("Search reports...", value=st.session_state.rep_filters["search"], key="rep_search")
        st.session_state.rep_filters["search"] = search_query
    with col_f2:
        filter_ort = st.text_input("Filter by ORT model", value=st.session_state.rep_filters["ort"], key="rep_ort")
        st.session_state.rep_filters["ort"] = filter_ort

    # Xử lý logic lọc
    if not df_display.empty:
        if search_query:
            mask = df_display.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
            df_display = df_display[mask]
        if filter_ort:
            df_display = df_display[df_display["ORT model"].str.contains(filter_ort, case=False, na=False)]

    # Xử lý hiển thị bảng
    if not df_display.empty:
        df_display.insert(0, "No.", range(1, len(df_display) + 1))
        st.caption(f"Hiển thị **{len(df_display)}** bản ghi trong khoảng thời gian đã chọn.")
        st.dataframe(df_display, use_container_width=True, hide_index=True, height=500)
    else:
        st.info("ℹ️ No production reports found in the selected date range.")
