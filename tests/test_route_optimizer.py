"""
Unit tests for Google OR-Tools VRP route optimizer.
"""

import pytest
from src.route_optimizer import run_ortools_vrp


def test_ortools_vrp_simple():
    warehouse = {"location_id": "LOC-000", "location_name": "Hub", "latitude": 41.8781, "longitude": -87.6298}
    vehicles = [{"vehicle_id": "VEH-001", "capacity_kg": 500, "max_distance_km": 200, "cost_per_km": 1.0, "fixed_cost": 50, "is_available": 1}]
    orders = [
        {"order_id": "ORD-001", "customer_name": "Cust 1", "quantity_kg": 100, "latitude": 41.8850, "longitude": -87.6300, "priority": "High", "time_window_start": "08:00", "time_window_end": "17:00", "service_time_mins": 15},
        {"order_id": "ORD-002", "customer_name": "Cust 2", "quantity_kg": 150, "latitude": 41.8900, "longitude": -87.6350, "priority": "Medium", "time_window_start": "08:00", "time_window_end": "17:00", "service_time_mins": 15}
    ]

    summary, stops, unassigned_diag = run_ortools_vrp(warehouse, orders, vehicles, search_time_limit_sec=2)

    assert summary["assigned_orders"] == 2
    assert summary["unassigned_orders"] == 0
    assert summary["vehicles_used"] == 1
    assert summary["total_distance_km"] > 0
    assert len(stops) == 4
    assert len(unassigned_diag) == 0


def test_ortools_vrp_infeasible_oversized_order():
    warehouse = {"location_id": "LOC-000", "location_name": "Hub", "latitude": 41.8781, "longitude": -87.6298}
    # Max vehicle capacity = 300 kg
    vehicles = [{"vehicle_id": "VEH-001", "capacity_kg": 300, "max_distance_km": 200, "cost_per_km": 1.0, "fixed_cost": 50, "is_available": 1}]
    # Order quantity = 800 kg (exceeds vehicle capacity)
    orders = [
        {"order_id": "ORD-999", "customer_name": "Oversized Cust", "quantity_kg": 800, "latitude": 41.8850, "longitude": -87.6300, "priority": "High", "time_window_start": "08:00", "time_window_end": "17:00", "service_time_mins": 15}
    ]

    summary, stops, unassigned_diag = run_ortools_vrp(warehouse, orders, vehicles, search_time_limit_sec=2)

    assert summary["assigned_orders"] == 0
    assert summary["unassigned_orders"] == 1
    assert len(unassigned_diag) == 1
    assert unassigned_diag[0]["order_id"] == "ORD-999"
    assert "exceeds maximum single vehicle capacity" in unassigned_diag[0]["reason"]
