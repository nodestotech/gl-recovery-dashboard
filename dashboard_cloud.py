import streamlit as st
import pandas as pd
import os
from datetime import datetime
from io import BytesIO

# Set page config
st.set_page_config(page_title="GL Recovery Dashboard - Cloud", layout="wide", initial_sidebar_state="expanded")

st.title("💰 GL Recovery Dashboard - Cloud Version")
st.markdown("---")

# ============= INFO BOX =============
with st.sidebar:
    st.header("📋 Instructions")
    st.info("""
    **How to use:**
    1. Upload your files below
    2. Select categories to filter
    3. Query employees
    4. Download reports
    
    **Files needed:**
    - GL_dump.xlsx
    - GL_Description.xlsx
    """)
    
    st.markdown("---")
    st.subheader("📤 Upload Your Files")

# ============= FILE UPLOAD SECTION =============
uploaded_gl_dump = st.sidebar.file_uploader(
    "Upload GL_dump.xlsx",
    type=['xlsx'],
    key="gl_dump_upload"
)

uploaded_gl_desc = st.sidebar.file_uploader(
    "Upload GL_Description.xlsx",
    type=['xlsx'],
    key="gl_desc_upload"
)

# ============= HELPER FUNCTIONS =============

def load_gl_dump_from_upload(file):
    """Load GL dump from uploaded file"""
    try:
        df = pd.read_excel(file)
        return df
    except:
        st.error("❌ Error reading GL dump file")
        return None

def load_gl_descriptions_from_upload(file):
    """Load GL descriptions from uploaded file"""
    try:
        df = pd.read_excel(file)
        gl_name_dict = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
        gl_category_dict = dict(zip(df.iloc[:, 0], df.iloc[:, 2])) if len(df.columns) >= 3 else {}
        return gl_name_dict, gl_category_dict
    except:
        st.error("❌ Error reading GL Description file")
        return {}, {}

def get_gl_name(gl_code, gl_dict):
    return gl_dict.get(gl_code, "Unknown GL")

def get_gl_category(gl_code, gl_cat_dict):
    return gl_cat_dict.get(gl_code, "Uncategorized")

def process_gl_data(df, gl_name_dict, gl_category_dict):
    """Process GL data"""
    df_copy = df.copy()
    df_copy.columns = range(len(df_copy.columns))
    
    gl_col = 1
    order_col = 6
    amount_col = 12
    
    df_copy['GL_Code'] = df_copy[gl_col]
    df_copy['Order'] = df_copy[order_col]
    df_copy['Amount'] = pd.to_numeric(df_copy[amount_col], errors='coerce')
    df_copy['GL_Description'] = df_copy['GL_Code'].apply(lambda x: get_gl_name(x, gl_name_dict))
    df_copy['Category'] = df_copy['GL_Code'].apply(lambda x: get_gl_category(x, gl_category_dict))
    
    df_copy = df_copy.dropna(subset=['Amount'])
    
    return df_copy[['GL_Code', 'GL_Description', 'Category', 'Order', 'Amount']]

# ============= MAIN APP =============

