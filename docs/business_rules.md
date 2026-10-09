# Business Rules and Validation Specifications

## 1. Capacity Constraints
- Every vehicle in the fleet has a strict maximum payload capacity in kilograms (`capacity_kg`).
- The sum of delivery order quantities (`quantity_kg`) assigned to a single vehicle on a single route must never exceed its rated capacity limit.
- **Rule Enforcement**: Hard constraint checked in both Baseline and OR-Tools VRP models. Orders exceeding max single vehicle capacity are flagged as unassigned with diagnostic reasons.

## 2. Vehicle Availability & Fleet Constraints
- Only vehicles marked `is_available = 1` are eligible for routing.
- Deactivated or unavailable vehicles (`is_available = 0`) are excluded from route assignment.
- Fixed vehicle dispatch cost (`fixed_cost`) and per-kilometer operating cost (`cost_per_km`) are included in transportation cost calculations.

## 3. Maximum Route Distance & Working Hours
- Each vehicle has a configured maximum distance limit (`max_distance_km`, e.g. 180–450 km) based on fuel tank capacity or battery range.
- Shift operating hours (default 08:00 AM to 18:00 PM) and driver working hours (`max_working_hours`, e.g. 9 hours) bound total route duration including service drop-off time.

## 4. Delivery Time Windows & Service Times
- Orders specify delivery time windows (e.g. `08:00 - 12:00`, `12:00 - 16:00`, `08:00 - 17:00`).
- A constant service / drop-off time (default: 15 minutes) is added at every customer stop.
- On-time delivery performance evaluates estimated arrival times against `time_window_end`.

## 5. Infeasibility Handling
- The optimizer gracefully handles infeasible orders (e.g. order quantity > max fleet capacity, time window too narrow, route distance exceeded) using priority penalty disjunctions (`AddDisjunction`).
- Unassigned orders are never silently dropped; they are explicitly logged with detailed diagnostic reasons.

## 6. Distance & Travel-Time Model
- Distances are calculated using the Haversine formula modified by a configurable road circuity factor multiplier (default: 1.30) to approximate urban road network routing.
- Travel duration is computed assuming a configurable average fleet speed (default: 40 km/h) plus service time per stop.
