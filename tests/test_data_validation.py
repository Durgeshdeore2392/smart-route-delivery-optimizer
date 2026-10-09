"""
Unit tests for data validation module.
"""

import pytest
import pandas as pd
from src.data_validation import validate_orders_df, validate_vehicles_df, validate_time_window


def test_validate_time_window():
    assert validate_time_window("08:00", "12:00") is True
    assert validate_time_window("14:30", "17:00") is True
    assert validate_time_window("12:00", "08:00") is False  # Inverted
    assert validate_time_window("invalid", "12:00") is False


def test_validate_orders_df():
    data = [
        {
            "order_id": "ORD-001",
            "customer_name": "Cust A",
            "location_id": "LOC-001",
            "latitude": 41.8781,
            "longitude": -87.6298,
            "quantity_kg": 50.0,
            "priority": "High",
            "time_window_start": "08:00",
            "time_window_end": "12:00"
        },
        {
            "order_id": "ORD-001",  # Duplicate ID
            "customer_name": "Cust A Dup",
            "location_id": "LOC-001",
            "latitude": 41.8781,
            "longitude": -87.6298,
            "quantity_kg": 50.0,
            "priority": "High",
            "time_window_start": "08:00",
            "time_window_end": "12:00"
        },
        {
            "order_id": "ORD-002",
            "customer_name": "Cust B",
            "location_id": "LOC-002",
            "latitude": 41.8781,
            "longitude": -87.6298,
            "quantity_kg": -10.0,  # Invalid negative quantity
            "priority": "Medium",
            "time_window_start": "08:00",
            "time_window_end": "12:00"
        }
    ]
    df = pd.DataFrame(data)
    cleaned_df, report = validate_orders_df(df)

    assert report["valid_count"] == 1
    assert report["invalid_count"] == 2
    assert "ORD-001" in cleaned_df["order_id"].values
    assert len(report["errors"]) > 0


def test_validate_vehicles_df():
    data = [
        {
            "vehicle_id": "VEH-001",
            "vehicle_type": "Van",
            "capacity_kg": 300.0,
            "cost_per_km": 1.2,
            "max_distance_km": 200.0
        },
        {
            "vehicle_id": "VEH-002",
            "vehicle_type": "Truck",
            "capacity_kg": -50.0,  # Invalid capacity
            "cost_per_km": 2.0,
            "max_distance_km": 300.0
        }
    ]
    df = pd.DataFrame(data)
    cleaned_df, report = validate_vehicles_df(df)

    assert report["valid_count"] == 1
    assert "VEH-001" in cleaned_df["vehicle_id"].values
    assert "VEH-002" not in cleaned_df["vehicle_id"].values
