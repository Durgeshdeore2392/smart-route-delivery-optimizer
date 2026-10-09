"""
Fleet Management Page
Manage delivery vehicles, vehicle capacities, costs per km, and operating availability.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import load_table_as_df, execute_transaction
from src.data_validation import validate_vehicles_df

st.set_page_config(page_title="Fleet Management - Logistics Optimizer", page_icon="🚚", layout="wide")

st.title("🚚 Vehicle Fleet Management")
st.caption("Manage logistics vehicle fleet, capacities, per-kilometer transportation costs, and working hour limits.")

DB_FILE = Path(__file__).parent.parent / "data" / "delivery_system.db"

df_vehicles = load_table_as_df("vehicles", DB_FILE)

# Fleet KPI Cards
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
total_fleet = len(df_vehicles)
avail_fleet = len(df_vehicles[df_vehicles["is_available"] == 1]) if not df_vehicles.empty else 0
total_cap = df_vehicles["capacity_kg"].sum() if not df_vehicles.empty else 0.0
avg_cost_km = df_vehicles["cost_per_km"].mean() if not df_vehicles.empty else 0.0

kpi1.metric("Total Fleet Size", f"{total_fleet} Vehicles", "Registered")
kpi2.metric("Available Fleet", f"{avail_fleet} Vehicles", f"{avail_fleet/max(total_fleet,1)*100:.0f}% Available")
kpi3.metric("Total Capacity", f"{total_cap:,.0f} kg", "Fleet Payload")
kpi4.metric("Avg Operating Cost", f"${avg_cost_km:.2f} / km", "Fleet Variable Cost")

st.markdown("---")

tab_fleet, tab_add = st.tabs(["🚛 Active Vehicle Fleet", "➕ Register New Vehicle"])

with tab_fleet:
    st.subheader("Vehicle Fleet Roster")
    st.dataframe(df_vehicles, use_container_width=True, height=400)

    # Availability toggle quick action
    st.subheader("⚙️ Quick Availability Toggle")
    if not df_vehicles.empty:
        col_v, col_btn = st.columns([3, 1])
        selected_v = col_v.selectbox("Select Vehicle ID", df_vehicles["vehicle_id"].tolist())
        curr_avail = df_vehicles[df_vehicles["vehicle_id"] == selected_v]["is_available"].iloc[0]
        new_avail_label = "Deactivate (Mark Unavailable)" if curr_avail == 1 else "Activate (Mark Available)"
        
        if col_btn.button(new_avail_label):
            new_val = 0 if curr_avail == 1 else 1
            sql = "UPDATE vehicles SET is_available = ? WHERE vehicle_id = ?;"
            execute_transaction([(sql, (new_val, selected_v))], DB_FILE)
            st.success(f"Updated {selected_v} availability to {new_val}!")
            st.rerun()

with tab_add:
    st.subheader("Register New Logistics Vehicle")
    with st.form("add_vehicle_form"):
        c1, c2, c3 = st.columns(3)
        v_id = c1.text_input("Vehicle ID", f"VEH-{(total_fleet + 1):03d}")
        v_name = c2.text_input("Vehicle Name", "Heavy Cargo Van #21")
        v_type = c3.selectbox("Vehicle Type", ["Van", "Electric Van", "Light Truck", "Heavy Truck"])

        c4, c5, c6 = st.columns(3)
        cap = c4.number_input("Max Capacity (kg)", value=500.0, min_value=10.0)
        cost_km = c5.number_input("Cost per KM ($)", value=1.20, min_value=0.1)
        fixed_cost = c6.number_input("Fixed Dispatch Cost ($)", value=50.0, min_value=0.0)

        c7, c8 = st.columns(2)
        max_dist = c7.number_input("Max Route Distance (km)", value=300.0, min_value=10.0)
        max_hours = c8.number_input("Max Working Hours", value=9.0, min_value=1.0)

        submit_v = st.form_submit_button("Register Vehicle")

        if submit_v:
            sql = """
                INSERT OR REPLACE INTO vehicles (
                    vehicle_id, vehicle_name, vehicle_type, capacity_kg, cost_per_km,
                    fixed_cost, max_distance_km, max_working_hours, shift_start, shift_end, is_available
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '08:00', '18:00', 1);
            """
            execute_transaction([(sql, (v_id, v_name, v_type, cap, cost_km, fixed_cost, max_dist, max_hours))], DB_FILE)
            st.success(f"Vehicle {v_id} registered successfully!")
            st.rerun()
