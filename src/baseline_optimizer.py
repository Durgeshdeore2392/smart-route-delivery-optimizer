"""
Baseline Route Optimizer module using Greedy Nearest-Neighbor heuristic.
Provides a benchmark for comparing optimization results from OR-Tools.
"""

import math
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timedelta

from src.distance_matrix import build_distance_and_time_matrices


def time_to_minutes(time_str: str) -> int:
    """Convert 'HH:MM' string to minutes from start of day."""
    h, m = map(int, time_str.split(":"))
    return h * 60 + m


def minutes_to_time(mins: float) -> str:
    """Convert minutes from start of day to 'HH:MM' string."""
    h = int(mins // 60) % 24
    m = int(mins % 60)
    return f"{h:02d}:{m:02d}"


def run_baseline_optimization(
    warehouse: Dict[str, Any],
    orders: List[Dict[str, Any]],
    vehicles: List[Dict[str, Any]],
    circuity_factor: float = 1.30,
    avg_speed_kmh: float = 40.0,
    service_time_mins: float = 15.0
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Run Nearest-Neighbor heuristic baseline routing algorithm.

    Returns:
    - summary: Dict containing baseline performance metrics.
    - route_stops: List of stop dicts formatted for DB insertion and visualization.
    """
    # Filter available vehicles
    avail_vehicles = [v for v in vehicles if v.get("is_available", 1) == 1]
    if not avail_vehicles or not orders:
        return {
            "algorithm": "Baseline Nearest Neighbor",
            "total_orders": len(orders),
            "assigned_orders": 0,
            "unassigned_orders": len(orders),
            "vehicles_used": 0,
            "total_distance_km": 0.0,
            "total_cost": 0.0,
            "avg_capacity_utilization": 0.0,
            "total_duration_hours": 0.0,
            "on_time_rate_pct": 0.0,
            "unassigned_order_ids": [o["order_id"] for o in orders]
        }, []

    # Prepare location nodes: Index 0 = Warehouse, Index 1..N = Orders
    all_locations = [warehouse] + orders
    dist_km, time_mins, _ = build_distance_and_time_matrices(
        all_locations, circuity_factor, avg_speed_kmh, service_time_mins
    )

    unassigned_indices = list(range(1, len(all_locations)))
    all_route_stops = []
    vehicles_used_count = 0
    total_fleet_distance_km = 0.0
    total_fleet_cost = 0.0
    total_fleet_duration_mins = 0.0
    vehicle_utilizations = []
    on_time_count = 0
    total_assigned_count = 0

    shift_start_mins = 8 * 60  # 08:00 AM

    for vehicle in avail_vehicles:
        if not unassigned_indices:
            break

        v_id = vehicle["vehicle_id"]
        v_cap = vehicle["capacity_kg"]
        v_max_dist = vehicle["max_distance_km"]
        v_cost_km = vehicle["cost_per_km"]
        v_fixed_cost = vehicle.get("fixed_cost", 50.0)

        current_node = 0
        current_load = 0.0
        current_dist = 0.0
        current_time_mins = float(shift_start_mins)
        
        route_nodes = [0]  # Start at warehouse
        route_stop_records = []

        # Warehouse start stop
        route_stop_records.append({
            "vehicle_id": v_id,
            "stop_sequence": 0,
            "order_id": None,
            "location_id": warehouse.get("location_id", "LOC-000"),
            "location_name": warehouse.get("location_name", "Warehouse"),
            "latitude": warehouse["latitude"],
            "longitude": warehouse["longitude"],
            "arrival_time": minutes_to_time(current_time_mins),
            "departure_time": minutes_to_time(current_time_mins),
            "distance_from_prev_km": 0.0,
            "cumulative_distance_km": 0.0,
            "load_after_stop_kg": 0.0,
            "is_warehouse": True
        })

        seq = 1
        vehicle_assigned = False

        while unassigned_indices:
            # Find nearest feasible unassigned order
            best_idx = None
            best_dist = float("inf")

            for candidate_idx in unassigned_indices:
                cand_order = orders[candidate_idx - 1]
                cand_qty = cand_order["quantity_kg"]

                # Check capacity constraint
                if current_load + cand_qty > v_cap:
                    continue

                # Check distance constraint (current -> cand -> warehouse)
                leg_dist = dist_km[current_node, candidate_idx]
                return_dist = dist_km[candidate_idx, 0]
                if current_dist + leg_dist + return_dist > v_max_dist:
                    continue

                if leg_dist < best_dist:
                    best_dist = leg_dist
                    best_idx = candidate_idx

            if best_idx is None:
                # No more feasible orders for this vehicle
                break

            # Assign best candidate
            unassigned_indices.remove(best_idx)
            vehicle_assigned = True
            cand_order = orders[best_idx - 1]

            leg_dist = dist_km[current_node, best_idx]
            travel_duration = time_mins[current_node, best_idx]
            current_dist += leg_dist
            current_time_mins += travel_duration
            current_load += cand_order["quantity_kg"]
            current_node = best_idx

            # Check time window on-time status
            tw_end = time_to_minutes(cand_order.get("time_window_end", "17:00"))
            if current_time_mins <= tw_end:
                on_time_count += 1
            total_assigned_count += 1

            dep_time_mins = current_time_mins + cand_order.get("service_time_mins", 15)

            route_stop_records.append({
                "vehicle_id": v_id,
                "stop_sequence": seq,
                "order_id": cand_order["order_id"],
                "location_id": cand_order.get("location_id", f"LOC-{best_idx}"),
                "location_name": cand_order.get("customer_name", f"Order #{best_idx}"),
                "latitude": cand_order["latitude"],
                "longitude": cand_order["longitude"],
                "arrival_time": minutes_to_time(current_time_mins),
                "departure_time": minutes_to_time(dep_time_mins),
                "distance_from_prev_km": round(leg_dist, 2),
                "cumulative_distance_km": round(current_dist, 2),
                "load_after_stop_kg": round(current_load, 1),
                "is_warehouse": False
            })
            current_time_mins = dep_time_mins
            seq += 1

        if vehicle_assigned:
            # Return to warehouse
            return_dist = dist_km[current_node, 0]
            travel_duration = time_mins[current_node, 0]
            current_dist += return_dist
            current_time_mins += travel_duration

            route_stop_records.append({
                "vehicle_id": v_id,
                "stop_sequence": seq,
                "order_id": None,
                "location_id": warehouse.get("location_id", "LOC-000"),
                "location_name": warehouse.get("location_name", "Warehouse"),
                "latitude": warehouse["latitude"],
                "longitude": warehouse["longitude"],
                "arrival_time": minutes_to_time(current_time_mins),
                "departure_time": minutes_to_time(current_time_mins),
                "distance_from_prev_km": round(return_dist, 2),
                "cumulative_distance_km": round(current_dist, 2),
                "load_after_stop_kg": round(current_load, 1),
                "is_warehouse": True
            })

            vehicles_used_count += 1
            total_fleet_distance_km += current_dist
            v_cost = (current_dist * v_cost_km) + v_fixed_cost
            total_fleet_cost += v_cost
            v_duration = current_time_mins - shift_start_mins
            total_fleet_duration_mins += v_duration
            vehicle_utilizations.append((current_load / v_cap) * 100.0)

            all_route_stops.extend(route_stop_records)

    unassigned_order_ids = [orders[idx - 1]["order_id"] for idx in unassigned_indices]
    avg_util = float(np.mean(vehicle_utilizations)) if vehicle_utilizations else 0.0
    on_time_pct = (on_time_count / total_assigned_count * 100.0) if total_assigned_count > 0 else 0.0

    summary = {
        "algorithm": "Baseline Nearest Neighbor",
        "total_orders": len(orders),
        "assigned_orders": total_assigned_count,
        "unassigned_orders": len(unassigned_order_ids),
        "vehicles_used": vehicles_used_count,
        "total_distance_km": round(total_fleet_distance_km, 2),
        "total_cost": round(total_fleet_cost, 2),
        "avg_capacity_utilization": round(avg_util, 1),
        "total_duration_hours": round(total_fleet_duration_mins / 60.0, 2),
        "on_time_rate_pct": round(on_time_pct, 1),
        "unassigned_order_ids": unassigned_order_ids
    }

    return summary, all_route_stops
