"""
Route Map Page
Interactive visual map rendering of vehicle delivery routes, stop sequences,
warehouse location, and unassigned orders using Folium & Plotly fallback.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import load_table_as_df, execute_sql_query

try:
    import folium
    from streamlit_folium import st_folium
    HAS_FOLIUM = True
except ImportError:
    HAS_FOLIUM = False

st.set_page_config(page_title="Route Map - Logistics Optimizer", page_icon="🗺️", layout="wide")

st.title("🗺️ Interactive Route Map & Delivery Sequence")
st.caption("Explore color-coded vehicle routes, stop order sequences, arrival estimates, and warehouse hub location.")

DB_FILE = Path(__file__).parent.parent / "data" / "delivery_system.db"

# Fetch latest route stops
latest_run_id = st.session_state.get("latest_run_id")

if not latest_run_id:
    # Get last run_id from DB
    df_runs = load_table_as_df("optimization_runs", DB_FILE)
    if not df_runs.empty:
        latest_run_id = df_runs.iloc[-1]["run_id"]

if not latest_run_id:
    st.warning("⚠️ No optimization runs found. Please run an optimization on the **Route Optimizer** page first.")
    st.stop()

# Query stops for this run
sql_stops = "SELECT * FROM route_stops WHERE run_id = ? ORDER BY vehicle_id, stop_sequence;"
df_stops = execute_sql_query(sql_stops, (latest_run_id,), DB_FILE)

if df_stops.empty:
    st.info("No route stops recorded for the selected optimization run.")
    st.stop()

st.sidebar.subheader("🗺️ Map Layer Controls")
render_mode = st.sidebar.radio("Map Rendering Engine", ["Folium (OpenStreetMap)", "Plotly Map (Fallback Mode)"])
show_unassigned = st.sidebar.checkbox("Show Unassigned Orders", value=True)

st.info("ℹ️ **Note**: Displayed route polylines reflect geographic distance with an applied road circuity factor multiplier. Lines represent approximate road-following routes.")

# Color palette for vehicles
VEHICLE_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
]

vehicle_ids = df_stops["vehicle_id"].unique().tolist()
color_map = {v_id: VEHICLE_COLORS[i % len(VEHICLE_COLORS)] for i, v_id in enumerate(vehicle_ids)}

# RENDER MODE 1: FOLIUM MAP
if render_mode == "Folium (OpenStreetMap)" and HAS_FOLIUM:
    wh_stop = df_stops[df_stops["is_warehouse"] == 1].iloc[0]
    map_center = [wh_stop["latitude"], wh_stop["longitude"]]
    
    m = folium.Map(location=map_center, zoom_start=11, tiles="OpenStreetMap")

    # Warehouse Marker
    folium.Marker(
        location=map_center,
        popup="<b>Central Distribution Warehouse</b>",
        tooltip="Central Hub (Warehouse)",
        icon=folium.Icon(color="red", icon="home", prefix="fa")
    ).add_to(m)

    # Vehicle Routes & Stop Markers
    for v_id in vehicle_ids:
        v_stops = df_stops[df_stops["vehicle_id"] == v_id].sort_values("stop_sequence")
        v_color = color_map[v_id]
        
        points = []
        for _, row in v_stops.iterrows():
            pt = [row["latitude"], row["longitude"]]
            points.append(pt)
            
            if not row["is_warehouse"]:
                popup_txt = f"""
                <b>Vehicle:</b> {v_id}<br>
                <b>Stop #:</b> {row['stop_sequence']}<br>
                <b>Order ID:</b> {row['order_id']}<br>
                <b>Customer:</b> {row['location_name']}<br>
                <b>Est. Arrival:</b> {row['arrival_time']}<br>
                <b>Leg Distance:</b> {row['distance_from_prev_km']} km<br>
                <b>Load:</b> {row['load_after_stop_kg']} kg
                """
                folium.CircleMarker(
                    location=pt,
                    radius=7,
                    popup=popup_txt,
                    tooltip=f"Stop #{row['stop_sequence']} ({row['order_id']})",
                    color=v_color,
                    fill=True,
                    fill_color=v_color,
                    fill_opacity=0.8
                ).add_to(m)

        # Draw vehicle polyline route
        if len(points) > 1:
            folium.PolyLine(
                locations=points,
                color=v_color,
                weight=3,
                opacity=0.8,
                tooltip=f"Route {v_id}"
            ).add_to(m)

    st_folium(m, width=1200, height=550)

# RENDER MODE 2: PLOTLY MAP FALLBACK
else:
    wh_stop = df_stops[df_stops["is_warehouse"] == 1].iloc[0]
    
    # Version-compatible Plotly map trace selector (Plotly v7+ uses Scattermap; Plotly v5 uses Scattermapbox)
    ScatterMapTrace = getattr(go, "Scattermap", getattr(go, "Scattermapbox", go.Scattergeo))
    map_layout_key = "map" if hasattr(go, "Scattermap") else ("mapbox" if hasattr(go, "Scattermapbox") else "geo")

    fig = go.Figure()

    # Warehouse Marker
    fig.add_trace(ScatterMapTrace(
        lat=[wh_stop["latitude"]],
        lon=[wh_stop["longitude"]],
        mode="markers",
        marker=dict(size=16, color="red"),
        name="Warehouse Hub",
        text=["Central Distribution Warehouse"]
    ))

    # Vehicle Routes
    for v_id in vehicle_ids:
        v_stops = df_stops[df_stops["vehicle_id"] == v_id].sort_values("stop_sequence")
        v_color = color_map[v_id]

        fig.add_trace(ScatterMapTrace(
            lat=v_stops["latitude"],
            lon=v_stops["longitude"],
            mode="lines+markers",
            line=dict(width=3, color=v_color),
            marker=dict(size=9, color=v_color),
            name=f"Vehicle {v_id}",
            text=v_stops.apply(lambda r: f"Stop #{r['stop_sequence']}: {r['location_name']} ({r['order_id']})", axis=1)
        ))

    layout_kwargs = {
        map_layout_key: dict(
            style="open-street-map",
            center=dict(lat=wh_stop["latitude"], lon=wh_stop["longitude"]),
            zoom=10
        ),
        "margin": dict(l=0, r=0, t=20, b=0),
        "height": 550,
        "showlegend": True
    }

    fig.update_layout(**layout_kwargs)
    st.plotly_chart(fig, use_container_width=True)

# Stop Manifest Table
st.subheader("📋 Delivery Route Manifest Breakdown")
selected_vehicle = st.selectbox("Filter Route Manifest by Vehicle", ["All Vehicles"] + vehicle_ids)

if selected_vehicle == "All Vehicles":
    st.dataframe(df_stops, use_container_width=True)
else:
    st.dataframe(df_stops[df_stops["vehicle_id"] == selected_vehicle], use_container_width=True)
