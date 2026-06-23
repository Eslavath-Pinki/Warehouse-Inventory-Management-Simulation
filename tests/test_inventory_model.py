"""
Tests for simulation.inventory_model and analysis.metrics
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from simulation.inventory_model import Product, InventoryModel, DailyRecord
from simulation.demand_generator import DemandGenerator
from simulation.reorder_policy import ReorderPointPolicy, MinMaxPolicy, PeriodicReviewPolicy
from analysis.metrics import compute_metrics, compare_policies, rank_policies


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_product(**overrides) -> Product:
    defaults = dict(
        product_id="TEST",
        product_name="Test Product",
        initial_stock=500.0,
        mean_demand=20.0,
        std_demand=5.0,
        lead_time_min=2,
        lead_time_max=4,
        holding_cost=0.5,
        stockout_cost=50.0,
        ordering_cost=100.0,
        reorder_point=200.0,
        order_quantity=300.0,
        max_stock=800.0,
        review_period=7,
        demand_pattern="normal",
    )
    defaults.update(overrides)
    return Product(**defaults)


def run_sim(product=None, policy=None, num_days=100, seed=42) -> pd.DataFrame:
    product = product or make_product()
    policy = policy or ReorderPointPolicy(reorder_point=200, order_quantity=300)
    dg = DemandGenerator(mean=product.mean_demand, std=product.std_demand, seed=seed)
    model = InventoryModel(product=product, policy=policy,
                           demand_generator=dg, num_days=num_days, seed=seed)
    return model.results_df()


# ── Product.from_dict ──────────────────────────────────────────────────────────

class TestProductFromDict:
    def test_basic_construction(self):
        d = {
            "product_id": "P001", "product_name": "Widget",
            "initial_stock": "200", "mean_demand": "10", "std_demand": "2",
            "lead_time_min": "1", "lead_time_max": "3",
            "holding_cost": "0.5", "stockout_cost": "30", "ordering_cost": "50",
            "reorder_point": "80", "order_quantity": "150",
            "max_stock": "400", "review_period": "7",
        }
        p = Product.from_dict(d)
        assert p.product_id == "P001"
        assert p.initial_stock == pytest.approx(200.0)
        assert p.demand_pattern == "normal"   # default

    def test_demand_pattern_passed_through(self):
        d = {
            "product_id": "P002", "product_name": "Chemical",
            "initial_stock": "100", "mean_demand": "5", "std_demand": "1",
            "lead_time_min": "2", "lead_time_max": "5",
            "holding_cost": "1", "stockout_cost": "80", "ordering_cost": "120",
            "reorder_point": "40", "order_quantity": "100",
            "max_stock": "300", "review_period": "14",
            "demand_pattern": "seasonal",
        }
        p = Product.from_dict(d)
        assert p.demand_pattern == "seasonal"


# ── InventoryModel.run ─────────────────────────────────────────────────────────

class TestInventoryModelRun:
    def test_returns_correct_number_of_days(self):
        df = run_sim(num_days=90)
        assert len(df) == 90

    def test_columns_present(self):
        df = run_sim()
        required = {
            "day", "stock_level", "demand", "units_sold", "unmet_demand",
            "order_placed", "order_received", "holding_cost", "stockout_cost",
            "ordering_cost", "total_cost", "stockout_occurred",
        }
        assert required.issubset(set(df.columns))

    def test_stock_never_negative(self):
        df = run_sim()
        assert (df["stock_level"] >= 0).all()

    def test_units_sold_le_demand(self):
        df = run_sim()
        assert (df["units_sold"] <= df["demand"] + 1e-9).all()

    def test_unmet_demand_non_negative(self):
        df = run_sim()
        assert (df["unmet_demand"] >= 0).all()

    def test_total_cost_equals_sum(self):
        df = run_sim()
        computed = df["holding_cost"] + df["stockout_cost"] + df["ordering_cost"]
        pd.testing.assert_series_equal(df["total_cost"], computed, check_names=False)

    def test_stockout_occurred_consistent(self):
        df = run_sim()
        expected = df["unmet_demand"] > 0
        pd.testing.assert_series_equal(
            df["stockout_occurred"], expected, check_names=False
        )

    def test_day_column_sequential(self):
        df = run_sim(num_days=50)
        assert list(df["day"]) == list(range(50))

    def test_holding_cost_formula(self):
        """holding_cost per day = stock_level * product.holding_cost"""
        product = make_product(holding_cost=1.0)
        df = run_sim(product=product)
        expected = df["stock_level"] * 1.0
        pd.testing.assert_series_equal(df["holding_cost"], expected, check_names=False)

    def test_ordering_cost_charged_only_when_order_placed(self):
        product = make_product(ordering_cost=99.0)
        df = run_sim(product=product)
        no_order_rows = df[df["order_placed"] == 0]
        assert (no_order_rows["ordering_cost"] == 0).all()
        order_rows = df[df["order_placed"] > 0]
        assert (order_rows["ordering_cost"] == 99.0).all()

    def test_results_df_consistent_with_run(self):
        product = make_product()
        policy = ReorderPointPolicy(reorder_point=200, order_quantity=300)
        dg = DemandGenerator(mean=20, std=5, seed=0)
        model = InventoryModel(product=product, policy=policy,
                               demand_generator=dg, num_days=50, seed=0)
        records = model.run()
        df = model.results_df()
        assert len(df) == len(records)

    def test_seed_reproducibility(self):
        df1 = run_sim(seed=7)
        df2 = run_sim(seed=7)
        pd.testing.assert_frame_equal(df1, df2)

    def test_different_seeds_differ(self):
        df1 = run_sim(seed=1)
        df2 = run_sim(seed=99)
        assert not df1["demand"].equals(df2["demand"])

    def test_orders_replenish_stock(self):
        """A product with high demand and low initial stock should eventually reorder."""
        product = make_product(initial_stock=50, mean_demand=20, reorder_point=200, order_quantity=400)
        df = run_sim(product=product, num_days=200)
        assert df["order_placed"].sum() > 0

    def test_lead_time_multiplier(self):
        """Longer lead time should generally not crash the simulation."""
        product = make_product()
        dg = DemandGenerator(mean=20, std=5, seed=0)
        policy = ReorderPointPolicy(reorder_point=200, order_quantity=300)
        model = InventoryModel(product=product, policy=policy,
                               demand_generator=dg, num_days=50,
                               lead_time_multiplier=3.0, seed=0)
        df = model.results_df()
        assert len(df) == 50
        assert (df["stock_level"] >= 0).all()


# ── Metrics ───────────────────────────────────────────────────────────────────

class TestComputeMetrics:
    def setup_method(self):
        self.df = run_sim(num_days=365)
        self.m = compute_metrics(self.df, policy_name="TestPolicy", product_name="P_TEST")

    def test_keys_present(self):
        required_keys = {
            "fill_rate_pct", "service_level_pct", "total_cost",
            "total_holding_cost", "total_stockout_cost", "total_ordering_cost",
            "stockout_days", "avg_inventory", "num_orders_placed",
        }
        assert required_keys.issubset(set(self.m.keys()))

    def test_fill_rate_between_0_and_100(self):
        assert 0 <= self.m["fill_rate_pct"] <= 100

    def test_service_level_between_0_and_100(self):
        assert 0 <= self.m["service_level_pct"] <= 100

    def test_total_cost_positive(self):
        assert self.m["total_cost"] >= 0

    def test_total_cost_equals_sum_of_components(self):
        expected = (
            self.m["total_holding_cost"]
            + self.m["total_stockout_cost"]
            + self.m["total_ordering_cost"]
        )
        assert self.m["total_cost"] == pytest.approx(expected, rel=1e-3)

    def test_labels(self):
        assert self.m["policy"] == "TestPolicy"
        assert self.m["product"] == "P_TEST"

    def test_stockout_days_matches_df(self):
        expected = int(self.df["stockout_occurred"].sum())
        assert self.m["stockout_days"] == expected

    def test_zero_demand_edge_case(self):
        """If demand is zero, fill rate should be 100%."""
        df_zero = self.df.copy()
        df_zero["demand"] = 0
        df_zero["units_sold"] = 0
        df_zero["unmet_demand"] = 0
        m = compute_metrics(df_zero)
        assert m["fill_rate_pct"] == pytest.approx(100.0)


class TestComparePolicies:
    def test_returns_dataframe(self):
        results = {
            "PolicyA": run_sim(num_days=100, seed=1),
            "PolicyB": run_sim(num_days=100, seed=2),
        }
        df = compare_policies(results)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

    def test_index_is_policy_name(self):
        results = {"Alpha": run_sim(), "Beta": run_sim(seed=99)}
        df = compare_policies(results, product_name="P001")
        assert "Alpha" in df.index
        assert "Beta" in df.index


class TestRankPolicies:
    def test_adds_composite_score(self):
        results = {
            "A": run_sim(seed=1),
            "B": run_sim(seed=2),
            "C": run_sim(seed=3),
        }
        cdf = compare_policies(results)
        ranked = rank_policies(cdf)
        assert "composite_score" in ranked.columns

    def test_sorted_ascending_by_composite(self):
        results = {
            "A": run_sim(seed=10),
            "B": run_sim(seed=20),
        }
        cdf = compare_policies(results)
        ranked = rank_policies(cdf)
        scores = ranked["composite_score"].tolist()
        assert scores == sorted(scores)
