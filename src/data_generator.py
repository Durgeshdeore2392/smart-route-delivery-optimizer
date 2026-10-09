"""
Synthetic Data Generator for Logistics & Route Optimization System.
Generates realistic datasets deterministically using fixed random seeds.
Creates: locations.csv, vehicles.csv, orders.csv, historical_deliveries.csv.
"""

import os
import sys
import random
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Tuple, Dict, List

# Ensure parent directory is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

DATA_DIR = Path(__file__).parent.parent / "data"

# Center coordinates: Chicago Metropolitan Area
WAREHOUSE_LAT = 41.8781
WAREHOUSE_LON = -87.6298


def generate_synthetic_data(seed: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Generate deterministic synthetic datasets for logistics supply chain optimization.
    Returns: (df_locations, df_vehicles, df_orders, df_historical)
    """
    random.seed(seed)
    np.random.seed(seed)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. GENERATE LOCATIONS (1 Warehouse + 30 Customer Locations)
    locations = []
    # Central Warehouse
    locations.append({
        "location_id": "LOC-000",
        "location_name": "Central Distribution Hub",
        "location_type": "warehouse",
        "latitude": WAREHOUSE_LAT,
        "longitude": WAREHOUSE_LON,
        "address": "100 Logistics Blvd, Central Hub",
        "city": "Chicago"
    })

    neighborhoods = [
        "West Loop", "River North", "Lincoln Park", "Lakeview", "Hyde Park",
        "Pilsen", "Logan Square", "Wicker Park", "Bridgeport", "Uptown",
        "Rogers Park", "Evanston", "Oak Park", "Cicero", "Skokie",
        "Des Plaines", "Schaumburg", "Naperville", "Aurora", "Joliet",
        "Elgin", "Waukegan", "Bolingbrook", "Arlington Heights", "Orland Park",
        "Hammond", "Gary", "Wheaton", "Downers Grove", "Lombard"
    ]

    for i, name in enumerate(neighborhoods, start=1):
        # Generate coordinates within ~25 km radius of warehouse
        lat = WAREHOUSE_LAT + np.random.uniform(-0.18, 0.18)
        lon = WAREHOUSE_LON + np.random.uniform(-0.22, 0.22)
        locations.append({
            "location_id": f"LOC-{i:03d}",
            "location_name": f"{name} Center",
            "location_type": "customer",
            "latitude": round(lat, 5),
            "longitude": round(lon, 5),
            "address": f"{random.randint(100, 9999)} {name} Ave",
            "city": name if i <= 15 else "Greater Chicago Area"
        })

    df_locations = pd.DataFrame(locations)

    # 2. GENERATE VEHICLES (20 Vehicles with varied types, capacities, costs)
    vehicle_types = [
        ("Van", 350.0, 0.90, 45.0, 220.0),
        ("Electric Van", 280.0, 0.75, 40.0, 180.0),
        ("Light Truck", 650.0, 1.35, 65.0, 320.0),
        ("Heavy Truck", 1200.0, 2.10, 95.0, 450.0)
    ]

    vehicles = []
    for i in range(1, 21):
        # Pick type weighted
        v_type, base_cap, base_cost, base_fixed, max_dist = vehicle_types[i % 4]
        # Add slight variation per vehicle
        capacity = round(base_cap * random.uniform(0.9, 1.1), 0)
        cost_per_km = round(base_cost * random.uniform(0.95, 1.05), 2)
        fixed_cost = round(base_fixed * random.uniform(0.95, 1.05), 2)
        max_distance = round(max_dist * random.uniform(0.9, 1.1), 0)
        
        # Make vehicle #19 unavailable for realistic fleet availability constraint demonstration
        is_avail = 0 if i == 19 else 1

        vehicles.append({
            "vehicle_id": f"VEH-{i:03d}",
            "vehicle_name": f"{v_type} #{i:02d}",
            "vehicle_type": v_type,
            "capacity_kg": capacity,
            "cost_per_km": cost_per_km,
            "fixed_cost": fixed_cost,
            "max_distance_km": max_distance,
            "max_working_hours": 9.0,
            "shift_start": "08:00",
            "shift_end": "18:00",
            "is_available": is_avail
        })

    df_vehicles = pd.DataFrame(vehicles)

    # 3. GENERATE ORDERS (500 Delivery Orders)
    customer_locs = df_locations[df_locations["location_type"] == "customer"].to_dict("records")
    
    company_prefixes = ["Apex", "Beacon", "Crest", "Delta", "Echo", "Falcon", "Global", "Horizon", "Infinity", "Jupiter"]
    company_suffixes = ["Retail", "Logistics", "Mart", "Supply", "Depot", "Direct", "Express", "Trader", "Hub", "Store"]

    time_windows = [
        ("08:00", "12:00"),
        ("09:00", "13:00"),
        ("10:00", "14:00"),
        ("11:00", "15:00"),
        ("12:00", "16:00"),
        ("08:00", "17:00")  # Full day
    ]

    priorities = ["High", "Medium", "Low"]
    priority_weights = [0.25, 0.55, 0.20]

    base_date = datetime.now().date()
    
    orders = []
    for i in range(1, 501):
        loc = random.choice(customer_locs)
        c_name = f"{random.choice(company_prefixes)} {random.choice(company_suffixes)} #{random.randint(100, 999)}"
        
        # Quantity between 15 kg and 280 kg (some oversized to test infeasibility / vehicle limits)
        if i == 500:
            qty = 1500.0  # Deliberate infeasible order exceeding max vehicle capacity (1200kg)
        else:
            qty = round(random.choice([15.0, 25.0, 40.0, 60.0, 85.0, 110.0, 140.0, 180.0, 220.0, 260.0]), 1)
        
        tw_start, tw_end = random.choice(time_windows)
        prio = random.choices(priorities, weights=priority_weights)[0]
        
        # Order date across past 7 days and next 7 days
        day_offset = random.randint(-7, 7)
        ord_date = (base_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")
        
        status = "Pending"
        if day_offset < 0:
            status = random.choices(["Delivered", "Delayed"], weights=[0.85, 0.15])[0]

        orders.append({
            "order_id": f"ORD-{i:04d}",
            "customer_name": c_name,
            "location_id": loc["location_id"],
            "latitude": loc["latitude"],
            "longitude": loc["longitude"],
            "quantity_kg": qty,
            "priority": prio,
            "time_window_start": tw_start,
            "time_window_end": tw_end,
            "order_date": ord_date,
            "status": status,
            "service_time_mins": 15
        })

    df_orders = pd.DataFrame(orders)

    # 4. GENERATE HISTORICAL DELIVERIES (500 Historical Performance Records)
    historical = []
    delay_reasons = [
        "Traffic Congestion",
        "Customer Unavailable",
        "Warehouse Loading Delay",
        "Vehicle Mechanical Issue",
        "Weather / Severe Rain",
        "Incorrect Address"
    ]
    delay_weights = [0.45, 0.20, 0.15, 0.10, 0.06, 0.04]

    for i in range(1, 501):
        order_ref = df_orders.iloc[i - 1]
        v_assigned = f"VEH-{(i % 18) + 1:03d}"
        
        # Baseline delivery outcome
        is_delayed = random.random() < 0.18
        
        if is_delayed:
            status = "Delayed"
            delay_mins = random.randint(15, 120)
            reason = random.choices(delay_reasons, weights=delay_weights)[0]
            planned_h = random.randint(9, 14)
            actual_h = planned_h + (delay_mins // 60)
            actual_m = (delay_mins % 60)
            planned_arr = f"{planned_h:02d}:00"
            actual_arr = f"{actual_h:02d}:{actual_m:02d}"
        else:
            status = "On-Time"
            delay_mins = 0
            reason = None
            planned_h = random.randint(9, 16)
            planned_arr = f"{planned_h:02d}:00"
            actual_arr = f"{planned_h:02d}:{random.randint(0, 14):02d}"

        dist = round(random.uniform(5.0, 35.0), 2)
        cost = round(dist * random.uniform(1.1, 1.8) + 15.0, 2)

        historical.append({
            "record_id": i,
            "order_id": order_ref["order_id"],
            "vehicle_id": v_assigned,
            "planned_arrival": planned_arr,
            "actual_arrival": actual_arr,
            "delivery_status": status,
            "delay_minutes": delay_mins,
            "delay_reason": reason,
            "delivery_date": order_ref["order_date"],
            "actual_cost": cost,
            "distance_km": dist
        })

    df_historical = pd.DataFrame(historical)

    # Save to CSV files
    df_locations.to_csv(DATA_DIR / "locations.csv", index=False)
    df_vehicles.to_csv(DATA_DIR / "vehicles.csv", index=False)
    df_orders.to_csv(DATA_DIR / "orders.csv", index=False)
    df_historical.to_csv(DATA_DIR / "historical_deliveries.csv", index=False)

    return df_locations, df_vehicles, df_orders, df_historical


def seed_database_from_csv(db_path=None) -> None:
    """Load generated CSV datasets into SQLite database."""
    from src.database import init_db, get_connection
    init_db(db_path)

    conn = get_connection(db_path)
    cursor = conn.cursor()

    df_locations = pd.read_csv(DATA_DIR / "locations.csv")
    df_vehicles = pd.read_csv(DATA_DIR / "vehicles.csv")
    df_orders = pd.read_csv(DATA_DIR / "orders.csv")
    df_historical = pd.read_csv(DATA_DIR / "historical_deliveries.csv")

    df_locations.to_sql("locations", conn, if_exists="replace", index=False)
    df_vehicles.to_sql("vehicles", conn, if_exists="replace", index=False)
    df_orders.to_sql("orders", conn, if_exists="replace", index=False)
    df_historical.to_sql("historical_deliveries", conn, if_exists="replace", index=False)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    generate_synthetic_data()
    seed_database_from_csv()
    print("Synthetic data generated and SQLite database initialized successfully!")
