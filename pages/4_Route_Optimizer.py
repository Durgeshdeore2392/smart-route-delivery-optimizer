"""
Route Optimizer Page
Configure parameters, execute Google OR-Tools VRP and Baseline algorithms,
view execution summaries, and inspect unassigned/infeasible order diagnostics.
"""

import time
import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import load_table_as_df, save_optimization_run, execute_sql_query
from src.baseline_optimizer import run_baseline_optimization
from src.route_optimizer import run_ortools_vrp
from src.delivery_analytics import compare_baseline_vs_optimized

st.set_page_config(page_title="Route Optimizer - Logistics Optimizer", page_icon="⚙️", layout="wide")

st.title("⚙️ Route Optimization Engine")
st.caption("Configure fleet routing constraints, execute OR-Tools VRP & Baseline algorithms, and analyze solution feasibility.")

DB_FILE = Path(__file__).parent.parent / "data" / "delivery_system.db"

# Load current orders & vehicles
df_locations = load_table_as_df("locations", DB_FILE)
df_orders = load_table_as_df("orders", DB_FILE)
df_vehicles = load_table_as_df("vehicles", DB_FILE)

warehouse = df_locations[df_locations["location_type"] == "warehouse"].iloc[0].to_dict() if not df_locations.empty else {
    "location_id": "LOC-000", "location_name": "Warehouse", "latitude": 41.8781, "longitude": -87.6298
}

# SETTINGS PANEL
with st.sidebar:
    st.subheader("⚙️ Solver Settings")
    circuity = st.slider("Road Circuity Factor", min_value=1.0, max_value=1.60, value=1.30, step=0.05, help="Multiplier for straight-line distance approximation")
    avg_speed = st.number_input("Avg Fleet Speed (km/h)", min_value=10.0, max_value=100.0, value=40.0, step=5.0)
    service_time = st.number_input("Service Time / Stop (mins)", min_value=0, max_value=60, value=15, step=5)
    enforce_tw = st.checkbox("Enforce Time Windows (VRPTW)", value=True)
    solver_time_limit = st.number_input("Solver Time Limit (sec)", min_value=1, max_value=30, value=5)

st.subheader("📋 Select Delivery Orders Batch for Optimization")

col_opt1, col_opt2 = st.columns(2)
with col_opt1:
    sample_size = st.slider("Select Number of Pending Orders to Route", min_value=5, max_value=min(100, max(5, len(df_orders))), value=min(30, len(df_orders)))
with col_opt2:
    st.markdown("**Active Fleet Available:**")
    avail_count = len(df_vehicles[df_vehicles["is_available"] == 1])
    st.info(f"🚚 **{avail_count} / {len(df_vehicles)} Vehicles Ready**")

# Prepare orders batch
batch_orders = df_orders.head(sample_size).to_dict("records")
vehicles_list = df_vehicles.to_dict("records")

st.markdown("---")

if st.button("🚀 Run Route Optimization Engine", type="primary"):
    with st.spinner("Calculating distance matrices and solving Vehicle Routing Problem..."):
        # 1. Run Baseline Optimization
        base_summary, base_stops = run_baseline_optimization(
            warehouse, batch_orders, vehicles_list,
            circuity_factor=circuity, avg_speed_kmh=avg_speed, service_time_mins=service_time
        )
        base_run_id = f"RUN-BASE-{int(time.time())}"
        base_summary["run_id"] = base_run_id
        save_optimization_run(base_summary, base_stops, DB_FILE)

        # 2. Run OR-Tools VRP Optimization
        opt_summary, opt_stops, unassigned_diag = run_ortools_vrp(
            warehouse, batch_orders, vehicles_list,
            circuity_factor=circuity, avg_speed_kmh=avg_speed, service_time_mins=service_time,
            enforce_time_windows=enforce_tw, search_time_limit_sec=solver_time_limit
        )
        opt_run_id = f"RUN-OPT-{int(time.time())}"
        opt_summary["run_id"] = opt_run_id
        save_optimization_run(opt_summary, opt_stops, DB_FILE)

        # 3. Store in session state for Map & Analysis pages
        comp_dict = compare_baseline_vs_optimized(base_summary, opt_summary)
        st.session_state["latest_run_summary"] = opt_summary
        st.session_state["latest_route_stops"] = opt_stops
        st.session_state["latest_unassigned_diag"] = unassigned_diag
        st.session_state["latest_comparison"] = comp_dict
        st.session_state["latest_run_id"] = opt_run_id

    st.success("✅ Route Optimization Execution Complete!")

    # DISPLAY SOLUTION SUMMARY METRICS
    st.subheader("📊 Optimization Solution Summary")

    m1, m2, m3, m4, m5, m6 = st.columns(6)

    m1.metric("Orders Assigned", f"{opt_summary['assigned_orders']} / {opt_summary['total_orders']}")
    
    imp = comp_dict["improvements"]
    m2.metric("Total Distance", f"{opt_summary['total_distance_km']:.1f} km", f"-{imp['distance_savings_pct']:.1f}% vs Baseline")
    m3.metric("Est. Transport Cost", f"${opt_summary['total_cost']:,.2f}", f"-{imp['cost_savings_pct']:.1f}% vs Baseline")
    m4.metric("Vehicles Used", f"{opt_summary['vehicles_used']} Vehicles", f"{imp['vehicles_reduced_count']} fewer")
    m5.metric("Avg Utilization", f"{opt_summary['avg_capacity_utilization']:.1f}%", f"+{imp['utilization_gain_pts']:.1f}% pts")
    m6.metric("On-Time Rate", f"{opt_summary['on_time_rate_pct']:.1f}%", f"{opt_summary['execution_time_sec']}s solver")

    st.markdown("---")

    # DISPLAY INFEASIBLE / UNASSIGNED ORDERS DIAGNOSTICS
    if unassigned_diag:
        st.warning(f"⚠️ **{len(unassigned_diag)} Order(s) Could Not Be Assigned** (Infeasibility Diagnostic Report)")
        df_diag = pd.DataFrame(unassigned_diag)
        st.dataframe(df_diag, use_container_width=True)
    else:
        st.info("🎉 **All pending delivery orders successfully assigned to vehicle routes with zero unassigned orders!**")

    st.subheader("🗺️ Next Steps")
    st.info("Navigate to **Route Map** to visually inspect vehicle stops, or **Performance Analysis** for detailed cost savings breakdowns.")

elif "latest_run_summary" in st.session_state and st.session_state["latest_run_summary"] is not None:
    opt_summary = st.session_state["latest_run_summary"]
    st.subheader("📋 Latest Saved Optimization Result")
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Algorithm", opt_summary.get("algorithm"))
    s2.metric("Assigned Orders", opt_summary.get("assigned_orders"))
    s3.metric("Total Distance", f"{opt_summary.get('total_distance_km')} km")
    s4.metric("Total Cost", f"${opt_summary.get('total_cost'):,.2f}")
