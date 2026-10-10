import streamlit as st
import pandas as pd
from supabase import create_client
from database.db_helper import (
    get_setting_prefix, add_setting_prefix,
    get_setting_dropdowns, add_setting_dropdown,
    get_tier_rules, get_dynamic_rule
)

def render(df_shared=None):
    # Khởi tạo Supabase client cho các thao tác cập nhật quy tắc
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
            ⚙️ SETTINGS MANAGEMENT
</h2></div>
</div>
""", unsafe_allow_html=True)

    # ================= 1. PREFIX CONVERSION RULES =================
    st.subheader("🔗 Prefix Conversion Rules")
    st.info("💡 **Rule:** The system extracts the first 3 digits of the TTI Model, matches them in this table to get the 'Mapped code', and combines them with the middle digits to form the ORT Model.")

    df_prefix_db = get_setting_prefix()
    if not df_prefix_db.empty and "prefix" in df_prefix_db.columns and "mapped" in df_prefix_db.columns:
        df_prefix = df_prefix_db[["prefix", "mapped"]].rename(columns={"prefix": "3 digits (Prefix)", "mapped": "Mapped code"})
    else:
        df_prefix = pd.DataFrame([["011", "A1"]], columns=["3 digits (Prefix)", "Mapped code"])

    col1, col2 = st.columns([1, 2])

    with col1:
        with st.form("form_add_prefix"):
            st.markdown("**➕ Add New Prefix Rule**")
            new_prefix = st.text_input("3 digits (e.g., 012)", max_chars=3)
            new_mapped = st.text_input("Mapped code (e.g., A2)")
            
            if st.form_submit_button("Save Rule", type="primary"):
                if new_prefix and new_mapped:
                    if not df_prefix.empty and new_prefix in df_prefix["3 digits (Prefix)"].values:
                        st.error(f"Prefix '{new_prefix}' already exists in the database!")
                    else:
                        add_setting_prefix([{"prefix": new_prefix, "mapped": new_mapped}])
                        st.success("Successfully added!")
                        st.rerun()
                else:
                    st.error("Please fill in all fields!")

    with col2:
        st.markdown("**📋 Current Prefix Rules List**")
        st.dataframe(df_prefix, use_container_width=True, hide_index=True)

    st.divider()

    # ================= 2. MASTER DROPDOWNS SETUP =================
    st.subheader("📋 Master Dropdowns Setup")

    def render_dropdown_section(title, dropdown_type):
        st.markdown(f"#### {title}")
        col_d1, col_d2 = st.columns([1, 2])
        
        df_drop = get_setting_dropdowns(dropdown_type)
        display_df = df_drop.rename(columns={"value": title}) if not df_drop.empty else pd.DataFrame(columns=[title])
        
        with col_d1:
            with st.form(f"form_add_{dropdown_type}"):
                st.markdown(f"**➕ Add New {title}**")
                new_val = st.text_input(f"Enter {title}")
                
                if st.form_submit_button("Save Data", type="primary"):
                    if new_val:
                        if not display_df.empty and new_val in display_df[title].values:
                            st.error("This data already exists!")
                        else:
                            add_setting_dropdown(dropdown_type, new_val)
                            st.success("Successfully added!")
                            st.rerun()
                    else:
                        st.error("Please enter data!")
                        
        with col_d2:
            st.markdown(f"**📋 List of {title}**")
            st.dataframe(display_df, width="stretch", hide_index=True)

    render_dropdown_section("Model Name", "model_name")
    st.divider()
    render_dropdown_section("Category", "category")
    st.divider()
    render_dropdown_section("P.I.C", "pic")
    st.divider()
    # --- THÊM ĐOẠN NÀY CHO REGION ---
    render_dropdown_section("Region", "region")
    st.divider()

    # ================= 3. SAMPLE REQUIREMENTS RULES =================
    st.subheader("📈 SRR")

    col_r1, col_r2 = st.columns([2, 2])

    with col_r1:
        st.markdown("**1. Static Tier Milestones**")
        st.info("Example: 1000 - 5 means from 0 to 1000 samples take 5 test units.")
        
        df_tier = get_tier_rules()
        if not df_tier.empty:
            df_tier_show = df_tier.rename(columns={"max_fg_accum": "Max FG Accum", "req_samples": "Req. Samples"})
        else:
            df_tier_show = pd.DataFrame([[1000, 5], [5000, 7]], columns=["Max FG Accum", "Req. Samples"])
        
        edited_tier = st.data_editor(
            df_tier_show,
            num_rows="dynamic",
            hide_index=True,
            width="stretch",
            key="editor_tier_rules"
        )
        
        if st.button("💾 Save Tier Rules", type="primary"):
            try:
                supabase.table("setting_rules").delete().neq("max_fg_accum", -1).execute()
                tier_rows = []
                for _, row in edited_tier.iterrows():
                    try:
                        m_acc = int(row["Max FG Accum"])
                        r_sam = int(row["Req. Samples"])
                        tier_rows.append({"max_fg_accum": m_acc, "req_samples": r_sam})
                    except:
                        pass
                if tier_rows:
                    supabase.table("setting_rules").insert(tier_rows).execute()
                st.success("✅ Tier rules saved to Cloud successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error saving tier rules: {e}")

    with col_r2:
        st.markdown("**2. Dynamic Rule for Exceeding Max Milestone**")
        st.info("Example: Exceeding 75000, every 30000 units adds 1 sample.")
        
        df_dyn = get_dynamic_rule()
        if not df_dyn.empty:
            df_dyn_show = df_dyn.rename(columns={"over_m": "Over Milestone", "step": "Step Increment", "add_val": "Add Value"})
        else:
            df_dyn_show = pd.DataFrame([[75000, 30000, 1]], columns=["Over Milestone", "Step Increment", "Add Value"])
            
        edited_dyn = st.data_editor(
            df_dyn_show,
            hide_index=True,
            width="stretch",
            key="editor_dynamic_rule"
        )
        
        if st.button("💾 Save Dynamic Rule", type="primary"):
            try:
                supabase.table("setting_dynamic_rule").delete().neq("over_m", -1).execute()
                dyn_rows = []
                for _, row in edited_dyn.iterrows():
                    try:
                        over = int(row["Over Milestone"])
                        step = int(row["Step Increment"])
                        add_v = int(row["Add Value"])
                        dyn_rows.append({"over_m": over, "step": step, "add_val": add_v})
                    except:
                        pass
                if dyn_rows:
                    supabase.table("setting_dynamic_rule").insert(dyn_rows).execute()
                st.success("✅ Dynamic rule saved to Cloud successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error saving dynamic rule: {e}")