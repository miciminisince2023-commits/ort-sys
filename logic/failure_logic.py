def get_failure_mapping():
    """
    Hàm lưu trữ và trả về toàn bộ logic phân nhánh của Root Cause -> Failure Group, Code, Mode.
    Sau này muốn thêm, xóa hoặc sửa mã lỗi, chỉ cần chỉnh sửa ở duy nhất hàm này.
    """
    return {
        "Man": {
            "group": "M1",
            "codes": {
                "M1-01": "Assembly Appearance Issue",
                "M1-02": "Assembly Function Issue",
                "M1-03": "Use wrong WI",
                "M1-04": "Worker not yet training / certificate",
                "M1-05": "PMC/WH provide wrong part number",
                "M1-06": "Not follow process"
            }
        },
        "Material": {
            "group": "M2",
            "codes": {
                "M2-01": "Component Appearance Issue",
                "M2-02": "Out of spec",
                "M2-03": "Component Function Issue",
                "M2-04": "Supplier delivery wrong part"
            }
        },
        "Machine": {
            "group": "M3",
            "codes": {
                "M3-01": "Fixture issue",
                "M3-02": "Machine issue",
                "M3-03": "No calibration"
            }
        },
        "Method": {
            "group": "M4",
            "codes": {
                "M4-01": "WI not clearly",
                "M4-02": "WI incorrect"
            }
        },
        "Design": {
            "group": "D5",
            "codes": {
                "D5-01": "BOM/ECO/TD issue",
                "D5-02": "Assembly issue"
            }
        },
        "Under investigation": {
            "group": "U6",
            "codes": {
                "U6-01": "Under investigation"
            }
        }
    }