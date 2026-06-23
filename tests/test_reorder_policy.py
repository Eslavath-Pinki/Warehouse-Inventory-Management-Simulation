"""
Tests for simulation.reorder_policy
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from simulation.reorder_policy import (
    ReorderPointPolicy,
    MinMaxPolicy,
    PeriodicReviewPolicy,
    OrderDecision,
)


# ── ReorderPointPolicy ─────────────────────────────────────────────────────────

class TestReorderPointPolicy:
    def setup_method(self):
        self.policy = ReorderPointPolicy(reorder_point=100, order_quantity=200)

    def test_name(self):
        assert "s, Q" in self.policy.name or "Reorder" in self.policy.name

    def test_orders_when_at_reorder_point(self):
        decision = self.policy.decide(current_stock=100, pending_orders=0, day=0)
        assert decision.should_order is True
        assert decision.quantity == 200

    def test_orders_when_below_reorder_point(self):
        decision = self.policy.decide(current_stock=50, pending_orders=0, day=0)
        assert decision.should_order is True

    def test_no_order_above_reorder_point(self):
        decision = self.policy.decide(current_stock=150, pending_orders=0, day=0)
        assert decision.should_order is False
        assert decision.quantity == 0

    def test_considers_pending_orders(self):
        # Stock 50 + pending 100 = 150 > reorder point 100 → no order
        decision = self.policy.decide(current_stock=50, pending_orders=100, day=0)
        assert decision.should_order is False

    def test_orders_despite_pending_if_still_low(self):
        # Stock 10 + pending 20 = 30 ≤ 100 → should order
        decision = self.policy.decide(current_stock=10, pending_orders=20, day=0)
        assert decision.should_order is True

    def test_fixed_quantity(self):
        for stock in [0, 50, 100]:
            d = self.policy.decide(current_stock=stock, pending_orders=0, day=0)
            if d.should_order:
                assert d.quantity == 200

    def test_returns_order_decision_type(self):
        d = self.policy.decide(current_stock=50, pending_orders=0, day=0)
        assert isinstance(d, OrderDecision)


# ── MinMaxPolicy ───────────────────────────────────────────────────────────────

class TestMinMaxPolicy:
    def setup_method(self):
        self.policy = MinMaxPolicy(min_level=100, max_level=500)

    def test_name(self):
        assert "Min" in self.policy.name or "s, S" in self.policy.name

    def test_raises_if_min_ge_max(self):
        with pytest.raises(ValueError):
            MinMaxPolicy(min_level=200, max_level=100)
        with pytest.raises(ValueError):
            MinMaxPolicy(min_level=150, max_level=150)

    def test_orders_to_max_when_at_min(self):
        decision = self.policy.decide(current_stock=100, pending_orders=0, day=0)
        assert decision.should_order is True
        # Should order enough to reach max: 500 - 100 = 400
        assert decision.quantity == pytest.approx(400.0)

    def test_orders_to_max_when_below_min(self):
        decision = self.policy.decide(current_stock=30, pending_orders=0, day=0)
        assert decision.should_order is True
        assert decision.quantity == pytest.approx(470.0)

    def test_no_order_above_min(self):
        decision = self.policy.decide(current_stock=200, pending_orders=0, day=0)
        assert decision.should_order is False

    def test_considers_pending_orders_in_position(self):
        # Stock 20 + pending 200 = 220 > min 100 → no order
        decision = self.policy.decide(current_stock=20, pending_orders=200, day=0)
        assert decision.should_order is False

    def test_variable_order_quantity(self):
        d1 = self.policy.decide(current_stock=50, pending_orders=0, day=0)
        d2 = self.policy.decide(current_stock=80, pending_orders=0, day=0)
        # Both trigger, but different quantities
        assert d1.quantity > d2.quantity

    def test_quantity_never_negative(self):
        # If somehow inventory position > max, quantity should be 0 not negative
        policy = MinMaxPolicy(min_level=50, max_level=100)
        d = policy.decide(current_stock=200, pending_orders=0, day=0)
        # Not ordering because stock > min
        assert d.quantity >= 0


# ── PeriodicReviewPolicy ───────────────────────────────────────────────────────

class TestPeriodicReviewPolicy:
    def setup_method(self):
        self.policy = PeriodicReviewPolicy(review_period=7, target_level=500)

    def test_name_includes_period(self):
        assert "7" in self.policy.name

    def test_orders_on_review_day_zero(self):
        d = self.policy.decide(current_stock=100, pending_orders=0, day=0)
        assert d.should_order is True

    def test_orders_on_multiples_of_period(self):
        for day in [0, 7, 14, 21, 49]:
            d = self.policy.decide(current_stock=0, pending_orders=0, day=day)
            assert d.should_order is True, f"Should order on day {day}"

    def test_no_order_between_review_days(self):
        for day in [1, 2, 3, 4, 5, 6, 8, 9, 13]:
            d = self.policy.decide(current_stock=0, pending_orders=0, day=day)
            assert d.should_order is False, f"Should NOT order on day {day}"

    def test_quantity_reaches_target(self):
        d = self.policy.decide(current_stock=100, pending_orders=0, day=7)
        assert d.quantity == pytest.approx(400.0)  # 500 - 100

    def test_no_order_if_already_at_target(self):
        d = self.policy.decide(current_stock=500, pending_orders=0, day=7)
        assert d.should_order is False

    def test_considers_pending_orders(self):
        # Stock 50 + pending 500 → position 550 > target 500 → no order
        d = self.policy.decide(current_stock=50, pending_orders=500, day=7)
        assert d.should_order is False

    def test_review_period_1(self):
        """With period=1, every day is a review day."""
        policy = PeriodicReviewPolicy(review_period=1, target_level=200)
        for day in range(10):
            d = policy.decide(current_stock=50, pending_orders=0, day=day)
            assert d.should_order is True
