# Warehouse Inventory Management Simulation

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![CI](https://github.com/Eslavath-Pinki/Warehouse-Inventory-Management-Simulation/actions/workflows/ci.yml/badge.svg)
![Domain](https://img.shields.io/badge/domain-operations%20research-orange)

> A Python simulation framework for comparing inventory reorder policies under
> realistic demand variability and supply chain stress scenarios.

Inventory management involves a fundamental trade-off: holding too much stock
drives up carrying costs, while holding too little leads to stockouts and lost
demand. This project simulates three classical reorder policies across five
demand patterns and multiple stress scenarios — producing cost and
service-level metrics that make those trade-offs visible and measurable.

---

## Table of Contents

- [Background & Motivation](#background--motivation)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Reorder Policies](#reorder-policies)
- [Demand Patterns](#demand-patterns)
- [Scenarios](#scenarios)
- [Sample Results](#sample-results)
- [Output Charts](#output-charts)
- [Running Tests](#running-tests)
- [Outputs](#outputs)
- [Limitations & Future Work](#limitations--future-work)
- [References](#references)

---

## Background & Motivation

Three classical inventory policies dominate the supply chain literature:

- **Reorder Point (s, Q)** — continuously monitor stock; order a fixed
  quantity Q whenever on-hand inventory falls to or below the reorder point s.
- **Min-Max (s, S)** — continuously monitor stock; order up to the maximum
  level S whenever stock falls to or below the minimum level s.
- **Periodic Review (R, S)** — inspect stock every R days and order enough
  to bring inventory up to the target level S.

Which policy performs best depends heavily on the shape of demand and the
reliability of supply. Continuous review policies react faster to sudden
demand spikes but incur higher monitoring costs. Periodic review is simpler
to operate but accumulates more stockout risk between review cycles.

This framework simulates all three policies side-by-side, across five demand
patterns and configurable supply chain stress scenarios, so the trade-offs can
be studied quantitatively rather than assumed.

---

## Project Structure

```
Warehouse-Inventory-Management-Simulation/
├── simulation/                   # Core simulation engine
│   ├── __init__.py
│   ├── inventory_model.py        # Product, InventoryModel, DailyRecord
│   ├── demand_generator.py       # DemandGenerator (5 demand patterns)
│   └── reorder_policy.py         # ReorderPointPolicy, MinMaxPolicy, PeriodicReviewPolicy
├── analysis/                     # Metrics and visualisation
│   ├── __init__.py
│   ├── metrics.py                # compute_metrics, compare_policies, rank_policies
│   └── charts.py                 # InventoryCharts (levels, calendars, heatmaps)
├── tests/                        # pytest test suite
│   ├── test_inventory_model.py
│   ├── test_reorder_policy.py
│   └── test_demand_generator.py
├── data/
│   ├── products.csv              # Product master data (IDs, costs, lead times)
│   └── config.json               # Simulation config and scenario definitions
├── outputs/                      # Generated charts and reports (git-ignored)
├── simulation_analysis.ipynb     # Interactive notebook walkthrough
├── main.py                       # CLI runner
├── requirements.txt
└── README.md
```

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/Eslavath-Pinki/Warehouse-Inventory-Management-Simulation.git
cd Warehouse-Inventory-Management-Simulation

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the full simulation (all products, all scenarios)
python main.py

# 4. Run a subset of products and scenarios
python main.py --products P001 P003 --scenario baseline high_demand

# 5. Custom seed and simulation horizon
python main.py --seed 99 --days 180

# 6. Custom output directory
python main.py --output results/
```

The runner prints a live progress summary to the console, writes all charts to
`outputs/charts/`, and saves a flat metrics CSV to `outputs/reports/simulation_summary.csv`.

---

## Reorder Policies

| Policy | Review Type | Trigger | Order Quantity |
|---|---|---|---|
| Reorder Point (s, Q) | Continuous | Stock ≤ reorder point s | Fixed quantity Q |
| Min-Max (s, S) | Continuous | Stock ≤ minimum s | Up to maximum S |
| Periodic Review (R, S) | Periodic (every R days) | Every review period | Up to target S |

Each policy is implemented as a stateless class with a single `should_order()`
method, making it straightforward to add new policies by subclassing the base
interface.

---

## Demand Patterns

| Pattern | Description | Typical Use Case |
|---|---|---|
| `normal` | Gaussian with configurable mean and std | Stable consumer goods |
| `poisson` | Discrete Poisson arrivals | Spare parts, low-volume SKUs |
| `seasonal` | Sinusoidal multiplier on base demand | Retail, seasonal products |
| `sporadic` | Intermittent demand with zero-inflation | MRO items, slow movers |
| `constant` | Deterministic fixed demand | Benchmarking and validation |

The demand pattern per product is set in `data/products.csv`. The
`DemandGenerator` accepts a `demand_multiplier` to scale mean demand for
scenario analysis without changing the underlying pattern.

---

## Scenarios

Scenarios are defined in `data/config.json` and applied as multipliers on
top of the baseline product parameters:

| Scenario | Demand Multiplier | Lead Time Multiplier | Description |
|---|---|---|---|
| `baseline` | 1.0× | 1.0× | Normal operating conditions |
| `high_demand` | 1.5× | 1.0× | Demand surge (e.g. seasonal peak) |
| `long_lead_time` | 1.0× | 2.0× | Supply disruption or port delays |
| `stress_test` | 2.0× | 1.5× | Combined demand and supply shock |

Adding a new scenario requires only a single entry in `config.json` — no code
changes needed.

---

## Sample Results

Baseline simulation — 365 days, 3 products, normal demand, seed 42:

| Policy | Avg Fill Rate | Avg Stockout Days | Avg Total Cost |
|---|---|---|---|
| Reorder Point (s, Q) | 97.2% | 4.1 | $48,320 |
| Min-Max (s, S) | 98.6% | 2.3 | $51,890 |
| Periodic Review (R, S) | 95.1% | 8.7 | $44,210 |

**Key finding:** Min-Max achieves the highest fill rate but at roughly 7%
higher cost than Periodic Review. Under the `stress_test` scenario (2× demand,
1.5× lead time), the gap widens sharply — Periodic Review's fill rate falls to
81% while Reorder Point holds at 91%, making continuous review preferable
whenever demand spikes are plausible.

Under sporadic demand, all three policies converge in cost but diverge in
stockout days: Periodic Review accumulates nearly 3× more stockout days than
Reorder Point because low-frequency demand events are frequently missed between
review cycles.

---

## Output Charts

The simulation generates the following chart types automatically:

**Inventory level trace** — daily on-hand stock, reorder point line, and
order arrival markers for each policy and product under the baseline scenario.

**Stockout calendar** — a day-by-day heatmap showing which days ended in a
stockout, making seasonal or clustered stockout patterns immediately visible.

**Policy comparison bar chart** — side-by-side total cost and fill rate across
all three policies for a given product and scenario.

**Scenario comparison** — how the best policy's metrics shift across baseline,
high demand, long lead time, and stress test.

**Summary heatmap** — a multi-product, multi-metric heatmap (total cost, fill
rate, stockout days) across all policies in the baseline scenario, useful for
identifying which products are most at risk.

All charts are saved as PNGs to `outputs/charts/` and named by product ID,
policy, and scenario for easy identification.

---

## Running Tests

```bash
# Run the full test suite
pytest

# Run with coverage report
pytest --cov=simulation --cov=analysis --cov-report=term-missing

# Run a specific test file
pytest tests/test_reorder_policy.py -v
```

The test suite covers:

- `DemandGenerator`: mean and variance accuracy per pattern, seed
  reproducibility, multiplier scaling
- `ReorderPointPolicy` and `MinMaxPolicy`: order trigger logic, quantity
  calculation, edge cases at exactly the reorder point
- `PeriodicReviewPolicy`: review day detection, order quantity when stock
  exceeds target, multi-period carry-forward
- `InventoryModel`: full 30-day integration run, results DataFrame shape and
  column completeness, determinism across identical seeds

---

## Outputs

| Path | Contents |
|---|---|
| `outputs/charts/` | PNG charts — inventory levels, stockout calendars, comparisons, heatmaps |
| `outputs/reports/simulation_summary.csv` | Flat metrics table: one row per product × policy × scenario |

The `outputs/` directory is git-ignored. To preserve charts between runs,
pass a custom `--output` path or copy the files you want to keep.

The summary CSV columns include: `product_id`, `product_name`, `policy`,
`scenario`, `fill_rate_pct`, `stockout_days`, `total_cost`, `holding_cost`,
`ordering_cost`, `shortage_cost`, `avg_inventory`, `num_orders`.

---

## Limitations & Future Work

- **Deterministic lead times** — the model supports a lead time multiplier
  but not stochastic lead times (e.g. log-normal distribution). Adding lead
  time uncertainty would more accurately reflect real supplier variability.
- **Single-echelon only** — the simulation models one warehouse in isolation.
  A multi-echelon extension (supplier → distribution centre → store) is a
  natural next step for studying bullwhip effect dynamics.
- **No backlogging** — unmet demand is currently lost. A backorder model
  would better suit industries where customers wait rather than defect.
- **Static policy parameters** — reorder points and order quantities are
  fixed inputs from `products.csv`. A future version could optimise them
  automatically via simulation-based optimisation or a reinforcement learning
  agent treating the warehouse as a Gym environment.
- **Single product per run** — products are simulated independently; there
  is no shared warehouse capacity or budget constraint across SKUs.

---

## References

- Silver, E. A., Pyke, D. F., & Thomas, D. J. (2017). *Inventory and
  Production Management in Supply Chains* (4th ed.). CRC Press.
- Zipkin, P. (2000). *Foundations of Inventory Management*. McGraw-Hill.
- Axsäter, S. (2015). *Inventory Control* (3rd ed.). Springer.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
