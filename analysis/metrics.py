"""
analysis.metrics
================
Functions to compute, compare, and rank inventory policy performance.
"""

from __future__ import annotations

from typing import Dict, Optional

import pandas as pd


def compute_metrics(
    df: pd.DataFrame,
    policy_name: str = "Unknown",
    product_name: str = "Unknown",
) -> dict:
    """
    Compute a flat dict of KPIs from a simulation results DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Output of InventoryModel.results_df()
    policy_name : str
    product_name : str

    Returns
    -------
    dict with keys:
        policy, product,
        fill_rate_pct, service_level_pct,
        total_cost, total_holding_cost, total_stockout_cost, total_ordering_cost,
        stockout_days, avg_inventory, num_orders_placed
    """
    total_demand = df["demand"].sum()
    total_sold = df["units_sold"].sum()

    if total_demand > 0:
        fill_rate = 100.0 * total_sold / total_demand
    else:
        fill_rate = 100.0

    non_stockout_days = int((~df["stockout_occurred"]).sum())
    service_level = 100.0 * non_stockout_days / len(df)

    total_holding = float(df["holding_cost"].sum())
    total_stockout = float(df["stockout_cost"].sum())
    total_ordering = float(df["ordering_cost"].sum())
    total_cost = total_holding + total_stockout + total_ordering

    stockout_days = int(df["stockout_occurred"].sum())
    avg_inventory = float(df["stock_level"].mean())
    num_orders = int((df["order_placed"] > 0).sum())

    return {
        "policy": policy_name,
        "product": product_name,
        "fill_rate_pct": round(fill_rate, 4),
        "service_level_pct": round(service_level, 4),
        "total_cost": round(total_cost, 4),
        "total_holding_cost": round(total_holding, 4),
        "total_stockout_cost": round(total_stockout, 4),
        "total_ordering_cost": round(total_ordering, 4),
        "stockout_days": stockout_days,
        "avg_inventory": round(avg_inventory, 4),
        "num_orders_placed": num_orders,
    }


def compare_policies(
    results: Dict[str, pd.DataFrame],
    product_name: str = "Unknown",
) -> pd.DataFrame:
    """
    Compare multiple policies from a dict {policy_name -> results_df}.

    Returns a DataFrame indexed by policy name, one row per policy.
    """
    rows = []
    for policy_name, df in results.items():
        m = compute_metrics(df, policy_name=policy_name, product_name=product_name)
        rows.append(m)

    comparison = pd.DataFrame(rows)
    comparison = comparison.set_index("policy")
    return comparison


def rank_policies(comparison_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add composite ranking to a compare_policies() DataFrame.

    Composite score = mean of (cost_rank, fill_rank) where:
      - cost_rank: 1 = lowest total cost
      - fill_rank: 1 = highest fill rate

    Returns DataFrame sorted ascending by composite_score.
    """
    df = comparison_df.copy()

    df["cost_rank"] = df["total_cost"].rank(ascending=True, method="min")
    df["fill_rank"] = df["fill_rate_pct"].rank(ascending=False, method="min")
    df["composite_score"] = (df["cost_rank"] + df["fill_rank"]) / 2.0

    return df.sort_values("composite_score", ascending=True)
