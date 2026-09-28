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
        for index, row in df_prefix.iterrows():
            if row["3 số đầu (Prefix)"] == prefix:
                mapped_val = row["Mã đổi (Mapped)"]
                break
                
        return f"{mapped_val}{middle}"
        
    return "Mã không hợp lệ"