def convert_tti_to_ort(tti_model, df_prefix):
    """
    Hàm cắt 3 số đầu của TTI Model và tra cứu trong bảng Prefix
    để tạo thành ORT Model.
    """
    tti_model = str(tti_model).strip()
    
    if len(tti_model) >= 6:
        prefix = tti_model[0:3]
        middle = tti_model[3:6]
        
        mapped_val = prefix
        
        if not df_prefix.empty:
            # Tự động nhận diện tên cột: Ưu tiên "prefix"/"mapped", nếu không có thì lấy 2 cột đầu tiên
            col_prefix = "prefix" if "prefix" in df_prefix.columns else df_prefix.columns[0]
            col_mapped = "mapped" if "mapped" in df_prefix.columns else df_prefix.columns[1]
            
            for index, row in df_prefix.iterrows():
                # Dùng hàm .get() để chống văng lỗi KeyError
                if str(row.get(col_prefix, "")) == prefix:
                    mapped_val = str(row.get(col_mapped, ""))
                    break
                    
        return f"{mapped_val}{middle}"
        
    return "Invalid code"