"""
analysis package
================
Metrics, comparisons, and chart generation for inventory simulation results.
"""

from analysis.metrics import compute_metrics, compare_policies, rank_policies
from analysis.charts import InventoryCharts

__all__ = [
    "compute_metrics",
    "compare_policies",
    "rank_policies",
    "InventoryCharts",
]
