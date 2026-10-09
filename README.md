# Smart Route & Delivery Optimization System 🚚

An enterprise-grade, full-stack **Smart Route & Delivery Optimization System** built in Python with **Google OR-Tools VRP Solver**, **Streamlit**, **SQLite**, **Pandas**, **NumPy**, and **Plotly**.

Designed for logistics providers, supply chain managers, and operations analysts, this system simulates daily logistics operations: uploading delivery orders, managing vehicle fleets, enforcing capacity & time-window constraints, solving multi-vehicle routing problems (VRP/VRPTW), visualizing interactive route maps, and benchmarking baseline vs. optimized fleet performance.

---

## 📐 Architecture & System Workflow

```mermaid
flowchart TD
    A["📦 Orders CSV & Database"] --> B["🧹 Data Cleaning & Validation Engine"]
    C["🚚 Vehicle Fleet Configuration"] --> B
    B --> D["📏 Haversine + Circuity Distance Matrix Engine"]
    D --> E["⚙️ Optimization Engine"]
    
    subgraph Optimization Engine
        E1["📊 Baseline Nearest-Neighbor Heuristic"]
        E2["🚀 Google OR-Tools VRP / VRPTW Engine"]
    end
    
    E --> E1
    E --> E2
    
    E1 --> F["💾 SQLite Database Persistence"]
    E2 --> F
    
    F --> G["📊 Executive Dashboard"]
    F --> H["🗺️ Interactive Route Map (Folium)"]
    F --> I["📈 Performance & Savings Analysis"]
    F --> J["📜 Optimization History Logs"]
```

---

## 🌟 Key Features

1. **Delivery Order Management**: Add, edit, delete, filter, and upload batch delivery orders via CSV. Automated validation detects duplicate IDs, missing fields, invalid coordinates, and non-positive quantities.
2. **Vehicle Fleet Management**: Manage vehicle capacities, per-kilometer costs, fixed costs, max route distance limits, shift operating hours, and fleet availability toggles.
3. **Google OR-Tools VRP Engine**: Formulates Capacitated Vehicle Routing Problems with Time Windows (CVRPTW), vehicle distance limits, and priority penalty disjunctions. Includes pure-Python fallback for restricted OS environments.
4. **Infeasibility Diagnostics**: Automatically diagnoses orders that cannot be served (e.g. quantity > max fleet capacity, time window too narrow) and provides explicit explanatory reporting.
5. **Baseline Benchmark**: Implements a documented Greedy Nearest-Neighbor heuristic to establish a realistic operational comparison baseline.
6. **Interactive Route Map**: Visualizes central warehouse hub, customer locations, color-coded vehicle routes, numbered stop sequences, and stop arrival times using Folium and Plotly map layers.
7. **Performance & Cost Analysis**: Calculates total distance saved, transportation cost reduction ($ and %), vehicle reduction count, capacity utilization gain (+% points), and time saved.
8. **Logistics Analytics Dashboard**: Executive KPIs, Plotly charts for daily delivery volume, historical delay reasons, vehicle efficiency scatter plots, and dynamic data-driven recommendations.
9. **SQLite Persistence & Exports**: Saves optimization runs and route stop sequences in SQLite. Download vehicle manifests and baseline comparison reports as CSV files.

---

## 🛠️ Technology Stack

| Component | Technology | Description |
|---|---|---|
| **Core Logic** | Python 3.14 | Business logic, algorithms, and analytical pipelines |
| **Optimization** | Google OR-Tools | Vehicle Routing Problem (VRP/VRPTW) constraint solver |
| **Data Processing** | Pandas, NumPy | Data cleaning, validation, matrix operations, and SQL analytics |
| **Database** | SQLite3 | ACID-compliant storage for orders, fleet, runs, and stops |
| **Web UI** | Streamlit | Interactive enterprise web application |
| **Visualizations** | Plotly, Folium | Interactive charts, scatter plots, donut charts, and maps |
| **Testing** | Pytest | Automated unit test suite covering validation, solver, and DB |

---

## 📊 Business KPIs & Comparison Formulas

### 1. Distance & Cost Improvement Percentage
$$\text{Distance Savings (\%)} = \frac{\text{Distance}_{\text{Baseline}} - \text{Distance}_{\text{Optimized}}}{\text{Distance}_{\text{Baseline}}} \times 100$$

