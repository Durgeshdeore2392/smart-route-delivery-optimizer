"""
Distance and Travel Time calculation matrix generator.
Calculates geographic distance (Haversine formula) with road circuity factor
and converts to estimated travel times and integer matrices for optimization.
"""

import math
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Any

EARTH_RADIUS_KM = 6371.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees).
    Returns distance in kilometers.
    """
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(d_lat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2.0) ** 2)
    
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_KM * c


def build_distance_and_time_matrices(
    locations: List[Dict[str, Any]],
    circuity_factor: float = 1.30,
    avg_speed_kmh: float = 40.0,
    service_time_mins: float = 15.0
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Build distance matrix (km), travel duration matrix (mins), 
    and integer distance matrix (meters, for OR-Tools solver).

    Parameters:
    - locations: List of dicts with keys 'latitude', 'longitude', etc. First item (index 0) must be Warehouse.
    - circuity_factor: Multiplier to estimate road distance from straight-line (default 1.30).
    - avg_speed_kmh: Average fleet speed in km/h (default 40.0 km/h).
    - service_time_mins: Constant service / drop-off time at each customer stop (default 15 mins).

    Returns:
    - distance_matrix_km: 2D numpy array of distances in km.
    - time_matrix_mins: 2D numpy array of travel + service times in minutes.
    - distance_matrix_meters: 2D numpy int array (meters) for OR-Tools integer routing solver.
    """
    n = len(locations)
    dist_km = np.zeros((n, n), dtype=float)
    time_mins = np.zeros((n, n), dtype=float)

    for i in range(n):
        lat1, lon1 = locations[i]["latitude"], locations[i]["longitude"]
        for j in range(n):
            if i == j:
                dist_km[i, j] = 0.0
                time_mins[i, j] = 0.0
            else:
                straight_dist = haversine_distance(lat1, lon1, locations[j]["latitude"], locations[j]["longitude"])
                road_dist = straight_dist * circuity_factor
                dist_km[i, j] = road_dist

                # Travel time in minutes
                travel_time = (road_dist / avg_speed_kmh) * 60.0
                
                # Service time added if destination j is not warehouse (j > 0)
                st = service_time_mins if j > 0 else 0.0
                time_mins[i, j] = travel_time + st

    dist_meters = np.round(dist_km * 1000.0).astype(int)
    return dist_km, time_mins, dist_meters
