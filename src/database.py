"""
Database management module for Smart Route & Delivery Optimization System.
Provides SQLite schema setup, transactional CRUD operations, and historical run tracking.
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

DB_PATH = Path(__file__).parent.parent / "data" / "delivery_system.db"


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Get a SQLite database connection with row factory enabled."""
    target_path = db_path or DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize SQLite database tables and indexes."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Locations table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS locations (
        location_id TEXT PRIMARY KEY,
        location_name TEXT NOT NULL,
        location_type TEXT NOT NULL, -- 'warehouse' or 'customer'
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        address TEXT,
        city TEXT DEFAULT 'Metropolis'
    );
    """)

    # Vehicles table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        vehicle_id TEXT PRIMARY KEY,
        vehicle_name TEXT NOT NULL,
        vehicle_type TEXT NOT NULL, -- 'Van', 'Electric Van', 'Light Truck', 'Heavy Truck'
        capacity_kg REAL NOT NULL,
        cost_per_km REAL NOT NULL,
        fixed_cost REAL DEFAULT 50.0,
        max_distance_km REAL NOT NULL,
        max_working_hours REAL DEFAULT 9.0,
        shift_start TEXT DEFAULT '08:00',
        shift_end TEXT DEFAULT '18:00',
        is_available INTEGER DEFAULT 1
    );
    """)

    # Orders table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id TEXT PRIMARY KEY,
        customer_name TEXT NOT NULL,
        location_id TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        quantity_kg REAL NOT NULL,
        priority TEXT DEFAULT 'Medium', -- 'High', 'Medium', 'Low'
        time_window_start TEXT DEFAULT '08:00',
        time_window_end TEXT DEFAULT '17:00',
        order_date TEXT NOT NULL,
        status TEXT DEFAULT 'Pending', -- 'Pending', 'Assigned', 'Delivered', 'Delayed', 'Infeasible'
        service_time_mins INTEGER DEFAULT 15,
        FOREIGN KEY (location_id) REFERENCES locations(location_id)
    );
    """)

    # Historical deliveries table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historical_deliveries (
        record_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT NOT NULL,
        vehicle_id TEXT,
        planned_arrival TEXT,
        actual_arrival TEXT,
        delivery_status TEXT NOT NULL, -- 'On-Time', 'Delayed', 'Failed'
        delay_minutes INTEGER DEFAULT 0,
        delay_reason TEXT, -- 'Traffic', 'Customer Unavailable', 'Warehouse Delay', etc.
        delivery_date TEXT NOT NULL,
        actual_cost REAL,
        distance_km REAL
    );
    """)

    # Optimization Runs header
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS optimization_runs (
        run_id TEXT PRIMARY KEY,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        algorithm TEXT NOT NULL, -- 'OR-Tools VRP' or 'Baseline Nearest Neighbor'
        total_orders INTEGER NOT NULL,
        assigned_orders INTEGER NOT NULL,
        unassigned_orders INTEGER NOT NULL,
        vehicles_used INTEGER NOT NULL,
        total_distance_km REAL NOT NULL,
        total_cost REAL NOT NULL,
        avg_capacity_utilization REAL NOT NULL,
        total_duration_hours REAL NOT NULL,
        on_time_rate_pct REAL DEFAULT 100.0,
        execution_time_sec REAL DEFAULT 0.0,
        notes TEXT
    );
    """)

    # Route Stops details for runs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS route_stops (
        stop_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT NOT NULL,
        vehicle_id TEXT NOT NULL,
        stop_sequence INTEGER NOT NULL,
        order_id TEXT, -- NULL for warehouse start/end
        location_id TEXT NOT NULL,
        location_name TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        arrival_time TEXT,
        departure_time TEXT,
        distance_from_prev_km REAL DEFAULT 0.0,
        cumulative_distance_km REAL DEFAULT 0.0,
        load_after_stop_kg REAL DEFAULT 0.0,
        is_warehouse INTEGER DEFAULT 0,
        FOREIGN KEY (run_id) REFERENCES optimization_runs(run_id) ON DELETE CASCADE
    );
    """)

    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stops_run ON route_stops(run_id);")

    conn.commit()
    conn.close()


def execute_transaction(queries: List[Tuple[str, tuple]], db_path: Optional[Path] = None) -> None:
    """Execute multiple queries within a single ACID transaction."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        for sql, params in queries:
            cursor.execute(sql, params)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def save_optimization_run(run_data: Dict[str, Any], route_stops: List[Dict[str, Any]], db_path: Optional[Path] = None) -> None:
    """Save an optimization run header and stop sequence details to SQLite inside a transaction."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO optimization_runs (
                run_id, timestamp, algorithm, total_orders, assigned_orders, unassigned_orders,
                vehicles_used, total_distance_km, total_cost, avg_capacity_utilization,
                total_duration_hours, on_time_rate_pct, execution_time_sec, notes
            ) VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            run_data["run_id"],
            run_data.get("algorithm", "OR-Tools VRP"),
            run_data["total_orders"],
            run_data["assigned_orders"],
            run_data["unassigned_orders"],
            run_data["vehicles_used"],
            run_data["total_distance_km"],
            run_data["total_cost"],
            run_data["avg_capacity_utilization"],
            run_data["total_duration_hours"],
            run_data.get("on_time_rate_pct", 100.0),
            run_data.get("execution_time_sec", 0.0),
            run_data.get("notes", "")
        ))

        # Clear any existing stops for this run_id
        cursor.execute("DELETE FROM route_stops WHERE run_id = ?;", (run_data["run_id"],))

        for stop in route_stops:
            cursor.execute("""
                INSERT INTO route_stops (
                    run_id, vehicle_id, stop_sequence, order_id, location_id, location_name,
                    latitude, longitude, arrival_time, departure_time, distance_from_prev_km,
                    cumulative_distance_km, load_after_stop_kg, is_warehouse
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                run_data["run_id"],
                stop["vehicle_id"],
                stop["stop_sequence"],
                stop.get("order_id"),
                stop["location_id"],
                stop["location_name"],
                stop["latitude"],
                stop["longitude"],
                stop.get("arrival_time"),
                stop.get("departure_time"),
                stop.get("distance_from_prev_km", 0.0),
                stop.get("cumulative_distance_km", 0.0),
                stop.get("load_after_stop_kg", 0.0),
                1 if stop.get("is_warehouse") else 0
            ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def load_table_as_df(table_name: str, db_path: Optional[Path] = None) -> pd.DataFrame:
    """Load an entire SQLite table into a Pandas DataFrame."""
    conn = get_connection(db_path)
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        return df
    finally:
        conn.close()


def execute_sql_query(query: str, params: tuple = (), db_path: Optional[Path] = None) -> pd.DataFrame:
    """Execute custom SQL query and return DataFrame."""
    conn = get_connection(db_path)
    try:
        df = pd.read_sql_query(query, conn, params=params)
        return df
    finally:
        conn.close()
