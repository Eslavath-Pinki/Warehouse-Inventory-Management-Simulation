# Inventory Management Simulation

A discrete-event inventory simulation framework in Python, supporting three reorder policies, five demand patterns, and multi-scenario analysis.

## Project Structure

```
inventory-simulation/
├── simulation/               # Core simulation engine
│   ├── inventory_model.py    # Product, InventoryModel, DailyRecord
│   ├── demand_generator.py   # DemandGenerator (5 patterns)
│   └── reorder_policy.py     # ReorderPointPolicy, MinMaxPolicy, PeriodicReviewPolicy
├── analysis/                 # Metrics and visualisation
│   ├── metrics.py            # compute_metrics, compare_policies, rank_policies
│   └── charts.py             # InventoryCharts
├── tests/                    # pytest test suite
│   ├── test_inventory_model.py
│   ├── test_reorder_policy.py
│   └── test_demand_generator.py
├── data/
│   ├── products.csv          # Product master data
│   └── config.json           # Simulation config and scenarios
├── outputs/                  # Generated charts and reports (git-ignored)
├── simulation_analysis.ipynb # Interactive notebook
├── main.py                   # CLI runner
└── requirements.txt
```

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the full simulation
python main.py

# 3. Filter to specific products or scenarios
python main.py --products P001 P003 --scenario baseline high_demand

# 4. Custom seed and horizon
python main.py --seed 99 --days 180
```

## Reorder Policies

| Policy | Type | Description |
|---|---|---|
| Reorder Point (s, Q) | Continuous | Order fixed quantity Q when stock ≤ s |
| Min-Max (s, S) | Continuous | Order up to S when stock ≤ s |
| Periodic Review (R, S) | Periodic | Every R days, order up to target S |

## Demand Patterns

`normal` · `poisson` · `seasonal` · `sporadic` · `constant`

## Running Tests

```bash
pytest
```

## Outputs

- `outputs/charts/` — PNG charts (inventory levels, policy comparisons, heatmaps)
- `outputs/reports/simulation_summary.csv` — flat metrics table across all products, policies, and scenarios
