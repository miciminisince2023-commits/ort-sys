import streamlit as st
import pandas as pd
from database.db_helper import save_diary_task, get_diary_tasks, update_diary_task_status
from database.ui_helper import show_loader, hide_loader, set_goku_background

def render(df_power_tool=None):
    run_id = show_loader(sub_text="Loading Handbook...")
    set_goku_background()
    # --- HEADER ---
    st.markdown("""
    <style>
    .module-header-wrapper { filter: drop-shadow(4px 4px 0px rgba(0, 0, 0, 0.2)); margin-bottom: 25px; margin-top: 30px; }
    .module-header { background-color: #EBE600; color: #000000; padding: 15px 25px; font-size: 35px; font-weight: 800; clip-path: polygon(25px 0, 100% 0, 100% calc(100% - 25px), calc(100% - 25px) 100%, 0 100%, 0 25px); text-transform: uppercase; }
    </style>
    <div class="module-header-wrapper"><div class="module-header">
    <h2 style='text-align: center; color: #000000; background-color: #EBE600; padding: 10px; margin: 0;'> 👅 H A N D B O O K 👅</h2>
    </div></div>
    """, unsafe_allow_html=True)

    tab_diary, = st.tabs(["📓 Task Diary"])
    
    with tab_diary:
        st.markdown("### 📝 Log New Task / Issue")
        
        with st.form("diary_form", clear_on_submit=True):
            title = st.text_input("Task Title", placeholder="e.g., Follow up with Supplier on D4, Review NCR form...")
            content = st.text_area("Description", placeholder="Enter details to track...", height=100)
            
            col1, col2 = st.columns(2)
            with col1:
                priority = st.selectbox("Priority", ["Normal", "Important", "Urgent"])
            with col2:
                status = st.selectbox("Status", ["Pending", "In Progress", "Completed", "Cancelled"])
            
            if st.form_submit_button("💾 Save Task", type="primary"):
                if title:
                    # GỌI HÀM API SUPABASE THẬT
                    success, msg = save_diary_task(title, content, priority, status)
                    if success:
                        st.success("✅ Task saved successfully!") 
                        st.rerun() # Ép tải lại trang ngay lập tức để bảng dữ liệu bên dưới cập nhật
                    else:
                        st.error(f"❌ Error saving task: {msg}")
                else:
                    st.error("⚠️ Please enter a Task Title!")
                
        st.divider()
        st.markdown("**📌 Recent Tasks:**")
        
        # --- LẤY DỮ LIỆU THẬT TỪ DATABASE ---
        raw_tasks = get_diary_tasks()
        
        if not raw_tasks:
            st.info("No tasks recorded yet. Create your first task above!")
        else:
            df_diary = pd.DataFrame(raw_tasks)
            
            # Format lại cột thời gian cho đẹp (bỏ bớt múi giờ rườm rà)
            df_diary["created_at"] = pd.to_datetime(df_diary["created_at"]).dt.strftime('%Y-%m-%d %H:%M')
            
            # Đổi tên cột chuẩn xác để hiển thị ra UI
            df_diary = df_diary.rename(columns={
                "created_at": "Created Date",
                "title": "Title",
                "priority": "Priority",
                "status": "Status",
                "description": "Description"
            })
            
            # Chỉ hiển thị các cột quan trọng ra UI (ẩn cột ID và Description để tránh bảng bị quá dài)
            cols_to_show = ["Created Date", "Title", "Description", "Priority", "Status"]
            
            st.dataframe(df_diary[cols_to_show], use_container_width=True, hide_index=True)
            # ==========================================
            # UPDATE TASK STATUS SECTION
            # ==========================================
            st.markdown("<hr style='margin-top: 30px; margin-bottom: 20px;'>", unsafe_allow_html=True)
            st.markdown("### 🔄 Update Task Status")
            
            # 1. Extract ID and create display list for Selectbox
            # Display format: "[2026-10-12] Follow up D4 materials"
            task_mapping = {f"[{row['Created Date']}] {row['Title']}": row['id'] for _, row in df_diary.iterrows()}
            
            # 2. Update form
            with st.form("update_status_form"):
                u_col1, u_col2 = st.columns([3, 1])
                with u_col1:
                    # Dropdown to select the Task to update
                    selected_task_label = st.selectbox("Select Task to update", options=list(task_mapping.keys()))
                with u_col2:
                    # Dropdown for the new status
                    new_status = st.selectbox("New Status", ["Pending", "In Progress", "Completed", "Cancelled"])
                    
                submit_update = st.form_submit_button("🔄 Update Status", type="primary", use_container_width=True)
                
                if submit_update:
                    if selected_task_label:
                        # Get the real ID from the mapping dictionary
                        task_id = task_mapping[selected_task_label]
                        
                        # CALL SUPABASE API TO UPDATE
                        success, msg = update_diary_task_status(task_id, new_status)
                        if success:
                            st.success("✅ Status updated successfully!")
                            st.rerun() # Reload to update the table immediately
                        else:
                            st.error(f"❌ Update failed: {msg}")

    hide_loader(run_id=run_id)