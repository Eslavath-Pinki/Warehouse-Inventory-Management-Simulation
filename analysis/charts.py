"""
analysis.charts
===============
All chart-generation logic for the inventory simulation.

Class
-----
InventoryCharts — wraps matplotlib to produce and save figures.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

PALETTE = {
    "blue":   "#2563EB",
    "green":  "#10B981",
    "orange": "#F59E0B",
    "red":    "#EF4444",
    "purple": "#8B5CF6",
    "gray":   "#6B7280",
}

POLICY_COLORS = [
    PALETTE["blue"],
    PALETTE["green"],
    PALETTE["orange"],
    PALETTE["purple"],
    PALETTE["red"],
]


class InventoryCharts:
    """
    Generates and saves inventory simulation charts.

    Parameters
    ----------
    output_dir : str | Path
        Directory where PNG files are written.
    dpi : int
        Resolution of saved figures.
    """

    def __init__(self, output_dir: str = "outputs/charts", dpi: int = 150):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dpi = dpi

    # ── Inventory level time series ───────────────────────────────────────────

    def plot_inventory_levels(
        self,
        df: pd.DataFrame,
        policy_name: str = "Policy",
        product_name: str = "Product",
        reorder_point: Optional[float] = None,
    ) -> Path:
        """Line chart of daily stock level with optional reorder-point line."""
        fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=True,
                                 gridspec_kw={"height_ratios": [3, 1]})

        ax_stock, ax_demand = axes

        # Stock level
        ax_stock.plot(df["day"], df["stock_level"], color=PALETTE["blue"],
                      lw=1.0, label="Stock Level")
        ax_stock.fill_between(df["day"], df["stock_level"], alpha=0.15,
                              color=PALETTE["blue"])
        if reorder_point is not None:
            ax_stock.axhline(reorder_point, color=PALETTE["orange"], ls="--",
                             lw=1.2, label=f"Reorder Point ({reorder_point})")

        # Stockout markers
        stockout_days = df[df["stockout_occurred"]]["day"]
        if not stockout_days.empty:
            ax_stock.scatter(stockout_days,
                             [0] * len(stockout_days),
                             color=PALETTE["red"], s=12, zorder=5,
                             label="Stockout")

        # Order received markers
        order_days = df[df["order_received"] > 0]
        if not order_days.empty:
            ax_stock.scatter(order_days["day"], order_days["stock_level"],
                             marker="^", color=PALETTE["green"], s=25,
                             zorder=5, label="Order Received")

        ax_stock.set_ylabel("Stock Level (units)")
        ax_stock.set_title(f"{product_name} — {policy_name} | Inventory Levels",
                           fontweight="bold")
        ax_stock.legend(fontsize=8, loc="upper right")
        ax_stock.grid(axis="y", alpha=0.3)

        # Demand bar chart
        ax_demand.bar(df["day"], df["demand"], color=PALETTE["gray"],
                      alpha=0.6, width=1.0, label="Demand")
        ax_demand.bar(df["day"], df["unmet_demand"], color=PALETTE["red"],
                      alpha=0.7, width=1.0, label="Unmet Demand")
        ax_demand.set_xlabel("Day")
        ax_demand.set_ylabel("Units")
        ax_demand.legend(fontsize=8)
        ax_demand.grid(axis="y", alpha=0.3)

        plt.tight_layout()
        fname = self._slug(f"{product_name}_{policy_name}_inventory_levels") + ".png"
        path = self.output_dir / fname
        fig.savefig(path, dpi=self.dpi, bbox_inches="tight")
        plt.close(fig)
        return path

    # ── Policy comparison bar chart ───────────────────────────────────────────

    def plot_policy_comparison(
        self,
        comparison_df: pd.DataFrame,
        product_name: str = "Product",
    ) -> Path:
        """
        Grouped bar chart comparing total cost components and fill rate
        across policies.

        Parameters
        ----------
        comparison_df : pd.DataFrame
            Must have columns: policy (or index), total_holding_cost,
            total_stockout_cost, total_ordering_cost, fill_rate_pct.
        """
        df = comparison_df.copy()
        if "policy" not in df.columns:
            df = df.reset_index().rename(columns={"index": "policy"})

        policies = df["policy"].tolist()
        x = np.arange(len(policies))
        width = 0.55

        fig, (ax_cost, ax_fill) = plt.subplots(1, 2, figsize=(14, 5))

        # Stacked cost bars
        bars_h = ax_cost.bar(x, df["total_holding_cost"], width,
                             label="Holding", color=PALETTE["blue"])
        bars_s = ax_cost.bar(x, df["total_stockout_cost"], width,
                             bottom=df["total_holding_cost"],
                             label="Stockout", color=PALETTE["red"])
        bars_o = ax_cost.bar(x, df["total_ordering_cost"], width,
                             bottom=df["total_holding_cost"] + df["total_stockout_cost"],
                             label="Ordering", color=PALETTE["orange"])

        ax_cost.set_xticks(x)
        ax_cost.set_xticklabels(policies, rotation=15, ha="right", fontsize=9)
        ax_cost.set_ylabel("Total Cost ($)")
        ax_cost.set_title(f"{product_name} — Total Cost by Policy", fontweight="bold")
        ax_cost.legend()
        ax_cost.grid(axis="y", alpha=0.3)

        # Fill rate bars
        colors = POLICY_COLORS[: len(policies)]
        ax_fill.bar(x, df["fill_rate_pct"], width, color=colors, alpha=0.85)
        ax_fill.axhline(100, color="gray", ls="--", lw=0.8)
        ax_fill.set_ylim(0, 105)
        ax_fill.set_xticks(x)
        ax_fill.set_xticklabels(policies, rotation=15, ha="right", fontsize=9)
        ax_fill.set_ylabel("Fill Rate (%)")
        ax_fill.set_title(f"{product_name} — Fill Rate by Policy", fontweight="bold")
        ax_fill.grid(axis="y", alpha=0.3)

        plt.tight_layout()
        fname = self._slug(f"{product_name}_policy_comparison") + ".png"
        path = self.output_dir / fname
        fig.savefig(path, dpi=self.dpi, bbox_inches="tight")
        plt.close(fig)
        return path

    # ── Scenario comparison ───────────────────────────────────────────────────

    def plot_scenario_comparison(
        self,
        scenario_metrics: Dict[str, pd.DataFrame],
        product_name: str = "Product",
    ) -> Path:
        """
        Bar chart of total_cost and fill_rate across scenarios.

        Parameters
        ----------
        scenario_metrics : dict {scenario_name -> single-row DataFrame of metrics}
        """
        names = list(scenario_metrics.keys())
        costs = [float(df["total_cost"].iloc[0]) for df in scenario_metrics.values()]
        fills = [float(df["fill_rate_pct"].iloc[0]) for df in scenario_metrics.values()]

        x = np.arange(len(names))
        width = 0.55

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        ax1.bar(x, costs, width, color=PALETTE["blue"], alpha=0.85)
        ax1.set_xticks(x)
        ax1.set_xticklabels(names, rotation=20, ha="right", fontsize=9)
        ax1.set_ylabel("Total Cost ($)")
        ax1.set_title(f"{product_name} — Cost by Scenario", fontweight="bold")
        ax1.grid(axis="y", alpha=0.3)

        ax2.bar(x, fills, width, color=PALETTE["green"], alpha=0.85)
        ax2.axhline(100, color="gray", ls="--", lw=0.8)
        ax2.set_ylim(0, 105)
        ax2.set_xticks(x)
        ax2.set_xticklabels(names, rotation=20, ha="right", fontsize=9)
        ax2.set_ylabel("Fill Rate (%)")
        ax2.set_title(f"{product_name} — Fill Rate by Scenario", fontweight="bold")
        ax2.grid(axis="y", alpha=0.3)

        plt.tight_layout()
        fname = self._slug(f"{product_name}_scenario_comparison") + ".png"
        path = self.output_dir / fname
        fig.savefig(path, dpi=self.dpi, bbox_inches="tight")
        plt.close(fig)
        return path

    # ── Stockout calendar heatmap ─────────────────────────────────────────────

    def plot_stockout_calendar(
        self,
        df: pd.DataFrame,
        product_name: str = "Product",
        num_days: int = 365,
    ) -> Path:
        """
        Weekly heatmap of stockout occurrences (day × week grid).
        """
        stockout = df["stockout_occurred"].astype(int).values
        # Pad to full weeks
        weeks = int(np.ceil(num_days / 7))
        padded = np.zeros(weeks * 7, dtype=int)
        padded[: len(stockout)] = stockout
        grid = padded.reshape(weeks, 7)

        fig, ax = plt.subplots(figsize=(max(8, weeks * 0.25), 4))
        im = ax.imshow(grid.T, aspect="auto", cmap="Reds", vmin=0, vmax=1,
                       interpolation="nearest")

        ax.set_xlabel("Week")
        ax.set_ylabel("Day of Week")
        ax.set_yticks(range(7))
        ax.set_yticklabels(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
        ax.set_title(f"{product_name} — Stockout Calendar", fontweight="bold")

        red_patch = mpatches.Patch(color="#EF4444", label="Stockout day")
        white_patch = mpatches.Patch(color="white", ec="gray", label="No stockout")
        ax.legend(handles=[red_patch, white_patch], loc="upper right", fontsize=8)

        plt.tight_layout()
        fname = self._slug(f"{product_name}_stockout_calendar") + ".png"
        path = self.output_dir / fname
        fig.savefig(path, dpi=self.dpi, bbox_inches="tight")
        plt.close(fig)
        return path

    # ── Summary heatmap ───────────────────────────────────────────────────────

    def plot_summary_heatmap(
        self,
        metrics_df: pd.DataFrame,
        metric: str = "total_cost",
    ) -> Path:
        """
        Product × Policy heatmap for a chosen metric.

        Parameters
        ----------
        metrics_df : pd.DataFrame
            Must have columns 'product', 'policy', and `metric`.
        metric : str
        """
        pivot = metrics_df.pivot_table(
            index="product", columns="policy", values=metric, aggfunc="mean"
        )

        fig, ax = plt.subplots(figsize=(max(6, len(pivot.columns) * 2),
                                        max(4, len(pivot) * 0.7)))

        cmap = "RdYlGn_r" if metric not in {"fill_rate_pct", "service_level_pct"} else "RdYlGn"
        im = ax.imshow(pivot.values, aspect="auto", cmap=cmap)

        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels(pivot.columns, rotation=25, ha="right", fontsize=9)
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels(pivot.index, fontsize=9)
        ax.set_title(f"Summary Heatmap — {metric}", fontweight="bold")
        plt.colorbar(im, ax=ax, fraction=0.04)

        # Annotate cells
        for i in range(len(pivot.index)):
            for j in range(len(pivot.columns)):
                val = pivot.values[i, j]
                if not np.isnan(val):
                    ax.text(j, i, f"{val:,.1f}", ha="center", va="center",
                            fontsize=8, color="black")

        plt.tight_layout()
        fname = self._slug(f"heatmap_{metric}") + ".png"
        path = self.output_dir / fname
        fig.savefig(path, dpi=self.dpi, bbox_inches="tight")
        plt.close(fig)
        return path

    # ── Utility ───────────────────────────────────────────────────────────────

    @staticmethod
    def _slug(text: str) -> str:
        """Convert text to a safe filename slug."""
        return (
            text.lower()
            .replace(" ", "_")
            .replace("(", "")
            .replace(")", "")
            .replace(",", "")
            .replace("/", "_")
            .replace("\\", "_")
        )
