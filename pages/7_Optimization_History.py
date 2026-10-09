"""
Optimization History Page
Review past optimization runs persisted in SQLite database,
compare historical runs side-by-side, and download vehicle manifests.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import load_table_as_df, execute_sql_query
from src.reporting import generate_vehicle_manifest_df

st.set_page_config(page_title="Optimization History - Logistics Optimizer", page_icon="📜", layout="wide")

st.title("📜 Optimization History & Run Logs")
st.caption("Review historical route optimization runs stored in SQLite, analyze past performance, and export vehicle manifests.")

DB_FILE = Path(__file__).parent.parent / "data" / "delivery_system.db"

df_runs = load_table_as_df("optimization_runs", DB_FILE)

if df_runs.empty:
    st.info("No past optimization runs recorded in database. Run an optimization on the **Route Optimizer** page.")
    st.stop()

st.subheader("📋 Historical Optimization Run Logs")
st.dataframe(df_runs.sort_values("timestamp", ascending=False), use_container_width=True, height=350)

st.markdown("---")

tab_manifest, tab_compare = st.tabs(["📄 Export Vehicle Delivery Manifest", "⚖️ Compare Two Past Runs"])

with tab_manifest:
    st.subheader("Download Vehicle Manifest for Past Run")
    run_list = df_runs["run_id"].unique().tolist()
    selected_run = st.selectbox("Select Optimization Run ID", run_list)
    
    if selected_run:
        sql_stops = "SELECT * FROM route_stops WHERE run_id = ? ORDER BY vehicle_id, stop_sequence;"
        df_stops = execute_sql_query(sql_stops, (selected_run,), DB_FILE)
        
        manifest_df = generate_vehicle_manifest_df(df_stops.to_dict("records"))
        st.dataframe(manifest_df, use_container_width=True)
        
        csv_data = manifest_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            f"📥 Download Manifest for {selected_run} (CSV)",
            data=csv_data,
            file_name=f"vehicle_manifest_{selected_run}.csv",
            mime="text/csv"
        )

with tab_compare:
    st.subheader("Side-by-Side Run Comparison")
    if len(df_runs) >= 2:
        c1, c2 = st.columns(2)
        run_a_id = c1.selectbox("Select Run A", df_runs["run_id"].unique().tolist(), index=len(df_runs)-2)
        run_b_id = c2.selectbox("Select Run B", df_runs["run_id"].unique().tolist(), index=len(df_runs)-1)
        
        run_a = df_runs[df_runs["run_id"] == run_a_id].iloc[0]
        run_b = df_runs[df_runs["run_id"] == run_b_id].iloc[0]

        metrics = [
            "algorithm", "total_orders", "assigned_orders", "vehicles_used",
            "total_distance_km", "total_cost", "avg_capacity_utilization", "total_duration_hours", "on_time_rate_pct"
        ]
        
        comp_rows = []
        for m in metrics:
            comp_rows.append({
                "Metric": m.replace("_", " ").title(),
                f"Run A ({run_a_id})": run_a[m],
                f"Run B ({run_b_id})": run_b[m]
            })
            
        st.dataframe(pd.DataFrame(comp_rows), use_container_width=True)
    else:
        st.info("Execute at least two runs to perform side-by-side run comparisons.")
