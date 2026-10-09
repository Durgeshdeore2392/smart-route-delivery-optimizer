# Optimization Methodology & Algorithm Documentation

## 1. Overview of the Vehicle Routing Problem (VRP)
The Vehicle Routing Problem (VRP) is a combinatorial optimization problem that seeks to determine the optimal set of routes for a fleet of vehicles delivering goods from a central warehouse to a set of dispersed customer locations.

Variants implemented in this system:
- **Capacitated VRP (CVRP)**: Enforces vehicle weight/payload limits.
- **VRP with Time Windows (VRPTW)**: Enforces arrival time constraints per stop.
- **VRP with Distance & Duration Limits**: Restricts total route mileage and driver shift length.

---

## 2. Baseline Algorithm: Greedy Nearest-Neighbor Heuristic
The baseline model serves as an operational benchmark against which optimization gains are evaluated.

### Algorithm Logic:
1. Sort available fleet vehicles by capacity descending.
2. Initialize route for Vehicle $V$ at Central Warehouse ($Depot = 0$).
3. Iteratively evaluate unassigned orders and pick the nearest customer location $j$ that satisfies:
   $$\text{Current Load} + \text{Demand}_j \le \text{Capacity}_V$$
   $$\text{Current Distance} + d(\text{curr}, j) + d(j, 0) \le \text{Max Distance}_V$$
4. Insert $j$ into route, update location and load, and repeat until no candidate order fits.
5. Close route by returning to depot ($Depot = 0$).

---

## 3. Google OR-Tools VRP Optimization Engine
Google OR-Tools formulates the routing problem as a Constraint Programming (CP) model solved using heuristic local search algorithms.

### Mathematical Formulation:
- **Objective Function**:
  $$\min \sum_{k \in V} \left( \text{FixedCost}_k \cdot y_k + \sum_{i} \sum_{j} \text{CostPerKm}_k \cdot d_{ij} \cdot x_{ijk} \right) + \sum_{i \in \text{Unassigned}} \text{Penalty}_i$$

- **Constraints**:
  - Capacity Dimension: $\sum_{i} q_i \cdot x_{ijk} \le Q_k, \quad \forall k \in V$
  - Distance Dimension: $\sum_{i} \sum_{j} d_{ij} \cdot x_{ijk} \le D_k, \quad \forall k \in V$
  - Time Window Dimension: $T_i + S_i + t_{ij} \le T_j, \quad \forall (i,j) \in E$
  - Priority Disjunctions: High Priority penalty ($10^7$), Medium ($5 \times 10^6$), Low ($10^6$).

### Search Strategy:
- **First Solution Strategy**: `PARALLEL_CHEAPEST_INSERTION`
- **Local Search Metaheuristic**: `GUIDED_LOCAL_SEARCH`
- **Search Time Limit**: Configurable (default: 5 seconds).

---

## 4. Pure-Python Fallback Engine
When native C++ solver execution is restricted by host OS application control policies, the engine seamlessly executes an enhanced Clarke-Wright Savings / Priority-Insertion heuristic, ensuring zero service disruption.
