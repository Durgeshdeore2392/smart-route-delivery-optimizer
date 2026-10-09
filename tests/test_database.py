"""
Unit tests for database module.
"""

import pytest
import sqlite3
import pandas as pd
from pathlib import Path

from src.database import init_db, get_connection, save_optimization_run, load_table_as_df


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_delivery.db"
    init_db(db_file)
    return db_file


def test_init_db(temp_db):
    conn = get_connection(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    assert "locations" in tables
    assert "vehicles" in tables
    assert "orders" in tables
    assert "historical_deliveries" in tables
    assert "optimization_runs" in tables
    assert "route_stops" in tables


def test_save_and_load_optimization_run(temp_db):
    run_data = {
        "run_id": "RUN-TEST-001",
        "algorithm": "OR-Tools VRP",
        "total_orders": 10,
        "assigned_orders": 9,
        "unassigned_orders": 1,
        "vehicles_used": 2,
        "total_distance_km": 45.5,
        "total_cost": 120.0,
        "avg_capacity_utilization": 85.0,
        "total_duration_hours": 3.5,
        "on_time_rate_pct": 100.0,
        "execution_time_sec": 0.5,
        "notes": "Test run"
    }

    stops = [
        {
            "vehicle_id": "VEH-001",
            "stop_sequence": 0,
            "order_id": None,
            "location_id": "LOC-000",
            "location_name": "Warehouse",
            "latitude": 41.8781,
            "longitude": -87.6298,
            "arrival_time": "08:00",
            "departure_time": "08:00",
            "distance_from_prev_km": 0.0,
            "cumulative_distance_km": 0.0,
            "load_after_stop_kg": 0.0,
            "is_warehouse": True
        },
        {
            "vehicle_id": "VEH-001",
            "stop_sequence": 1,
            "order_id": "ORD-0001",
            "location_id": "LOC-001",
            "location_name": "Test Customer",
            "latitude": 41.8850,
            "longitude": -87.6300,
            "arrival_time": "08:15",
            "departure_time": "08:30",
            "distance_from_prev_km": 3.2,
            "cumulative_distance_km": 3.2,
            "load_after_stop_kg": 50.0,
            "is_warehouse": False
        }
    ]

    save_optimization_run(run_data, stops, temp_db)

    df_runs = load_table_as_df("optimization_runs", temp_db)
    df_stops = load_table_as_df("route_stops", temp_db)

    assert len(df_runs) == 1
    assert df_runs.iloc[0]["run_id"] == "RUN-TEST-001"
    assert len(df_stops) == 2
    assert df_stops.iloc[1]["order_id"] == "ORD-0001"
