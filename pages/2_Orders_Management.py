"""
Orders Management Page
CRUD operations, search/filter, and CSV batch upload with automated validation.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import load_table_as_df, execute_transaction, get_connection
from src.data_validation import validate_orders_df

st.set_page_config(page_title="Orders Management - Logistics Optimizer", page_icon="📦", layout="wide")

st.title("📦 Delivery Orders Management")
st.caption("Manage customer delivery orders, search & filter records, upload batch CSV files, and validate inputs.")

DB_FILE = Path(__file__).parent.parent / "data" / "delivery_system.db"

tab_view, tab_add, tab_upload = st.tabs(["📋 View & Filter Orders", "➕ Add / Edit Order", "📤 Batch Upload CSV"])

# Load orders
df_orders = load_table_as_df("orders", DB_FILE)

# TAB 1: VIEW & FILTER ORDERS
with tab_view:
    st.subheader("Filter & Search Orders")
    f_col1, f_col2, f_col3, f_col4 = st.columns(4)

    search_query = f_col1.text_input("🔍 Search Customer or Order ID", "")
    
    statuses = ["All"] + sorted(df_orders["status"].unique().tolist()) if not df_orders.empty else ["All"]
    status_filter = f_col2.selectbox("Filter Status", statuses)

    priorities = ["All"] + sorted(df_orders["priority"].unique().tolist()) if not df_orders.empty else ["All"]
    priority_filter = f_col3.selectbox("Filter Priority", priorities)

    min_qty, max_qty = 0.0, 2000.0
    if not df_orders.empty and "quantity_kg" in df_orders.columns:
        min_qty = float(df_orders["quantity_kg"].min())
        max_qty = float(df_orders["quantity_kg"].max())
    qty_range = f_col4.slider("Quantity Range (kg)", min_value=0.0, max_value=max(max_qty, 100.0), value=(0.0, max(max_qty, 100.0)))

    # Apply Filters
    df_filtered = df_orders.copy()
    if search_query:
        df_filtered = df_filtered[
            df_filtered["order_id"].str.contains(search_query, case=False, na=False) |
            df_filtered["customer_name"].str.contains(search_query, case=False, na=False)
        ]
    if status_filter != "All":
        df_filtered = df_filtered[df_filtered["status"] == status_filter]
    if priority_filter != "All":
        df_filtered = df_filtered[df_filtered["priority"] == priority_filter]
    df_filtered = df_filtered[
        (df_filtered["quantity_kg"] >= qty_range[0]) &
        (df_filtered["quantity_kg"] <= qty_range[1])
    ]

    st.markdown(f"**Showing {len(df_filtered)} of {len(df_orders)} Delivery Orders**")
    st.dataframe(df_filtered, use_container_width=True, height=450)

# TAB 2: ADD / EDIT ORDER
with tab_add:
    st.subheader("Add Single Delivery Order")
    with st.form("add_order_form"):
        col1, col2, col3 = st.columns(3)
        
        next_id = f"ORD-{(len(df_orders) + 1):04d}"
        ord_id = col1.text_input("Order ID", next_id)
        c_name = col2.text_input("Customer Name", "Acme Corp")
        loc_id = col3.text_input("Location ID", "LOC-001")

        c4, c5, c6 = st.columns(3)
        lat = c4.number_input("Latitude", value=41.8850, format="%.5f")
        lon = c5.number_input("Longitude", value=-87.6300, format="%.5f")
        qty = c6.number_input("Quantity (kg)", value=50.0, min_value=1.0)

        c7, c8, c9 = st.columns(3)
        priority = c7.selectbox("Priority", ["High", "Medium", "Low"], index=1)
        tw_start = c8.text_input("Time Window Start (HH:MM)", "08:00")
        tw_end = c9.text_input("Time Window End (HH:MM)", "17:00")

        submit_btn = st.form_submit_button("Save Order")

        if submit_btn:
            if not ord_id or not c_name:
                st.error("Order ID and Customer Name are required.")
            else:
                try:
                    sql = """
                        INSERT OR REPLACE INTO orders (
                            order_id, customer_name, location_id, latitude, longitude,
                            quantity_kg, priority, time_window_start, time_window_end,
                            order_date, status, service_time_mins
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_DATE, 'Pending', 15);
                    """
                    execute_transaction([(sql, (ord_id, c_name, loc_id, lat, lon, qty, priority, tw_start, tw_end))], DB_FILE)
                    st.success(f"Order {ord_id} saved successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save order: {e}")

# TAB 3: BATCH UPLOAD CSV
with tab_upload:
    st.subheader("Upload Orders via CSV File")
    st.markdown(
        """
        Upload a `.csv` file containing delivery orders.
        The file should contain columns: `order_id`, `customer_name`, `location_id`, `latitude`, `longitude`, `quantity_kg`, `priority`, `time_window_start`, `time_window_end`.
        """
    )

    uploaded_file = st.file_uploader("Choose CSV file", type=["csv"])

    if uploaded_file is not None:
        try:
            raw_df = pd.read_csv(uploaded_file)
            st.write("📄 **Raw CSV Preview:**")
            st.dataframe(raw_df.head(), use_container_width=True)

            cleaned_df, report = validate_orders_df(raw_df)

            if report["is_valid"]:
                st.success(f"✅ Validation Passed! {report['valid_count']} valid orders found.")
            else:
                st.error(f"❌ Validation Errors ({len(report['errors'])} issue(s)):")
                for err in report["errors"]:
                    st.write(f"- ⚠️ {err}")

            if report["warnings"]:
                st.warning(f"⚠️ Warnings ({len(report['warnings'])}):")
                for w in report["warnings"]:
                    st.write(f"- {w}")

            if st.button("Import Valid Orders into System"):
                conn = get_connection(DB_FILE)
                cleaned_df.to_sql("orders", conn, if_exists="append", index=False)
                conn.close()
                st.success(f"Successfully imported {len(cleaned_df)} orders into database!")
                st.rerun()

        except Exception as e:
            st.error(f"Error reading CSV file: {e}")