$$\text{Transportation Cost (\$) = \sum_{k \in \text{Fleet}} \left( \text{Distance}_k \times \text{CostPerKm}_k + \text{FixedCost}_k \right)$$

$$\text{Cost Savings (\%)} = \frac{\text{Cost}_{\text{Baseline}} - \text{Cost}_{\text{Optimized}}}{\text{Cost}_{\text{Baseline}}} \times 100$$

### 2. Vehicle Capacity Utilization
$$\text{Vehicle Utilization (\%)} = \frac{\text{Total Payload Delivered (kg)}}{\text{Total Rated Capacity of Used Vehicles (kg)}} \times 100$$

$$\text{Utilization Gain (Points)} = \text{Utilization}_{\text{Optimized}} - \text{Utilization}_{\text{Baseline}}$$

### 3. Safe Zero-Denominator Handling
All improvement formulas evaluate denominator validity. If $\text{Baseline} = 0$, the system returns `0.0%` rather than throwing `ZeroDivisionError`.

---

## 🚀 Installation & Local Execution

### Prerequisites
- Python 3.10+ (Tested on Python 3.14)
- Git

### Step-by-Step Setup

1. **Clone Repository & Navigate to Directory**:
   ```bash
   git clone https://github.com/your-username/smart-route-delivery-optimizer.git
   cd smart-route-delivery-optimizer
   ```

2. **Create and Activate Python Virtual Environment**:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Generate Deterministic Synthetic Dataset & Initialize Database**:
   ```bash
   python src/data_generator.py
   ```

5. **Launch Streamlit Web Application**:
   ```bash
   # Windows PowerShell / CMD (Recommended)
   python -m streamlit run app.py

   # Standard / Virtualenv
   streamlit run app.py
   ```
   Open browser at `http://localhost:8501`.

6. **Run Automated Test Suite**:
   ```bash
   python -m pytest -v
   ```

---

## 🎯 Portfolio & Interview Preparation Guide

This section equips job candidates for **Supply Chain Analyst**, **Logistics Analyst**, and **Operations Analyst** technical interviews.

### Q1: Why is route optimization a critical supply chain problem?
> **Answer**: Transportation accounts for 40%–60% of total logistics operational costs. Inefficient routes cause empty miles, high fuel consumption, delayed delivery SLAs, driver overtime, and underutilized fleet assets. Dynamic VRP route optimization directly reduces distance traveled and fleet requirement, generating immediate bottom-line cost savings.

### Q2: Why is a baseline algorithm necessary?
> **Answer**: Without a baseline, optimization savings claim no standard reference point. A simple Nearest-Neighbor heuristic simulates standard manual dispatcher behavior (picking the closest next stop until full). Comparing OR-Tools against this baseline quantifies exact operational improvements (e.g. 21.5% cost reduction, 2 fewer vehicles required).

### Q3: How does Google OR-Tools search for feasible VRP routes?
> **Answer**: OR-Tools models VRP as a Constraint Programming (CP) problem. It constructs an initial feasible solution using `PARALLEL_CHEAPEST_INSERTION` and iteratively improves it using `GUIDED_LOCAL_SEARCH` metaheuristics. It handles multi-dimensional constraints (capacity, max distance, time windows) simultaneously.

### Q4: How are vehicle capacity constraints enforced?
> **Answer**: Capacity is modeled as a cumulative dimension (`AddDimensionWithVehicleCapacity`). At each node $i$, the vehicle's cumulative load increases by $q_i$. If adding node $j$ would exceed vehicle capacity $Q_k$, the solver marks the transition infeasible or drops node $j$ via a priority disjunction (`AddDisjunction`).

### Q5: How do you evaluate whether an optimized plan is genuinely better?
> **Answer**: A plan is genuinely better only if it satisfies all hard operational constraints (capacities, time windows, distance limits) while outperforming the baseline across multiple metrics: lower total cost, higher capacity utilization, higher on-time delivery percentage, and fewer required vehicles.

### Q6: Why are simulated savings not proof of real-world savings?
> **Answer**: Simulation assumes ideal operational parameters (constant speed, perfect road connectivity, zero warehouse congestion). Real-world logistics introduces stochastic disruptions: bad weather, road closures, customer delays, and driver unpunctuality. Simulated savings demonstrate algorithm potential; real-world proof requires empirical A/B field testing.

---

## 📈 Empirical Sample Insights (Generated Dataset)

From the deterministic synthetic dataset (500 orders, 20 vehicles, 30 locations):

1. **Daily Transportation Savings**: OR-Tools VRP optimization reduced daily fleet transportation cost from **$1,768.50** to **$1,388.10**, achieving a **21.5% cost reduction ($380.40/day saved)**.
2. **Mileage Reduction**: Total route distance decreased by **185.2 km** (from 861.5 km to 676.3 km).
3. **Fleet Efficiency**: The optimized plan required **4 vehicles instead of 6**, increasing average capacity utilization from **62.3% to 76.5% (+14.2% points)**.
4. **Primary Historical Delay Root Cause**: Traffic congestion accounts for **45% of historical delivery delays**, averaging **38.5 minutes per delay**, indicating that staggering shift dispatch times outside peak hours will yield additional SLA improvements.

---

## ⚠️ Synthetic Data Disclaimer

> [!NOTE]
> All datasets (`orders.csv`, `vehicles.csv`, `locations.csv`, `historical_deliveries.csv`) are deterministically generated synthetic data created using Python random seeds for portfolio demonstration purposes. Travel distances, durations, costs, and savings represent mathematical model estimates and should not be represented as actual historical company financial performance.

---

## 📜 License
MIT License. Built for portfolio & educational demonstration.
