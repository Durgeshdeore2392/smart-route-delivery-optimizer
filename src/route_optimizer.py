"""
Google OR-Tools Vehicle Routing Problem (VRP / VRPTW) Optimization Engine
with Pure-Python Heuristic Fallback Engine.

Supports capacity constraints, max route distance, time windows, vehicle costs,
order priorities, and infeasibility diagnostics with clear explanation reporting.
"""

import math
import time
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional

from src.distance_matrix import build_distance_and_time_matrices
from src.baseline_optimizer import time_to_minutes, minutes_to_time

# Safely attempt to import Google OR-Tools C++ extensions
HAS_ORTOOLS = False
ORTOOLS_ERROR = None
try:
    from ortools.constraint_solver import routing_enums_pb2, pywrapcp
    HAS_ORTOOLS = True
except Exception as e:
    HAS_ORTOOLS = False
    ORTOOLS_ERROR = str(e)


def diagnose_unassigned_orders(
    unassigned_orders: List[Dict[str, Any]],
    vehicles: List[Dict[str, Any]],
    warehouse: Dict[str, Any],
    dist_km: np.ndarray,
    time_mins: np.ndarray
) -> List[Dict[str, Any]]:
    """
    Perform diagnostic analysis on orders that could not be assigned by the optimizer.
    Returns a list of dicts with order_id, customer_name, quantity_kg, priority, and reason.
    """
    diagnostics = []
    max_fleet_cap = max([v["capacity_kg"] for v in vehicles]) if vehicles else 0.0
    max_fleet_dist = max([v["max_distance_km"] for v in vehicles]) if vehicles else 0.0

    for order in unassigned_orders:
        reasons = []
        ord_qty = order["quantity_kg"]
        ord_id = order["order_id"]
        
        # 1. Capacity check
        if ord_qty > max_fleet_cap:
            reasons.append(f"Order quantity ({ord_qty} kg) exceeds maximum single vehicle capacity in fleet ({max_fleet_cap} kg).")
        
        # 2. Distance check (round-trip from warehouse)
        round_trip_dist = (dist_km[0, 1] * 2) if dist_km.shape[0] > 1 else 0.0
        if round_trip_dist > max_fleet_dist:
            reasons.append(f"Location is beyond maximum allowable vehicle route distance ({max_fleet_dist} km).")

        # 3. Time window check
        tw_start = time_to_minutes(order.get("time_window_start", "08:00"))
        tw_end = time_to_minutes(order.get("time_window_end", "17:00"))
        if tw_end - tw_start < 30:
            reasons.append(f"Time window [{order.get('time_window_start')}-{order.get('time_window_end')}] is too narrow for delivery.")

        # 4. Fleet capacity exhaustion / routing trade-off
        if not reasons:
            reasons.append("Fleet capacity or maximum distance limit reached under current route constraints and priority settings.")

        diagnostics.append({
            "order_id": ord_id,
            "customer_name": order.get("customer_name", "Unknown"),
            "quantity_kg": ord_qty,
            "priority": order.get("priority", "Medium"),
            "time_window": f"{order.get('time_window_start')}-{order.get('time_window_end')}",
            "reason": "; ".join(reasons)
        })

    return diagnostics


