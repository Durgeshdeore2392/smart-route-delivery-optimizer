"""
Smart Route & Delivery Optimization System
Main Streamlit Application Entrypoint.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import init_db, load_table_as_df, execute_sql_query
from src.data_generator import seed_database_from_csv

st.set_page_config(
    page_title="Smart Route & Delivery Optimization System",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Auto-initialize database on launch if not exists
DB_FILE = Path(__file__).parent / "data" / "delivery_system.db"
if not DB_FILE.exists():
    init_db(DB_FILE)
    try:
        seed_database_from_csv(DB_FILE)
    except Exception as e:
        st.warning(f"Initial seeding notice: {e}")
else:
    init_db(DB_FILE)

# Initialize Session State Variables
if "selected_date" not in st.session_state:
    st.session_state["selected_date"] = None
if "latest_run_summary" not in st.session_state:
    st.session_state["latest_run_summary"] = None

# Sidebar Header & Branding
st.sidebar.title("🚚 Smart Delivery Optimizer")
st.sidebar.caption("Enterprise Logistics & Route Planning System")
st.sidebar.markdown("---")

# Quick Fleet & Order Stats in Sidebar
try:
    orders_df = load_table_as_df("orders", DB_FILE)
    vehicles_df = load_table_as_df("vehicles", DB_FILE)
    
    st.sidebar.subheader("System Status")
    col1, col2 = st.sidebar.columns(2)
    col1.metric("Orders", len(orders_df))
    col2.metric("Fleet", len(vehicles_df))
    
    pending_count = len(orders_df[orders_df["status"] == "Pending"])
    st.sidebar.info(f"📋 **Pending Orders**: {pending_count}")
except Exception:
    st.sidebar.write("Database initializing...")

st.sidebar.markdown("---")
st.sidebar.markdown("**Portfolio & Interview Highlights**")
st.sidebar.markdown(
    """
    - **Optimization Engine**: Google OR-Tools VRP / VRPTW
    - **Baseline**: Nearest-Neighbor Routing Benchmark
    - **Distance Model**: Haversine + Road Circuity Factor
    - **Analytics**: SQL Performance Queries & Streamlit
    """
)

# Main Landing Header
st.title("🚚 Smart Route & Delivery Optimization System")
st.markdown(
    """
    Welcome to the **Smart Route & Delivery Optimization System** — a full-stack logistics solution 
    designed to help logistics providers reduce transportation costs, minimize delivery distances, 
    improve on-time delivery rates, and maximize vehicle capacity utilization.
    
    ### 🧭 Quick Navigation
    - **Executive Dashboard**: View top logistics KPIs, volume trends, and cost metrics.
    - **Orders Management**: Search, edit, and upload bulk delivery orders via CSV.
    - **Fleet Management**: Configure vehicle capacities, costs, and availability constraints.
    - **Route Optimizer**: Run Google OR-Tools VRP optimization against baseline plans.
    - **Route Map**: Explore color-coded interactive vehicle routes and stop sequences.
    - **Performance Analysis**: Detailed side-by-side Baseline vs. OR-Tools cost savings analysis.
    - **Optimization History**: Review past optimization runs saved in SQLite.
    - **Data & Settings**: Manage system parameters and regenerate synthetic datasets.
    """
)

# Key Performance Overview Banner
st.subheader("⚡ Quick System Overview")

col_a, col_b, col_c, col_d = st.columns(4)

with col_a:
    st.metric("Total Warehouse Locations", "1 Central Hub", "Chicago, IL")
with col_b:
    st.metric("Customer Locations", "30 Delivery Hubs", "Metropolitan Area")
with col_c:
    st.metric("Available Fleet", f"{len(vehicles_df[vehicles_df['is_available']==1])} / {len(vehicles_df)} Vehicles", "Active")
with col_d:
    st.metric("Total Orders Loaded", f"{len(orders_df)} Orders", "Data Ready")

st.info("👈 Use the **sidebar menu** to navigate between pages and run route optimizations.")
