import streamlit as st
from supabase import create_client, Client
import pandas as pd
import datetime
import math

# ==========================================
# 1. KHỞI TẠO KẾT NỐI
# ==========================================
# Sử dụng @st.cache_resource để Streamlit chỉ kết nối 1 lần duy nhất, tránh giật lag
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# ==========================================
# 2. CÁC HÀM XỬ LÝ MASTER MODEL (TOOL & BATTERY)
# ==========================================
def get_master_models():
    """Lấy toàn bộ danh sách Master Model"""
    # Thêm .limit(10000) để phá giới hạn 1000 dòng mặc định của Supabase
    response = supabase.table("master_models").select("*").limit(10000).execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame(columns=["ort_model", "model_name", "category", "pic", "product_type", "created_at"])

def add_master_model(data_dict):
    """Thêm mới 1 Model"""
    response = supabase.table("master_models").insert(data_dict).execute()
    return response

# ==========================================
# 3. CÁC HÀM XỬ LÝ REPORT QTY
# ==========================================
@st.cache_data(ttl=600)
def get_report_qty(start_date=None, end_date=None, all_time=False):
    # Nếu không yêu cầu lấy toàn bộ, áp dụng bộ lọc 30 ngày
    if not all_time:
        if not start_date or not end_date:
            from datetime import date, timedelta
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            
        start_str = start_date.strftime("%Y-%m-%d") if hasattr(start_date, 'strftime') else start_date
        end_str = end_date.strftime("%Y-%m-%d") if hasattr(end_date, 'strftime') else end_date

    all_data = []
    start = 0
    step = 1000
    
    while True:
        query = supabase.table("report_qty").select("*")
        
        # Chỉ gắn điều kiện lọc ngày nếu không bật all_time
        if not all_time:
            query = query.gte("rec_date", start_str).lte("rec_date", end_str)
            
        response = query.range(start, start + step - 1).execute()
        
        if not response.data:
            break
            
        all_data.extend(response.data)
        
        if len(response.data) < step:
            break
            
        start += step
        
    if all_data:
        return pd.DataFrame(all_data)
    return pd.DataFrame(columns=["id", "ort_model", "tti_model", "rec_date", "rec_qty", "created_at"])

def add_report_qty(data_list):
    """Thêm mới sản lượng (Hỗ trợ truyền vào 1 list để Add hàng loạt)"""
    response = supabase.table("report_qty").insert(data_list).execute()
    return response

# ==========================================
# 4. CÁC HÀM XỬ LÝ ST REQUEST (Đã fix chuẩn phân trang)
# ==========================================
def get_st_requests():
    all_data = []
    start = 0
    step = 1000
    
    while True:
        # BẮT BUỘC PHẢI CÓ .order() THÌ PHÂN TRANG .range() MỚI KHÔNG BỊ TRÙNG HOẶC SÓT DỮ LIỆU
        response = (
            supabase.table("st_requests")
            .select("*")
            .order("req_id", desc=False)  # Sắp xếp theo mã request tăng dần để phân trang chuẩn xác
            .range(start, start + step - 1)
            .execute()
        )
        
        if not response.data:
            break
            
        all_data.extend(response.data)
        
        # Nếu số dòng trả về ít hơn 1000 -> Đã kéo hết toàn bộ dữ liệu
        if len(response.data) < step:
            break
            
        start += step
        
    if all_data:
        #return pd.DataFrame(all_data)
        df = pd.DataFrame(all_data)
        
        # --- LOGIC TÍNH REQ. DURATION ĐỘNG (LIVE AGING) ---
        temp_req = pd.to_datetime(df['req_date'], errors='coerce')
        temp_end = pd.to_datetime(df['end_date'], errors='coerce')
        today = pd.to_datetime('today').normalize() # Lấy mốc ngày hiện tại (không lấy giờ)
        
        # Nếu dòng nào chưa có End date (tức là giá trị NaT), tự động thay thế bằng Today
        calc_end = temp_end.fillna(today)
        
        # Công thức: (End Date hoặc Today) - Req Date
        df['req_duration'] = (calc_end - temp_req).dt.days.fillna(0).astype(int)
        # --------------------------------------------------
        
        return df
        
    # Trả về DataFrame rỗng với các cột chuẩn nếu không có dữ liệu
    return pd.DataFrame(columns=[
        "req_id", "req_date", "tti_model", "ort_model", "req_qty", 
        "sam_job", "cb_f", "scp_f", "dr_f", "item_test", 
        "start_date", "end_date", "test_result", "req_status", "req_duration"
    ])

