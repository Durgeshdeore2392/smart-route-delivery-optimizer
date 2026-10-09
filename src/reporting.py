"""
Reporting and CSV Export Generation module.
Provides exportable DataFrames and CSV strings for manifests, comparisons, and KPIs.
"""

import pandas as pd
from typing import Dict, List, Any


def generate_vehicle_manifest_df(route_stops: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Format route stops list into a clean vehicle delivery manifest DataFrame.
    """
    if not route_stops:
        return pd.DataFrame()

    df = pd.DataFrame(route_stops)
    
    # Filter out warehouse stops if desired or format cleanly
    df["stop_type"] = df["is_warehouse"].apply(lambda x: "Warehouse" if x else "Customer Delivery")
    
    output_cols = [
        "vehicle_id", "stop_sequence", "stop_type", "order_id", "location_name",
        "arrival_time", "departure_time", "distance_from_prev_km",
        "cumulative_distance_km", "load_after_stop_kg", "latitude", "longitude"
    ]
    
    existing_cols = [c for c in output_cols if c in df.columns]
    manifest_df = df[existing_cols].copy()
    manifest_df.rename(columns={
        "vehicle_id": "Vehicle ID",
        "stop_sequence": "Stop #",
        "stop_type": "Stop Type",
        "order_id": "Order ID",
        "location_name": "Location / Customer",
        "arrival_time": "Est. Arrival",
        "departure_time": "Est. Departure",
        "distance_from_prev_km": "Leg Distance (km)",
        "cumulative_distance_km": "Total Distance (km)",
        "load_after_stop_kg": "Cumulative Load (kg)"
    }, inplace=True)

    return manifest_df


def generate_comparison_report_df(comp_dict: Dict[str, Any]) -> pd.DataFrame:
    """
    Create a side-by-side comparison DataFrame between Baseline and OR-Tools VRP.
    """
    base = comp_dict.get("baseline", {})
    opt = comp_dict.get("optimized", {})
    imp = comp_dict.get("improvements", {})

    metrics = [
        ("Total Orders", base.get("total_orders", 0), opt.get("total_orders", 0), "0"),
        ("Assigned Orders", base.get("assigned_orders", 0), opt.get("assigned_orders", 0), f"+{opt.get('assigned_orders',0)-base.get('assigned_orders',0)}"),
        ("Unassigned Orders", base.get("unassigned_orders", 0), opt.get("unassigned_orders", 0), f"{opt.get('unassigned_orders',0)-base.get('unassigned_orders',0)}"),
        ("Vehicles Used", base.get("vehicles_used", 0), opt.get("vehicles_used", 0), f"{imp.get('vehicles_reduced_count', 0)} fewer"),
        ("Total Distance (km)", base.get("total_distance_km", 0.0), opt.get("total_distance_km", 0.0), f"-{imp.get('distance_saved_km', 0.0)} km ({imp.get('distance_savings_pct', 0.0)}%)"),
        ("Transportation Cost ($)", f"${base.get('total_cost', 0.0):,.2f}", f"${opt.get('total_cost', 0.0):,.2f}", f"-${imp.get('cost_saved_usd', 0.0):,.2f} ({imp.get('cost_savings_pct', 0.0)}%)"),
        ("Avg Capacity Utilization (%)", f"{base.get('avg_capacity_utilization', 0.0)}%", f"{opt.get('avg_capacity_utilization', 0.0)}%", f"+{imp.get('utilization_gain_pts', 0.0)}% pts"),
        ("Total Duration (hours)", base.get("total_duration_hours", 0.0), opt.get("total_duration_hours", 0.0), f"-{imp.get('time_saved_hours', 0.0)} hrs ({imp.get('time_savings_pct', 0.0)}%)"),
        ("On-Time Delivery Rate (%)", f"{base.get('on_time_rate_pct', 0.0)}%", f"{opt.get('on_time_rate_pct', 0.0)}%", f"+{imp.get('ontime_rate_gain_pts', 0.0)}% pts")
    ]

    df = pd.DataFrame(metrics, columns=["Performance Metric", "Baseline (Nearest Neighbor)", "OR-Tools VRP", "Improvement / Delta"])
    return df
