"""
Data validation module for orders, vehicles, and location datasets.
Checks missing fields, invalid coordinates, non-positive quantities,
duplicate IDs, and time window consistency.
"""

import re
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional


def validate_time_window(start_str: str, end_str: str) -> bool:
    """Validate that start and end time windows are valid HH:MM strings and end > start."""
    time_regex = r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$"
    if not isinstance(start_str, str) or not isinstance(end_str, str):
        return False
    if not re.match(time_regex, start_str) or not re.match(time_regex, end_str):
        return False
    
    start_h, start_m = map(int, start_str.split(":"))
    end_h, end_m = map(int, end_str.split(":"))
    
    start_mins = start_h * 60 + start_m
    end_mins = end_h * 60 + end_m
    
    return end_mins > start_mins


def validate_orders_df(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Validate delivery orders DataFrame.
    Returns: (cleaned_df, validation_report)
    """
    errors = []
    warnings = []
    
    required_cols = [
        "order_id", "customer_name", "location_id", "latitude", "longitude",
        "quantity_kg", "priority", "time_window_start", "time_window_end"
    ]
    
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        return df, {
            "is_valid": False,
            "errors": [f"Missing required columns: {', '.join(missing_cols)}"],
            "warnings": [],
            "valid_count": 0,
            "invalid_count": len(df)
        }

    valid_mask = pd.Series(True, index=df.index)

    # 1. Missing required values
    for col in required_cols:
        null_mask = df[col].isnull()
        if null_mask.any():
            invalid_ids = df.loc[null_mask, "order_id"].tolist()
            errors.append(f"Null values in column '{col}' for orders: {invalid_ids[:5]}...")
            valid_mask &= ~null_mask

    # 2. Check coordinates range
    coord_mask = (df["latitude"].between(-90, 90)) & (df["longitude"].between(-180, 180))
    if not coord_mask.all():
        invalid_ids = df.loc[~coord_mask, "order_id"].tolist()
        errors.append(f"Invalid latitude/longitude for orders: {invalid_ids[:5]}...")
        valid_mask &= coord_mask

    # 3. Non-positive quantities
    qty_mask = df["quantity_kg"] > 0
    if not qty_mask.all():
        invalid_ids = df.loc[~qty_mask, "order_id"].tolist()
        errors.append(f"Non-positive order quantity_kg for orders: {invalid_ids[:5]}...")
        valid_mask &= qty_mask

    # 4. Duplicate Order IDs
    dup_ids = df[df.duplicated(subset=["order_id"], keep=False)]["order_id"].unique().tolist()
    if dup_ids:
        errors.append(f"Duplicate order_id(s) detected: {dup_ids[:5]}...")
        # Keep first instance
        dup_mask = ~df.duplicated(subset=["order_id"], keep="first")
        valid_mask &= dup_mask

    # 5. Time window logic check
    tw_valid = df.apply(
        lambda r: validate_time_window(str(r.get("time_window_start", "")), str(r.get("time_window_end", ""))),
        axis=1
    )
    if not tw_valid.all():
        invalid_ids = df.loc[~tw_valid, "order_id"].tolist()
        warnings.append(f"Invalid or inverted time window for orders: {invalid_ids[:5]}... (Defaulting to 08:00-17:00)")

    cleaned_df = df[valid_mask].copy()

    report = {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "valid_count": int(valid_mask.sum()),
        "invalid_count": int((~valid_mask).sum()),
        "total_count": len(df)
    }

    return cleaned_df, report


def validate_vehicles_df(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Validate vehicle fleet DataFrame."""
    errors = []
    warnings = []

    required_cols = ["vehicle_id", "vehicle_type", "capacity_kg", "cost_per_km", "max_distance_km"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        return df, {
            "is_valid": False,
            "errors": [f"Missing required vehicle columns: {', '.join(missing_cols)}"],
            "warnings": [],
            "valid_count": 0,
            "invalid_count": len(df)
        }

    valid_mask = pd.Series(True, index=df.index)

    # 1. Capacity > 0
    cap_mask = df["capacity_kg"] > 0
    if not cap_mask.all():
        invalid_ids = df.loc[~cap_mask, "vehicle_id"].tolist()
        errors.append(f"Vehicle capacity must be positive: {invalid_ids}")
        valid_mask &= cap_mask

    # 2. Cost per km >= 0
    cost_mask = df["cost_per_km"] >= 0
    if not cost_mask.all():
        invalid_ids = df.loc[~cost_mask, "vehicle_id"].tolist()
        errors.append(f"Vehicle cost_per_km must be non-negative: {invalid_ids}")
        valid_mask &= cost_mask

    # 3. Duplicates
    dup_ids = df[df.duplicated(subset=["vehicle_id"], keep=False)]["vehicle_id"].unique().tolist()
    if dup_ids:
        errors.append(f"Duplicate vehicle_id(s): {dup_ids}")
        dup_mask = ~df.duplicated(subset=["vehicle_id"], keep="first")
        valid_mask &= dup_mask

    cleaned_df = df[valid_mask].copy()

    report = {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "valid_count": int(valid_mask.sum()),
        "invalid_count": int((~valid_mask).sum()),
        "total_count": len(df)
    }

    return cleaned_df, report