def add_st_request(data_dict):
    response = supabase.table("st_requests").insert(data_dict).execute()
    return response

def update_st_request(req_id, data_dict):
    """Cập nhật thông tin Request (khi Edit)"""
    response = supabase.table("st_requests").update(data_dict).eq("req_id", req_id).execute()
    return response

    # --- SETTING PREFIX ---
def get_setting_prefix():
    try:
        response = supabase.table("setting_prefix").select("*").execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame(columns=["prefix", "mapped"])
    except:
        return pd.DataFrame(columns=["prefix", "mapped"])

def add_setting_prefix(data):
    try:
        supabase.table("setting_prefix").insert(data).execute()
    except Exception as e:
        print(f"Error adding prefix: {e}")

# --- SETTING DROPDOWNS (Model Names, Categories, P.I.C) ---
def get_setting_dropdowns(dropdown_type):
    try:
        response = supabase.table("setting_dropdowns").select("*").eq("type", dropdown_type).execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame(columns=["value"])
    except:
        return pd.DataFrame(columns=["value"])

def add_setting_dropdown(dropdown_type, value):
    try:
        supabase.table("setting_dropdowns").insert({"type": dropdown_type, "value": value}).execute()
    except Exception as e:
        print(f"Error adding dropdown: {e}")

# --- SETTING TIER RULES ---
def get_tier_rules():
    try:
        response = supabase.table("setting_rules").select("*").execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame(columns=["max_fg_accum", "req_samples"])
    except:
        return pd.DataFrame(columns=["max_fg_accum", "req_samples"])

# --- SETTING DYNAMIC RULE ---
def get_dynamic_rule():
    try:
        response = supabase.table("setting_dynamic_rule").select("*").execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame(columns=["over_m", "step", "add_val"])
    except:
        return pd.DataFrame(columns=["over_m", "step", "add_val"])

# --- authenticate ---
def authenticate_user(username, password):
    """
    Kiểm tra thông tin đăng nhập từ bảng users trên Supabase.
    Trả về dictionary chứa thông tin user nếu đúng, ngược lại trả về None.
    """
    try:
        response = supabase.table("users").select("*").eq("username", username).eq("password", password).execute()
        data = response.data
        if data and len(data) > 0:
            return data[0]
        return None
    except Exception as e:
        print(f"Authentication error: {e}")
        return None


@st.cache_data(ttl=600)
def get_processed_power_tool_data():
    # 1. Kéo toàn bộ dữ liệu cần thiết từ Database thay vì dùng session_state
    df_master = get_master_models()
    df_report = get_report_qty(all_time=True)
    
    # Đổi tên cột ort_model thành "ORT model" cho khớp với logic bên dưới
    if not df_master.empty and "ort_model" in df_master.columns:
        df_master = df_master.rename(columns={"ort_model": "ORT model"})
        
    df_show = df_master.copy()
    
    # ================= BƯỚC THIẾU: TÍNH FG ACCUM =================
    if not df_report.empty and "ort_model" in df_report.columns and "rec_qty" in df_report.columns:
        # Ép kiểu số để tính tổng an toàn
        df_report["rec_qty"] = pd.to_numeric(df_report["rec_qty"], errors="coerce").fillna(0)
        
        # Nhóm theo model và tính tổng
        report_grouped = df_report.groupby("ort_model")["rec_qty"].sum().reset_index()
        report_grouped = report_grouped.rename(columns={"ort_model": "ORT model", "rec_qty": "FG accum"})
        
        # Nối vào bảng chính df_show
        df_show = pd.merge(df_show, report_grouped, on="ORT model", how="left")
        df_show["FG accum"] = df_show["FG accum"].fillna(0).astype(int)
    else:
        df_show["FG accum"] = 0
    
