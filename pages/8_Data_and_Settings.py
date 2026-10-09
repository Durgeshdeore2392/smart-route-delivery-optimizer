"""
Data and Settings Page
Manage datasets, regenerate synthetic data deterministically,
inspect SQLite database tables, and reset operational data.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import load_table_as_df, init_db, get_connection
from src.data_generator import generate_synthetic_data, seed_database_from_csv

st.set_page_config(page_title="Data & Settings - Logistics Optimizer", page_icon="🛠️", layout="wide")

st.title("🛠️ Data & System Settings")
st.caption("Manage synthetic datasets, inspect raw database tables, and reset operational data.")

DB_FILE = Path(__file__).parent.parent / "data" / "delivery_system.db"

tab_tables, tab_reset = st.tabs(["🗄️ Database Table Inspector", "⚙️ Data Management & Reset"])

with tab_tables:
    st.subheader("Database Table Inspector")
    table_name = st.selectbox(
        "Select Table to Inspect",
        ["orders", "vehicles", "locations", "historical_deliveries", "optimization_runs", "route_stops"]
    )
    
    try:
        df_tbl = load_table_as_df(table_name, DB_FILE)
        st.write(f"**Table '{table_name}' ({len(df_tbl)} records):**")
        st.dataframe(df_tbl, use_container_width=True, height=450)
    except Exception as e:
        st.error(f"Error reading table {table_name}: {e}")

with tab_reset:
    st.subheader("Synthetic Dataset Regeneration")
    st.markdown(
        """
        Regenerate synthetic datasets (500 orders, 20 vehicles, 30 customer locations, 1 warehouse, 500 historical delivery records) 
        deterministically using a fixed random seed (seed = 42).
        """
    )

    seed_val = st.number_input("Random Seed", min_value=1, max_value=9999, value=42)

    if st.button("🔄 Regenerate & Seed Database Now", type="primary"):
        with st.spinner("Generating synthetic dataset and seeding SQLite database..."):
            generate_synthetic_data(seed=seed_val)
            seed_database_from_csv(DB_FILE)
        st.success(f"✅ Successfully regenerated dataset with seed={seed_val} and re-seeded SQLite database!")
        st.rerun()

    st.markdown("---")
    st.subheader("⚠️ System Maintenance")
    if st.button("🗑️ Reset Optimization History Runs Only"):
        conn = get_connection(DB_FILE)
        conn.execute("DELETE FROM optimization_runs;")
        conn.execute("DELETE FROM route_stops;")
        conn.commit()
        conn.close()
        st.success("Optimization history cleared successfully!")
        st.rerun()
