"""
Logistics & Delivery Performance Analytics module.
Performs SQL/Pandas analytics for Baseline vs. Optimized comparisons,
vehicle efficiency, route distance excesses, delay patterns, and recommendations.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional

from src.database import execute_sql_query, load_table_as_df


def safe_pct_improvement(baseline_val: float, optimized_val: float, lower_is_better: bool = True) -> float:
    """
    Calculate percentage improvement safely handling zero baseline denominators.
    - If lower_is_better=True (e.g. distance, cost, time): (baseline - optimized) / baseline * 100
    - If lower_is_better=False (e.g. utilization, on-time rate): (optimized - baseline) / baseline * 100
    """
    if baseline_val == 0.0 or pd.isna(baseline_val):
        return 0.0
    
    if lower_is_better:
        diff = baseline_val - optimized_val
    else:
        diff = optimized_val - baseline_val
        
    return round((diff / abs(baseline_val)) * 100.0, 2)


def compare_baseline_vs_optimized(baseline_summary: Dict[str, Any], ortools_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate comprehensive comparison metrics between Baseline and OR-Tools VRP plans.
    """
    base_dist = baseline_summary.get("total_distance_km", 0.0)
    opt_dist = ortools_summary.get("total_distance_km", 0.0)
    dist_savings_pct = safe_pct_improvement(base_dist, opt_dist, lower_is_better=True)
    dist_saved_km = round(base_dist - opt_dist, 2)

    base_cost = baseline_summary.get("total_cost", 0.0)
    opt_cost = ortools_summary.get("total_cost", 0.0)
    cost_savings_pct = safe_pct_improvement(base_cost, opt_cost, lower_is_better=True)
    cost_saved_usd = round(base_cost - opt_cost, 2)

    base_veh = baseline_summary.get("vehicles_used", 0)
    opt_veh = ortools_summary.get("vehicles_used", 0)
    veh_diff = base_veh - opt_veh

    base_util = baseline_summary.get("avg_capacity_utilization", 0.0)
    opt_util = ortools_summary.get("avg_capacity_utilization", 0.0)
    util_diff_pts = round(opt_util - base_util, 1)

    base_dur = baseline_summary.get("total_duration_hours", 0.0)
    opt_dur = ortools_summary.get("total_duration_hours", 0.0)
    time_savings_pct = safe_pct_improvement(base_dur, opt_dur, lower_is_better=True)

    base_ontime = baseline_summary.get("on_time_rate_pct", 0.0)
    opt_ontime = ortools_summary.get("on_time_rate_pct", 0.0)
    ontime_diff_pts = round(opt_ontime - base_ontime, 1)

    return {
        "baseline": baseline_summary,
        "optimized": ortools_summary,
        "improvements": {
            "distance_saved_km": dist_saved_km,
            "distance_savings_pct": dist_savings_pct,
            "cost_saved_usd": cost_saved_usd,
            "cost_savings_pct": cost_savings_pct,
            "vehicles_reduced_count": veh_diff,
            "utilization_gain_pts": util_diff_pts,
            "time_saved_hours": round(base_dur - opt_dur, 2),
            "time_savings_pct": time_savings_pct,
            "ontime_rate_gain_pts": ontime_diff_pts
        }
    }


def analyze_historical_delays(db_path: Optional[Any] = None) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    SQL analysis of historical delivery delays by reason and location.
    """
    sql_reasons = """
        SELECT 
            delay_reason,
            COUNT(*) as total_delays,
            ROUND(AVG(delay_minutes), 1) as avg_delay_mins,
            SUM(delay_minutes) as total_delay_mins
        FROM historical_deliveries
        WHERE delivery_status = 'Delayed' AND delay_reason IS NOT NULL
        GROUP BY delay_reason
        ORDER BY total_delays DESC;
    """
    df_reasons = execute_sql_query(sql_reasons, db_path=db_path)

    sql_locations = """
        SELECT 
            l.location_name,
            l.city,
            COUNT(h.record_id) as total_deliveries,
            SUM(CASE WHEN h.delivery_status = 'Delayed' THEN 1 ELSE 0 END) as delayed_deliveries,
            ROUND(CAST(SUM(CASE WHEN h.delivery_status = 'Delayed' THEN 1 ELSE 0 END) AS REAL) / COUNT(h.record_id) * 100, 1) as delay_rate_pct,
            ROUND(AVG(h.delay_minutes), 1) as avg_delay_mins
        FROM historical_deliveries h
        JOIN orders o ON h.order_id = o.order_id
        JOIN locations l ON o.location_id = l.location_id
        GROUP BY l.location_id
        ORDER BY delay_rate_pct DESC;
    """
    df_locations = execute_sql_query(sql_locations, db_path=db_path)

    # Overall Summary KPI
    sql_kpi = """
        SELECT 
            COUNT(*) as total_records,
            SUM(CASE WHEN delivery_status = 'On-Time' THEN 1 ELSE 0 END) as on_time_count,
            SUM(CASE WHEN delivery_status = 'Delayed' THEN 1 ELSE 0 END) as delayed_count,
            ROUND(AVG(actual_cost), 2) as avg_delivery_cost,
            ROUND(AVG(distance_km), 2) as avg_delivery_distance
        FROM historical_deliveries;
    """
    df_kpi = execute_sql_query(sql_kpi, db_path=db_path)
    kpi_dict = df_kpi.to_dict("records")[0] if not df_kpi.empty else {}

    return df_reasons, df_locations, kpi_dict


def generate_business_recommendations(comp_dict: Dict[str, Any], df_delay_reasons: pd.DataFrame) -> List[str]:
    """
    Generate dynamic business recommendations based on empirical calculated results.
    """
    recs = []
    imp = comp_dict.get("improvements", {})
    
    cost_saved = imp.get("cost_saved_usd", 0.0)
    cost_pct = imp.get("cost_savings_pct", 0.0)
    dist_saved = imp.get("distance_saved_km", 0.0)
    veh_reduced = imp.get("vehicles_reduced_count", 0)
    util_gain = imp.get("utilization_gain_pts", 0.0)

    if cost_saved > 0:
        recs.append(
            f"**Route Optimization Savings**: Adopting OR-Tools VRP route planning reduces daily transportation costs by **${cost_saved:,.2f} ({cost_pct:.1f}%)** and eliminates **{dist_saved:,.1f} km** of redundant mileage."
        )

    if veh_reduced > 0:
        recs.append(
            f"**Fleet Consolidation**: The optimized routing plan operates with **{veh_reduced} fewer vehicle(s)**, boosting average fleet capacity utilization by **+{util_gain:.1f}% points**, reducing capital & driver overhead."
        )
    elif util_gain < 0:
        recs.append(
            f"**Capacity Adjustment**: Fleet utilization is low. Consider consolidating smaller delivery orders or deploying smaller electric cargo vans."
        )

    if not df_delay_reasons.empty:
        top_reason = df_delay_reasons.iloc[0]
        recs.append(
            f"**Delay Mitigation**: The primary cause of historical delays is **{top_reason['delay_reason']}** ({top_reason['total_delays']} occurrences, averaging {top_reason['avg_delay_mins']} mins). Staggering warehouse departure times away from peak traffic windows is strongly recommended."
        )

    recs.append(
        "**Strategic Recommendation**: Transition from fixed manual territory routes to dynamic daily VRP route optimization to lock in distance and cost efficiencies."
    )

    return recs
