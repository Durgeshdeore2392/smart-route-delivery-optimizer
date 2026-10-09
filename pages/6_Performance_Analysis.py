"""
Performance Analysis Page
Comprehensive Baseline vs. OR-Tools VRP performance benchmark,
cost savings analysis, Plotly comparison charts, and CSV report exports.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import load_table_as_df
from src.delivery_analytics import compare_baseline_vs_optimized, generate_business_recommendations, analyze_historical_delays
from src.reporting import generate_comparison_report_df

st.set_page_config(page_title="Performance Analysis - Logistics Optimizer", page_icon="📈", layout="wide")

st.title("📈 Baseline vs. Optimized Performance Analysis")
st.caption("Side-by-side benchmarking of Nearest-Neighbor Baseline against Google OR-Tools VRP route plans.")

DB_FILE = Path(__file__).parent.parent / "data" / "delivery_system.db"

df_runs = load_table_as_df("optimization_runs", DB_FILE)

if df_runs.empty or len(df_runs) < 2:
    st.warning("⚠️ At least two optimization runs (Baseline & OR-Tools) are required to perform comparative analysis. Please run an optimization on the **Route Optimizer** page first.")
    st.stop()

# Get recent baseline and OR-Tools runs
df_base_runs = df_runs[df_runs["algorithm"].str.contains("Baseline", case=False, na=False)]
df_opt_runs = df_runs[df_runs["algorithm"].str.contains("VRP|Heuristic", case=False, na=False)]

latest_base = df_base_runs.iloc[-1].to_dict() if not df_base_runs.empty else df_runs.iloc[-2].to_dict()
latest_opt = df_opt_runs.iloc[-1].to_dict() if not df_opt_runs.empty else df_runs.iloc[-1].to_dict()

comp_dict = compare_baseline_vs_optimized(latest_base, latest_opt)
imp = comp_dict["improvements"]

# 1. TOP HIGHLIGHT SAVINGS CARDS
st.subheader("⚡ Executive Cost & Efficiency Gains")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Transportation Cost Saved",
    f"${imp['cost_saved_usd']:,.2f}",
    f"{imp['cost_savings_pct']:.1f}% Savings",
    delta_color="normal"
)

c2.metric(
    "Distance Reduced",
    f"{imp['distance_saved_km']:,.1f} km",
    f"{imp['distance_savings_pct']:.1f}% Less Distance",
    delta_color="normal"
)

c3.metric(
    "Vehicles Saved",
    f"{imp['vehicles_reduced_count']} Vehicle(s)",
    "Fleet Reduction",
    delta_color="normal"
)

c4.metric(
    "Capacity Utilization Gain",
    f"+{imp['utilization_gain_pts']:.1f}% pts",
    f"{latest_opt.get('avg_capacity_utilization', 0.0):.1f}% Final",
    delta_color="normal"
)

st.markdown("---")

# 2. COMPARISON TABLE
st.subheader("📋 Side-by-Side Metric Comparison Table")
df_comp_table = generate_comparison_report_df(comp_dict)
st.dataframe(df_comp_table, use_container_width=True)

# Export CSV Report
csv_bytes = df_comp_table.to_csv(index=False).encode('utf-8')
st.download_button(
    "📥 Download Baseline vs Optimized Report (CSV)",
    data=csv_bytes,
    file_name="baseline_vs_optimized_report.csv",
    mime="text/csv"
)

st.markdown("---")

# 3. INTERACTIVE PLOTLY COMPARATIVE CHARTS
st.subheader("📊 Operational Metrics Visual Comparison")

col_a, col_b = st.columns(2)

with col_a:
    fig_dist_cost = go.Figure(data=[
        go.Bar(name="Baseline Plan", x=["Distance (km)", "Cost ($)"], y=[latest_base["total_distance_km"], latest_base["total_cost"]], marker_color="#EF553B"),
        go.Bar(name="OR-Tools VRP Plan", x=["Distance (km)", "Cost ($)"], y=[latest_opt["total_distance_km"], latest_opt["total_cost"]], marker_color="#00CC96")
    ])
    fig_dist_cost.update_layout(barmode="group", title="Distance (km) & Cost ($) Comparison", height=350)
    st.plotly_chart(fig_dist_cost, use_container_width=True)

with col_b:
    fig_util_time = go.Figure(data=[
        go.Bar(name="Baseline Plan", x=["Capacity Util (%)", "On-Time Rate (%)"], y=[latest_base["avg_capacity_utilization"], latest_base["on_time_rate_pct"]], marker_color="#FFA15A"),
        go.Bar(name="OR-Tools VRP Plan", x=["Capacity Util (%)", "On-Time Rate (%)"], y=[latest_opt["avg_capacity_utilization"], latest_opt["on_time_rate_pct"]], marker_color="#636EFA")
    ])
    fig_util_time.update_layout(barmode="group", title="Capacity Utilization & On-Time Performance (%)", height=350)
    st.plotly_chart(fig_util_time, use_container_width=True)

st.markdown("---")

# 4. BUSINESS INSIGHTS & RECOMMENDATIONS
st.subheader("💡 Strategic Supply Chain Business Recommendations")
df_reasons, _, _ = analyze_historical_delays(DB_FILE)
recs = generate_business_recommendations(comp_dict, df_reasons)

for r in recs:
    st.markdown(f"- {r}")
