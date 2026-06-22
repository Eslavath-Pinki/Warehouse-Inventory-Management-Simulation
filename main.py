"""
Inventory Simulation — Main Runner
===================================
Runs the full multi-product, multi-policy, multi-scenario simulation,
computes metrics, generates all charts, and writes a summary CSV report.

Usage:
    python main.py                        # default: all products, all policies
    python main.py --products P001 P003   # specific products
    python main.py --scenario stress_test # single scenario
    python main.py --seed 99 --days 180   # custom seed and horizon
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

# ── Package imports ────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from simulation import (
    Product, InventoryModel, DemandGenerator,
    ReorderPointPolicy, MinMaxPolicy, PeriodicReviewPolicy,
)
from analysis import compute_metrics, compare_policies, InventoryCharts


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_config(path: str = "data/config.json") -> dict:
    with open(ROOT / path) as f:
        return json.load(f)


def load_products(path: str = "data/products.csv") -> List[Product]:
    df = pd.read_csv(ROOT / path)
    return [Product.from_dict(row) for row in df.to_dict(orient="records")]


def build_policies(product: Product) -> Dict[str, object]:
    """Return all three policies configured for a given product."""
    return {
        "Reorder Point (s,Q)": ReorderPointPolicy(
            reorder_point=product.reorder_point,
            order_quantity=product.order_quantity,
        ),
        "Min-Max (s,S)": MinMaxPolicy(
            min_level=product.reorder_point,
            max_level=product.max_stock,
        ),
        "Periodic Review (R,S)": PeriodicReviewPolicy(
            review_period=product.review_period,
            target_level=product.max_stock,
        ),
    }


def run_product_scenario(
    product: Product,
    scenario_name: str,
    scenario_cfg: dict,
    num_days: int,
    seed: int,
) -> Dict[str, pd.DataFrame]:
    """Run all three policies for one product under one scenario."""
    policies = build_policies(product)
    results = {}
    for policy_name, policy in policies.items():
        demand_gen = DemandGenerator(
            pattern=product.demand_pattern,
            mean=product.mean_demand,
            std=product.std_demand,
            seed=seed,
            demand_multiplier=scenario_cfg.get("demand_multiplier", 1.0),
        )
        model = InventoryModel(
            product=product,
            policy=policy,
            demand_generator=demand_gen,
            num_days=num_days,
            lead_time_multiplier=scenario_cfg.get("lead_time_multiplier", 1.0),
            seed=seed,
        )
        model.run()
        results[policy_name] = model.results_df()
    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def main(
    product_ids: Optional[List[str]] = None,
    scenario_names: Optional[List[str]] = None,
    num_days: Optional[int] = None,
    seed: Optional[int] = None,
    output_dir: str = "outputs",
):
    t0 = time.time()
    cfg = load_config()
    sim_cfg = cfg["simulation"]
    all_scenarios = cfg["scenarios"]

    num_days = num_days or sim_cfg["num_days"]
    seed = seed if seed is not None else sim_cfg["random_seed"]
    scenario_names = scenario_names or list(all_scenarios.keys())

    all_products = load_products()
    if product_ids:
        all_products = [p for p in all_products if p.product_id in product_ids]
    if not all_products:
        print("❌  No products matched the given IDs.")
        return

    charts_dir = ROOT / output_dir / "charts"
    reports_dir = ROOT / output_dir / "reports"
    charts_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    charts = InventoryCharts(output_dir=str(charts_dir))
    all_metrics_rows: List[dict] = []

    print(f"\n{'='*60}")
    print(f"  Inventory Simulation")
    print(f"  Products : {[p.product_id for p in all_products]}")
    print(f"  Scenarios: {scenario_names}")
    print(f"  Days     : {num_days}   Seed: {seed}")
    print(f"{'='*60}\n")

    for product in all_products:
        print(f"▶ Product: {product.product_id} — {product.product_name}")

        scenario_results_for_product: Dict[str, pd.DataFrame] = {}

        for scenario_name in scenario_names:
            scenario_cfg = all_scenarios[scenario_name]
            print(f"  ├─ Scenario: {scenario_name}")

            policy_results = run_product_scenario(
                product, scenario_name, scenario_cfg, num_days, seed
            )

            # Per-policy inventory level charts (baseline only, to keep output manageable)
            if scenario_name == "baseline":
                for policy_name, df in policy_results.items():
                    charts.plot_inventory_levels(
                        df,
                        policy_name=policy_name,
                        product_name=product.product_id,
                        reorder_point=product.reorder_point,
                    )
                    charts.plot_stockout_calendar(
                        df,
                        product_name=f"{product.product_id}_{policy_name.replace(' ', '_')}",
                        num_days=num_days,
                    )

            # Policy comparison chart for this scenario
            comparison_df = compare_policies(policy_results, product_name=product.product_id)
            charts.plot_policy_comparison(
                comparison_df.reset_index(),
                product_name=f"{product.product_id}_{scenario_name}",
            )

            # Collect metrics
            for policy_name, df in policy_results.items():
                m = compute_metrics(df, policy_name=policy_name, product_name=product.product_id)
                m["scenario"] = scenario_name
                all_metrics_rows.append(m)

            # Accumulate best-policy result for scenario comparison chart
            best_policy = comparison_df["total_cost"].idxmin()
            scenario_results_for_product[scenario_name] = policy_results[best_policy]

        # Scenario comparison chart (best policy per scenario)
        if len(scenario_names) > 1:
            all_scenario_metrics = {}
            for sc in scenario_names:
                m_df = pd.DataFrame([
                    compute_metrics(scenario_results_for_product[sc],
                                    policy_name="best", product_name=product.product_id)
                ])
                all_scenario_metrics[sc] = m_df
            charts.plot_scenario_comparison(
                all_scenario_metrics,
                product_name=product.product_id,
            )

    # ── Summary metrics CSV ───────────────────────────────────────────────────
    summary_df = pd.DataFrame(all_metrics_rows)
    summary_path = reports_dir / "simulation_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    print(f"\n📄 Summary CSV saved → {summary_path}")

    # ── Multi-product heatmaps (baseline only) ────────────────────────────────
    baseline_metrics = summary_df[summary_df["scenario"] == "baseline"]
    if not baseline_metrics.empty and len(all_products) > 1:
        for metric in ["total_cost", "fill_rate_pct", "stockout_days"]:
            charts.plot_summary_heatmap(baseline_metrics, metric=metric)

    elapsed = time.time() - t0
    print(f"\n✅  Simulation complete in {elapsed:.1f}s")
    print(f"   Charts  → {charts_dir}")
    print(f"   Reports → {reports_dir}")
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Inventory Management Simulation Runner"
    )
    parser.add_argument(
        "--products", nargs="+", metavar="ID",
        help="Product IDs to simulate (default: all). E.g. --products P001 P003"
    )
    parser.add_argument(
        "--scenario", nargs="+", metavar="NAME", dest="scenarios",
        help="Scenario names from config.json (default: all). E.g. --scenario baseline high_demand"
    )
    parser.add_argument(
        "--days", type=int, default=None,
        help="Number of simulation days (overrides config.json)"
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed (overrides config.json)"
    )
    parser.add_argument(
        "--output", default="outputs",
        help="Output directory for charts and reports (default: outputs/)"
    )
    args = parser.parse_args()

    main(
        product_ids=args.products,
        scenario_names=args.scenarios,
        num_days=args.days,
        seed=args.seed,
        output_dir=args.output,
    )
