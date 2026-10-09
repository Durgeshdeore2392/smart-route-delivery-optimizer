"""
Unit tests for Baseline Nearest Neighbor optimizer.
"""

import pytest
from src.baseline_optimizer import run_baseline_optimization


def test_baseline_empty_orders():
    warehouse = {"location_id": "LOC-000", "latitude": 41.8781, "longitude": -87.6298}
    vehicles = [{"vehicle_id": "VEH-001", "capacity_kg": 500, "max_distance_km": 200, "cost_per_km": 1.0, "is_available": 1}]
    orders = []

    summary, stops = run_baseline_optimization(warehouse, orders, vehicles)
    assert summary["assigned_orders"] == 0
    assert summary["total_distance_km"] == 0.0
    assert len(stops) == 0


def test_baseline_simple_routing():
    warehouse = {"location_id": "LOC-000", "location_name": "Hub", "latitude": 41.8781, "longitude": -87.6298}
    vehicles = [{"vehicle_id": "VEH-001", "capacity_kg": 500, "max_distance_km": 200, "cost_per_km": 1.0, "fixed_cost": 50, "is_available": 1}]
    orders = [
        {"order_id": "ORD-001", "customer_name": "Cust 1", "quantity_kg": 100, "latitude": 41.8850, "longitude": -87.6300, "time_window_end": "17:00", "service_time_mins": 15},
        {"order_id": "ORD-002", "customer_name": "Cust 2", "quantity_kg": 150, "latitude": 41.8900, "longitude": -87.6350, "time_window_end": "17:00", "service_time_mins": 15}
    ]

    summary, stops = run_baseline_optimization(warehouse, orders, vehicles)

    assert summary["assigned_orders"] == 2
    assert summary["unassigned_orders"] == 0
    assert summary["vehicles_used"] == 1
    assert summary["total_distance_km"] > 0
    assert summary["total_cost"] > 50.0
    # Stop sequence: Warehouse (0) -> ORD-001 (1) -> ORD-002 (2) -> Warehouse (3)
    assert len(stops) == 4
    assert stops[0]["is_warehouse"] is True
    assert stops[-1]["is_warehouse"] is True