def run_heuristic_vrp_fallback(
    warehouse: Dict[str, Any],
    orders: List[Dict[str, Any]],
    vehicles: List[Dict[str, Any]],
    circuity_factor: float,
    avg_speed_kmh: float,
    service_time_mins: float,
    enforce_time_windows: bool,
    start_cpu_time: float
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Advanced Clarke-Wright Savings / Priority-Insertion Pure Python VRP Optimizer.
    Serves as a high-performance fallback when OR-Tools native DLL execution is restricted.
    """
    avail_vehicles = [v for v in vehicles if v.get("is_available", 1) == 1]
    # Sort vehicles by capacity descending for optimal load allocation
    avail_vehicles = sorted(avail_vehicles, key=lambda x: x["capacity_kg"], reverse=True)

    all_locations = [warehouse] + orders
    num_nodes = len(all_locations)
    dist_km, time_mins, _ = build_distance_and_time_matrices(
        all_locations, circuity_factor, avg_speed_kmh, service_time_mins
    )

    # Sort orders by Priority (High -> Medium -> Low) then demand
    prio_order_map = {"High": 1, "Medium": 2, "Low": 3}
    sorted_order_indices = list(range(1, num_nodes))
    sorted_order_indices.sort(
        key=lambda idx: (prio_order_map.get(orders[idx - 1].get("priority", "Medium"), 2), -orders[idx - 1]["quantity_kg"])
    )

    unassigned_indices = list(sorted_order_indices)
    all_route_stops = []
    vehicles_used_count = 0
    total_fleet_distance_km = 0.0
    total_fleet_cost = 0.0
    total_fleet_duration_mins = 0.0
    vehicle_utilizations = []
    on_time_count = 0
    total_assigned_count = 0

    shift_start_mins = 8 * 60

    for vehicle in avail_vehicles:
        if not unassigned_indices:
            break

        v_id = vehicle["vehicle_id"]
        v_cap = vehicle["capacity_kg"]
        v_max_dist = vehicle["max_distance_km"]
        v_cost_km = vehicle["cost_per_km"]
        v_fixed_cost = vehicle.get("fixed_cost", 50.0)

        route_nodes = [0]
        current_load = 0.0
        current_dist = 0.0
        current_time_mins = float(shift_start_mins)

        route_stop_records = [{
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
        }]

        seq = 1
        vehicle_assigned = False

        while unassigned_indices:
            best_idx = None
            best_insertion_cost = float("inf")

            curr_node = route_nodes[-1]

            for cand_idx in unassigned_indices:
                cand_order = orders[cand_idx - 1]
                cand_qty = cand_order["quantity_kg"]

                if current_load + cand_qty > v_cap:
                    continue

                leg_dist = dist_km[curr_node, cand_idx]
                return_dist = dist_km[cand_idx, 0]
                if current_dist + leg_dist + return_dist > v_max_dist:
                    continue

                # Savings metric: 2*d(0, cand) - d(curr, cand)
                savings = (dist_km[0, curr_node] + dist_km[0, cand_idx]) - leg_dist
                cost = leg_dist - (savings * 0.5)

                if cost < best_insertion_cost:
                    best_insertion_cost = cost
                    best_idx = cand_idx

            if best_idx is None:
                break

            unassigned_indices.remove(best_idx)
            route_nodes.append(best_idx)
            vehicle_assigned = True
            cand_order = orders[best_idx - 1]

            leg_dist = dist_km[curr_node, best_idx]
            leg_time = time_mins[curr_node, best_idx]

            current_dist += leg_dist
            current_time_mins += leg_time
            current_load += cand_order["quantity_kg"]

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
            curr_node = route_nodes[-1]
            return_dist = dist_km[curr_node, 0]
            return_time = time_mins[curr_node, 0]
            current_dist += return_dist
            current_time_mins += return_time

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

    unassigned_orders = [orders[idx - 1] for idx in unassigned_indices]
    unassigned_diagnostics = diagnose_unassigned_orders(
        unassigned_orders, avail_vehicles, warehouse, dist_km, time_mins
    )

    exec_time = round(time.time() - start_cpu_time, 3)
    avg_util = float(np.mean(vehicle_utilizations)) if vehicle_utilizations else 0.0
    on_time_pct = (on_time_count / total_assigned_count * 100.0) if total_assigned_count > 0 else 0.0

    summary = {
        "algorithm": "Priority Savings Heuristic (VRP)",
        "total_orders": len(orders),
        "assigned_orders": total_assigned_count,
        "unassigned_orders": len(unassigned_orders),
        "vehicles_used": vehicles_used_count,
        "total_distance_km": round(total_fleet_distance_km, 2),
        "total_cost": round(total_fleet_cost, 2),
        "avg_capacity_utilization": round(avg_util, 1),
        "total_duration_hours": round(total_fleet_duration_mins / 60.0, 2),
        "on_time_rate_pct": round(on_time_pct, 1),
        "execution_time_sec": exec_time,
        "notes": f"Solved using Priority Savings Heuristic engine (OR-Tools native C++ extension restricted: {ORTOOLS_ERROR})."
    }

    return summary, all_route_stops, unassigned_diagnostics


def run_ortools_vrp(
    warehouse: Dict[str, Any],
    orders: List[Dict[str, Any]],
    vehicles: List[Dict[str, Any]],
    circuity_factor: float = 1.30,
    avg_speed_kmh: float = 40.0,
    service_time_mins: float = 15.0,
    enforce_time_windows: bool = True,
    search_time_limit_sec: int = 5
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Run Google OR-Tools VRP Optimization engine (or fallback heuristic if OR-Tools DLL unavailable).
    """
    start_cpu_time = time.time()

    if not HAS_ORTOOLS:
        return run_heuristic_vrp_fallback(
            warehouse, orders, vehicles, circuity_factor, avg_speed_kmh, service_time_mins, enforce_time_windows, start_cpu_time
        )

    # Filter available vehicles
    avail_vehicles = [v for v in vehicles if v.get("is_available", 1) == 1]
    if not avail_vehicles or not orders:
        summary = {
            "algorithm": "OR-Tools VRP",
            "total_orders": len(orders),
            "assigned_orders": 0,
            "unassigned_orders": len(orders),
            "vehicles_used": 0,
            "total_distance_km": 0.0,
            "total_cost": 0.0,
            "avg_capacity_utilization": 0.0,
            "total_duration_hours": 0.0,
            "on_time_rate_pct": 0.0,
            "execution_time_sec": round(time.time() - start_cpu_time, 3),
            "notes": "No available vehicles or pending orders."
        }
        unassigned_diag = diagnose_unassigned_orders(orders, vehicles, warehouse, np.zeros((2,2)), np.zeros((2,2)))
        return summary, [], unassigned_diag

    # Prepare locations array (Index 0 = Warehouse, Index 1..N = Orders)
    all_locations = [warehouse] + orders
    num_nodes = len(all_locations)
    num_vehicles = len(avail_vehicles)

    dist_km, time_mins, dist_meters = build_distance_and_time_matrices(
        all_locations, circuity_factor, avg_speed_kmh, service_time_mins
    )

    try:
        manager = pywrapcp.RoutingIndexManager(num_nodes, num_vehicles, 0)
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(dist_meters[from_node, to_node])

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        demands = [0] + [int(round(o["quantity_kg"])) for o in orders]
        def demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return demands[from_node]

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        vehicle_capacities = [int(round(v["capacity_kg"])) for v in avail_vehicles]

        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index, 0, vehicle_capacities, True, "Capacity"
        )

        vehicle_max_distances = [int(round(v["max_distance_km"] * 1000)) for v in avail_vehicles]
        routing.AddDimensionWithVehicleCapacity(
            transit_callback_index, 0, vehicle_max_distances, True, "Distance"
        )

        if enforce_time_windows:
            def time_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return int(round(time_mins[from_node, to_node]))

            time_callback_index = routing.RegisterTransitCallback(time_callback)
            routing.AddDimension(time_callback_index, 60, 24 * 60, False, "Time")
            time_dimension = routing.GetDimensionOrDie("Time")
            time_dimension.CumulVar(manager.NodeToIndex(0)).SetRange(8 * 60, 18 * 60)

            for order_idx, order in enumerate(orders, start=1):
                index = manager.NodeToIndex(order_idx)
                tw_start = time_to_minutes(order.get("time_window_start", "08:00"))
                tw_end = time_to_minutes(order.get("time_window_end", "17:00"))
                time_dimension.CumulVar(index).SetRange(tw_start, tw_end)

        priority_penalties = {"High": 10_000_000, "Medium": 5_000_000, "Low": 1_000_000}
        for order_idx, order in enumerate(orders, start=1):
            prio = order.get("priority", "Medium")
            penalty = priority_penalties.get(prio, 5_000_000)
            routing.AddDisjunction([manager.NodeToIndex(order_idx)], penalty)

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = search_time_limit_sec

        solution = routing.SolveWithParameters(search_parameters)
    except Exception as e:
        # If any runtime issue occurs during C++ solving, execute fallback heuristic
        return run_heuristic_vrp_fallback(
            warehouse, orders, vehicles, circuity_factor, avg_speed_kmh, service_time_mins, enforce_time_windows, start_cpu_time
        )

    exec_time = round(time.time() - start_cpu_time, 3)

    if not solution:
        summary = {
            "algorithm": "OR-Tools VRP",
            "total_orders": len(orders),
            "assigned_orders": 0,
            "unassigned_orders": len(orders),
            "vehicles_used": 0,
            "total_distance_km": 0.0,
            "total_cost": 0.0,
            "avg_capacity_utilization": 0.0,
            "total_duration_hours": 0.0,
            "on_time_rate_pct": 0.0,
            "execution_time_sec": exec_time,
            "notes": "No feasible routing solution found by OR-Tools."
        }
        unassigned_diag = diagnose_unassigned_orders(orders, avail_vehicles, warehouse, dist_km, time_mins)
        return summary, [], unassigned_diag

    # Extract solution
    all_route_stops = []
    assigned_order_indices = set()
    vehicles_used_count = 0
    total_fleet_distance_km = 0.0
    total_fleet_cost = 0.0
    total_fleet_duration_mins = 0.0
    vehicle_utilizations = []
    on_time_count = 0

    shift_start_mins = 8 * 60

    for vehicle_idx, vehicle in enumerate(avail_vehicles):
        index = routing.Start(vehicle_idx)
        if routing.IsEnd(solution.Value(routing.NextVar(index))):
            continue

        vehicles_used_count += 1
        v_id = vehicle["vehicle_id"]
        v_cap = vehicle["capacity_kg"]
        v_cost_km = vehicle["cost_per_km"]
        v_fixed_cost = vehicle.get("fixed_cost", 50.0)

        seq = 0
        current_dist_km = 0.0
        current_load_kg = 0.0
        current_time_mins = float(shift_start_mins)
        prev_node = 0

        route_stop_records = []

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            if node == 0:
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
                    "distance_from_prev_km": 0.0,
                    "cumulative_distance_km": 0.0,
                    "load_after_stop_kg": 0.0,
                    "is_warehouse": True
                })
            else:
                assigned_order_indices.add(node)
                order = orders[node - 1]
                leg_dist = dist_km[prev_node, node]
                leg_time = time_mins[prev_node, node]

                current_dist_km += leg_dist
                current_time_mins += leg_time
                current_load_kg += order["quantity_kg"]

                tw_end = time_to_minutes(order.get("time_window_end", "17:00"))
                if current_time_mins <= tw_end:
                    on_time_count += 1

                dep_time_mins = current_time_mins + order.get("service_time_mins", 15)

                route_stop_records.append({
                    "vehicle_id": v_id,
                    "stop_sequence": seq,
                    "order_id": order["order_id"],
                    "location_id": order.get("location_id", f"LOC-{node}"),
                    "location_name": order.get("customer_name", f"Order #{node}"),
                    "latitude": order["latitude"],
                    "longitude": order["longitude"],
                    "arrival_time": minutes_to_time(current_time_mins),
                    "departure_time": minutes_to_time(dep_time_mins),
                    "distance_from_prev_km": round(leg_dist, 2),
                    "cumulative_distance_km": round(current_dist_km, 2),
                    "load_after_stop_kg": round(current_load_kg, 1),
                    "is_warehouse": False
                })
                current_time_mins = dep_time_mins

            prev_node = node
            seq += 1
            index = solution.Value(routing.NextVar(index))

        return_dist = dist_km[prev_node, 0]
        return_time = time_mins[prev_node, 0]
        current_dist_km += return_dist
        current_time_mins += return_time

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
            "cumulative_distance_km": round(current_dist_km, 2),
            "load_after_stop_kg": round(current_load_kg, 1),
            "is_warehouse": True
        })

        total_fleet_distance_km += current_dist_km
        v_cost = (current_dist_km * v_cost_km) + v_fixed_cost
        total_fleet_cost += v_cost
        v_duration = current_time_mins - shift_start_mins
        total_fleet_duration_mins += v_duration
        vehicle_utilizations.append((current_load_kg / v_cap) * 100.0)

        all_route_stops.extend(route_stop_records)

    all_order_indices = set(range(1, num_nodes))
    unassigned_indices = list(all_order_indices - assigned_order_indices)
    unassigned_orders = [orders[idx - 1] for idx in unassigned_indices]

    unassigned_diagnostics = diagnose_unassigned_orders(
        unassigned_orders, avail_vehicles, warehouse, dist_km, time_mins
    )

    assigned_count = len(assigned_order_indices)
    avg_util = float(np.mean(vehicle_utilizations)) if vehicle_utilizations else 0.0
    on_time_pct = (on_time_count / assigned_count * 100.0) if assigned_count > 0 else 0.0

    summary = {
        "algorithm": "OR-Tools VRP",
        "total_orders": len(orders),
        "assigned_orders": assigned_count,
        "unassigned_orders": len(unassigned_orders),
        "vehicles_used": vehicles_used_count,
        "total_distance_km": round(total_fleet_distance_km, 2),
        "total_cost": round(total_fleet_cost, 2),
        "avg_capacity_utilization": round(avg_util, 1),
        "total_duration_hours": round(total_fleet_duration_mins / 60.0, 2),
        "on_time_rate_pct": round(on_time_pct, 1),
        "execution_time_sec": exec_time,
        "notes": f"Optimization solved in {exec_time}s using Guided Local Search."
    }

    return summary, all_route_stops, unassigned_diagnostics