if uploaded_gl_dump and uploaded_gl_desc:
    gl_dump = load_gl_dump_from_upload(uploaded_gl_dump)
    gl_name_dict, gl_category_dict = load_gl_descriptions_from_upload(uploaded_gl_desc)
    
    if gl_dump is not None:
        processed_data = process_gl_data(gl_dump, gl_name_dict, gl_category_dict)
        all_categories = sorted([cat for cat in processed_data['Category'].unique().tolist() if cat != 'Uncategorized'])
        
        # Sidebar navigation
        with st.sidebar:
            st.markdown("---")
            page = st.radio(
                "Select Option",
                ["📊 Dashboard Home", "🔍 Query Employee", "⚙️ Settings"]
            )
        
        if page == "📊 Dashboard Home":
            st.subheader("📊 Recovery Summary Dashboard")
            
            # Category filter
            st.subheader("🏷️ Filter by Category")
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            selected_categories = []
            
            for idx, cat in enumerate(all_categories):
                col = [col1, col2, col3, col4][idx % 4]
                if col.checkbox(cat, value=True, key=f"cat_{idx}"):
                    selected_categories.append(cat)
            
            if not selected_categories:
                selected_categories = all_categories
            
            filtered_by_cat = processed_data[processed_data['Category'].isin(selected_categories)]
            
            st.markdown("---")
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📊 GL Codes", filtered_by_cat['GL_Code'].nunique())
            with col2:
                st.metric("👥 Orders/IOs", filtered_by_cat['Order'].nunique())
            with col3:
                st.metric("💵 Total Amount (AED)", f"{filtered_by_cat['Amount'].sum():,.2f}")
            with col4:
                st.metric("📈 Records", len(filtered_by_cat))
            
            st.markdown("---")
            
            # GL Selection
            st.subheader("✅ Select GL Codes to Include")
            all_gls = sorted(filtered_by_cat['GL_Code'].unique().tolist())
            
            col1, col2, col3 = st.columns(3)
            selected_gls = []
            
            for idx, gl_code in enumerate(all_gls):
                gl_name = filtered_by_cat[filtered_by_cat['GL_Code'] == gl_code]['GL_Description'].iloc[0]
                col = [col1, col2, col3][idx % 3]
                
                if col.checkbox(f"{gl_code} - {gl_name[:30]}", value=True, key=f"gl_{gl_code}"):
                    selected_gls.append(gl_code)
            
            if not selected_gls:
                selected_gls = all_gls
            
            final_filtered = filtered_by_cat[filtered_by_cat['GL_Code'].isin(selected_gls)]
            
            st.markdown("---")
            
            # GL Summary
            st.subheader("💼 Summary by GL Code")
            gl_summary = final_filtered.groupby(['GL_Code', 'GL_Description', 'Category']).agg({
                'Amount': 'sum',
                'Order': 'count'
            }).reset_index()
            gl_summary.columns = ['GL Code', 'GL Description', 'Category', 'Total Amount (AED)', 'Number of Records']
            gl_summary = gl_summary.sort_values('Total Amount (AED)', ascending=False)
            
            st.dataframe(gl_summary, use_container_width=True)
            
            csv_gl = gl_summary.to_csv(index=False)
            st.download_button(
                label="📥 Download GL Summary as CSV",
                data=csv_gl,
                file_name=f"GL_Summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            st.markdown("---")
            
            # Order Summary
            st.subheader("👥 Summary by Order/IO")
            order_summary = final_filtered.groupby('Order').agg({
                'Amount': 'sum',
                'GL_Code': 'count'
            }).reset_index()
            order_summary.columns = ['Order/IO', 'Total Amount (AED)', 'Number of GLs']
            order_summary = order_summary.sort_values('Total Amount (AED)', ascending=False)
            
            st.dataframe(order_summary, use_container_width=True)
            
            csv_order = order_summary.to_csv(index=False)
            st.download_button(
                label="📥 Download Order Summary as CSV",
                data=csv_order,
                file_name=f"Order_Summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        elif page == "🔍 Query Employee":
            st.subheader("🔍 Query Recoveries by Employee/IO")
            
            # Category filter
            st.subheader("🏷️ Filter by Category (Optional)")
            selected_categories_query = []
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            
            for idx, cat in enumerate(all_categories):
                col = [col1, col2, col3, col4][idx % 4]
                if col.checkbox(cat, value=True, key=f"query_cat_{idx}"):
                    selected_categories_query.append(cat)
            
            if not selected_categories_query:
                selected_categories_query = all_categories
            
            filtered_by_cat_query = processed_data[processed_data['Category'].isin(selected_categories_query)]
            
            st.markdown("---")
            
            # Query input
            order_input = st.text_input(
                "Enter Order/Internal Order (IO) or Employee ID:",
                placeholder="e.g., 30102204"
            )
            
            if st.button("🔍 Search Recoveries", key="search_btn"):
                if order_input.strip():
                    filtered_data = filtered_by_cat_query[filtered_by_cat_query['Order'].astype(str).str.contains(order_input.strip(), na=False)]
                    
                    if not filtered_data.empty:
                        st.success(f"✅ Found {len(filtered_data)} records for Order: {order_input}")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Amount (AED)", f"{filtered_data['Amount'].sum():,.2f}")
                        with col2:
                            st.metric("Number of GLs", filtered_data['GL_Code'].nunique())
                        with col3:
                            st.metric("Number of Categories", filtered_data['Category'].nunique())
                        
                        st.markdown("---")
                        
                        st.subheader("📊 Category-wise Breakdown")
                        category_summary = filtered_data.groupby('Category').agg({
                            'Amount': 'sum',
                            'GL_Code': 'count'
                        }).reset_index()
                        category_summary.columns = ['Category', 'Amount (AED)', 'Number of GLs']
                        st.dataframe(category_summary, use_container_width=True)
                        
                        st.markdown("---")
                        
                        st.subheader("📋 GL-wise Breakdown")
                        detailed = filtered_data.groupby(['GL_Code', 'GL_Description', 'Category']).agg({
                            'Amount': 'sum'
                        }).reset_index()
                        detailed.columns = ['GL Code', 'GL Description', 'Category', 'Amount (AED)']
                        st.dataframe(detailed, use_container_width=True)
                        
                        csv_detail = detailed.to_csv(index=False)
                        st.download_button(
                            label="📥 Download Details as CSV",
                            data=csv_detail,
                            file_name=f"Recoveries_{order_input}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.warning(f"⚠️ No records found for Order: {order_input}")
                else:
                    st.warning("⚠️ Please enter an Order/IO")
        
        elif page == "⚙️ Settings":
            st.subheader("⚙️ System Settings & Status")
            
            st.info("📊 Data Summary:")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total GL Codes", processed_data['GL_Code'].nunique())
            with col2:
                st.metric("Total Orders", processed_data['Order'].nunique())
            with col3:
                st.metric("Total Categories", len(all_categories))
            with col4:
                st.metric("Total Records", len(processed_data))
            
            st.markdown("---")
            
            st.subheader("🏷️ Categories Found")
            st.write(", ".join(all_categories))
            
            st.markdown("---")
            
            st.subheader("📊 Data Preview")
            st.write("First 10 rows of processed GL data:")
            st.dataframe(processed_data.head(10), use_container_width=True)

else:
    st.warning("⚠️ Please upload both GL_dump.xlsx and GL_Description.xlsx files to get started!")
    st.info("""
    **How to use this cloud version:**
    1. Upload GL_dump.xlsx file (left sidebar)
    2. Upload GL_Description.xlsx file (left sidebar)
    3. Dashboard will load automatically
    4. Use filters and queries as needed
    5. Download reports as CSV
    """)
