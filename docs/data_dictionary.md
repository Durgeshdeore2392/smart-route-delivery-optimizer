# Data Dictionary & Schema Documentation

## 1. `locations` Table (`data/locations.csv`)
| Column | Data Type | Description |
|---|---|---|
| `location_id` | TEXT (PK) | Unique location identifier (e.g. `LOC-000`, `LOC-001`) |
| `location_name` | TEXT | Human-readable location or neighborhood name |
| `location_type` | TEXT | Location classification (`warehouse` or `customer`) |
| `latitude` | REAL | Geographic latitude in decimal degrees |
| `longitude` | REAL | Geographic longitude in decimal degrees |
| `address` | TEXT | Street address |
| `city` | TEXT | Metropolitan area city |

## 2. `vehicles` Table (`data/vehicles.csv`)
| Column | Data Type | Description |
|---|---|---|
| `vehicle_id` | TEXT (PK) | Unique vehicle identifier (e.g. `VEH-001`) |
| `vehicle_name` | TEXT | Vehicle name or label |
| `vehicle_type` | TEXT | Vehicle classification (`Van`, `Electric Van`, `Light Truck`, `Heavy Truck`) |
| `capacity_kg` | REAL | Maximum rated payload capacity in kilograms |
| `cost_per_km` | REAL | Variable operating cost per kilometer ($/km) |
| `fixed_cost` | REAL | Fixed dispatch cost per route ($) |
| `max_distance_km` | REAL | Maximum route distance limit per shift (km) |
| `max_working_hours` | REAL | Maximum driver working shift length (hours) |
| `shift_start` | TEXT | Driver shift start time (`HH:MM`) |
| `shift_end` | TEXT | Driver shift end time (`HH:MM`) |
| `is_available` | INTEGER | Active availability flag (`1` = Available, `0` = Unavailable) |

## 3. `orders` Table (`data/orders.csv`)
| Column | Data Type | Description |
|---|---|---|
| `order_id` | TEXT (PK) | Unique delivery order identifier (e.g. `ORD-0001`) |
| `customer_name` | TEXT | Customer or commercial recipient name |
| `location_id` | TEXT (FK) | Reference to `locations.location_id` |
| `latitude` | REAL | Customer delivery latitude |
| `longitude` | REAL | Customer delivery longitude |
| `quantity_kg` | REAL | Delivery order payload weight in kilograms |
| `priority` | TEXT | Business delivery priority (`High`, `Medium`, `Low`) |
| `time_window_start` | TEXT | Earliest delivery window start (`HH:MM`) |
| `time_window_end` | TEXT | Latest delivery window deadline (`HH:MM`) |
| `order_date` | TEXT | Order date (`YYYY-MM-DD`) |
| `status` | TEXT | Order status (`Pending`, `Assigned`, `Delivered`, `Delayed`, `Infeasible`) |
| `service_time_mins` | INTEGER | Customer unloading / drop-off service duration (minutes) |

## 4. `historical_deliveries` Table (`data/historical_deliveries.csv`)
| Column | Data Type | Description |
|---|---|---|
| `record_id` | INTEGER (PK) | Historical record sequence ID |
| `order_id` | TEXT | Reference order ID |
| `vehicle_id` | TEXT | Assigned vehicle ID |
| `planned_arrival` | TEXT | Planned delivery arrival time (`HH:MM`) |
| `actual_arrival` | TEXT | Actual recorded arrival time (`HH:MM`) |
| `delivery_status` | TEXT | Operational delivery status (`On-Time`, `Delayed`, `Failed`) |
| `delay_minutes` | INTEGER | Delay duration in minutes (0 if on-time) |
| `delay_reason` | TEXT | Root cause category for delay (`Traffic Congestion`, `Customer Unavailable`, etc.) |
| `delivery_date` | TEXT | Historical delivery date |
| `actual_cost` | REAL | Actual recorded delivery cost ($) |
| `distance_km` | REAL | Actual route mileage (km) |

## 5. `optimization_runs` Table
Stores header metrics for baseline and OR-Tools VRP optimization executions.

## 6. `route_stops` Table
Stores detailed ordered stop sequences for assigned vehicles per optimization run.
