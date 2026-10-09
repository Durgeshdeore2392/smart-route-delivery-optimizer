"""
Unit tests for delivery analytics and reporting modules.
"""

import pytest
from src.delivery_analytics import safe_pct_improvement, compare_baseline_vs_optimized
from src.reporting import generate_comparison_report_df, generate_vehicle_manifest_df


def test_safe_pct_improvement():
    # Lower is better (distance/cost)
    assert safe_pct_improvement(100.0, 80.0, lower_is_better=True) == 20.0
    assert safe_pct_improvement(0.0, 50.0, lower_is_better=True) == 0.0  # Zero denominator safe

    # Higher is better (utilization/on-time)
    assert safe_pct_improvement(60.0, 75.0, lower_is_better=False) == 25.0


def test_compare_baseline_vs_optimized():
    base = {
        "total_orders": 50,
        "assigned_orders": 45,
        "unassigned_orders": 5,
        "vehicles_used": 5,
        "total_distance_km": 500.0,
        "total_cost": 750.0,
        "avg_capacity_utilization": 60.0,
        "total_duration_hours": 20.0,
        "on_time_rate_pct": 85.0
    }

    opt = {
        "total_orders": 50,
        "assigned_orders": 49,
        "unassigned_orders": 1,
        "vehicles_used": 4,
        "total_distance_km": 400.0,
        "total_cost": 600.0,
        "avg_capacity_utilization": 78.0,
        "total_duration_hours": 16.0,
        "on_time_rate_pct": 96.0
    }

    comp = compare_baseline_vs_optimized(base, opt)
    imp = comp["improvements"]

    assert imp["distance_saved_km"] == 100.0
    assert imp["distance_savings_pct"] == 20.0
    assert imp["cost_saved_usd"] == 150.0
    assert imp["cost_savings_pct"] == 20.0
    assert imp["vehicles_reduced_count"] == 1
    assert imp["utilization_gain_pts"] == 18.0

    df_report = generate_comparison_report_df(comp)
    assert len(df_report) == 9