# ================= BỔ SUNG ĐỊNH NGHĨA BIẾN =================
    
    # 1. Kéo dữ liệu S&T BẰNG HÀM ĐÃ PHÂN TRANG (Không dùng select().execute() trực tiếp nữa)
    df_st_raw = get_st_requests()
    
    if not df_st_raw.empty:
        df_st = df_st_raw.rename(columns={
            "req_status": "Req. status",
            "ort_model": "ORT model",
            "req_qty": "Req. qty",
            "start_date": "Start date",
            "test_result": "Test result",
            "req_id": "Req. id"
        })
    else:
        # BẮT BUỘC: Khai báo khung rỗng có sẵn tên cột nếu DB chưa có dữ liệu
        df_st = pd.DataFrame(columns=["Req. status", "ORT model", "Req. qty", "Start date", "Test result", "Req. id"])

    # 2. Kéo dữ liệu Tier Rules

    # 2. Kéo dữ liệu Tier Rules
    response_tier = supabase.table("setting_rules").select("*").execute()
    df_tier_rules = pd.DataFrame(response_tier.data) if response_tier.data else pd.DataFrame()

    # 3. Kéo dữ liệu Dynamic Rules
    response_dyn = supabase.table("setting_dynamic_rule").select("*").execute()
    df_dynamic_rule = pd.DataFrame(response_dyn.data) if response_dyn.data else pd.DataFrame()
    # ==========================================================

    # ================= CALCULATE REQ. & NEXT QTY =================
    def calculate_sample_req(fg_qty):
        if fg_qty <= 0: return 0
        # Thay thế kiểm tra session_state bằng biến df_tier_rules vừa kéo
        if not df_tier_rules.empty:
            tiers = df_tier_rules.sort_values(by="max_fg_accum")
            for _, row in tiers.iterrows():
                if fg_qty <= row["max_fg_accum"]:
                    return int(row["req_samples"])
            
            max_tier = tiers["max_fg_accum"].max()
            max_req = tiers.loc[tiers["max_fg_accum"] == max_tier, "req_samples"].iloc[0]
            
            if not df_dynamic_rule.empty:
                dyn = df_dynamic_rule.iloc[0]
                over_m = dyn["over_m"]
                step = dyn["step"]
                add_val = dyn["add_val"]
                
                if fg_qty > over_m and step > 0:
                    return int(max_req + math.floor((fg_qty - over_m - 1) / step) + add_val)
                    
        return 5

    def calculate_next_test_qty(fg_qty):
        if not df_tier_rules.empty:
            tiers = df_tier_rules.sort_values(by="max_fg_accum")
            for _, row in tiers.iterrows():
                if fg_qty < row["max_fg_accum"]:
                    return int(row["max_fg_accum"])
                    
        if not df_dynamic_rule.empty:
            dyn = df_dynamic_rule.iloc[0]
            over_m = dyn["over_m"]
            step = dyn["step"]
            if fg_qty >= over_m and step > 0:
                return int(over_m + (math.floor((fg_qty - over_m) / step) + 1) * step)
        return 75000

    if "FG accum" in df_show.columns:
        df_show["Req."] = df_show["FG accum"].apply(calculate_sample_req)
        df_show["Next test qty"] = df_show["FG accum"].apply(calculate_next_test_qty)

   # ================= UPDATE AVAIL & LATEST FROM ST =================
    if not df_st.empty:
        df_st_temp = df_st.copy()
        
        # 1. Đổi tên cột từ database cho khớp với bảng hiển thị (nếu chưa có)
        if "ort_model" in df_st_temp.columns and "ORT model" not in df_st_temp.columns:
            df_st_temp = df_st_temp.rename(columns={"ort_model": "ORT model"})
        if "req_qty" in df_st_temp.columns and "Req. qty" not in df_st_temp.columns:
            df_st_temp = df_st_temp.rename(columns={"req_qty": "Req. qty"})
        if "req_id" in df_st_temp.columns and "Req. id" not in df_st_temp.columns:
            df_st_temp = df_st_temp.rename(columns={"req_id": "Req. id"})

        # 2. Loại bỏ các dòng không có ORT model (tránh lỗi gom nhóm "NAN" hoặc None)
        df_st_temp = df_st_temp.dropna(subset=["ORT model"])
        df_st_temp = df_st_temp[df_st_temp["ORT model"].astype(str).str.strip() != ""]
        df_st_temp = df_st_temp[df_st_temp["ORT model"].astype(str).str.upper() != "NAN"]

        # 3. Chuẩn hóa giá trị ORT model (Xóa khoảng trắng thừa, viết hoa toàn bộ)
        df_st_temp["ORT model"] = df_st_temp["ORT model"].astype(str).str.strip().str.upper()
        
        if "ORT model" in df_show.columns:
            df_show["ORT model"] = df_show["ORT model"].astype(str).str.strip().str.upper()

        # 4. Ép kiểu cột số lượng về dạng số an toàn
        df_st_temp["Req. qty"] = pd.to_numeric(df_st_temp["Req. qty"], errors="coerce").fillna(0)

        # 5. Tính tổng Avail. theo từng ORT model chuẩn xác
        avail_sums = df_st_temp.groupby("ORT model")["Req. qty"].sum().to_dict()
        df_show["Avail."] = df_show["ORT model"].map(avail_sums).fillna(0).astype(int)
        
        # 6. Lấy ngày và kết quả test gần nhất
        sort_col = "Req. id" if "Req. id" in df_st_temp.columns else ("req_id" if "req_id" in df_st_temp.columns else None)
        if sort_col:
            latest_st = df_st_temp.sort_values(by=sort_col).drop_duplicates(subset=["ORT model"], keep="last")
        else:
            latest_st = df_st_temp.drop_duplicates(subset=["ORT model"], keep="last")
            
        date_col = "Start date" if "Start date" in latest_st.columns else ("start_date" if "start_date" in latest_st.columns else None)
        result_col = "Test result" if "Test result" in latest_st.columns else ("test_result" if "test_result" in latest_st.columns else None)
        
        latest_date_map = latest_st.set_index("ORT model")[date_col].to_dict() if date_col else {}
        latest_result_map = latest_st.set_index("ORT model")[result_col].to_dict() if result_col else {}
        
        df_show["Latest test date"] = df_show["ORT model"].map(latest_date_map).fillna("-")
        
        def map_result(val):
            return val if pd.notna(val) and val != "" else "Pending"
        df_show["Latest result"] = df_show["ORT model"].map(latest_result_map).apply(map_result)
    else:
        df_show["Avail."] = 0
        df_show["Latest test date"] = "-"
        df_show["Latest result"] = "Pending"

    # ================= CALCULATE GAP, STATUS & ACTION =================
    df_show["Gap"] = df_show["Req."] - df_show["Avail."]

    # ================= LOGIC TỰ ĐỘNG GHI NHỚ NGÀY BẮT ĐẦU SHORTAGE =================
    from datetime import date
    today_str = date.today().strftime("%Y-%m-%d")
    
    # Chỉ chạy logic nếu cột đã được tạo trên Supabase
    if "shortage_start_date" in df_show.columns:
        for index, row in df_show.iterrows():
            ort = row["ORT model"]
            gap = row["Gap"]
            current_start = row["shortage_start_date"] 

            # Hàm nhỏ kiểm tra xem ô ngày đang bị trống hay không
            is_empty = pd.isna(current_start) or str(current_start).strip() in ["", "None", "NaT"]

            # Trường hợp 1: Mới rớt vào Shortage -> Ghi nhận ngày hôm nay
            if gap > 0 and is_empty:
                try:
                    supabase.table("master_models").update({"shortage_start_date": today_str}).eq("ort_model", ort).execute()
                    df_show.at[index, "shortage_start_date"] = today_str 
                except Exception as e:
                    pass
            
            # Trường hợp 2: Đã hết Shortage (Avail bù đủ Req) -> Xóa ngày bấm giờ
            elif gap <= 0 and not is_empty:
                try:
                    supabase.table("master_models").update({"shortage_start_date": None}).eq("ort_model", ort).execute()
                    df_show.at[index, "shortage_start_date"] = None
                except Exception as e:
                    pass

        # Tính toán ra số ngày thực tế để hiển thị
        temp_start = pd.to_datetime(df_show["shortage_start_date"], errors='coerce')
        df_show["Shortage days val"] = (pd.to_datetime('today').normalize() - temp_start).dt.days
        df_show["Shortage days"] = df_show["Shortage days val"].apply(lambda x: f"{int(x)} ngày" if pd.notna(x) else "")
    else:
        df_show["Shortage days val"] = 0
        df_show["Shortage days"] = ""
    # ===============================================================================

    df_show["Sample Status"] = df_show["Gap"].apply(lambda gap: "Shortage" if gap > 0 else "Sufficient")
    df_show["Action required"] = df_show["Gap"].apply(lambda gap: "Request Sample" if gap > 0 else "Monitor")

    return df_show