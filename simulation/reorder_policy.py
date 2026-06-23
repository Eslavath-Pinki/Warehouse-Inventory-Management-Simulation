"""
simulation.reorder_policy
=========================
Implements the three inventory reorder policies:
  - ReorderPointPolicy  (s, Q)  — fixed reorder point + fixed order quantity
  - MinMaxPolicy        (s, S)  — order up to max when stock falls below min
  - PeriodicReviewPolicy(R, S)  — review every R days, order up to target S
"""

from dataclasses import dataclass


@dataclass
class OrderDecision:
    """Result returned by every policy's decide() method."""
    should_order: bool
    quantity: float


# ── Base ──────────────────────────────────────────────────────────────────────

class BasePolicy:
    """Abstract base — subclasses must implement decide() and name."""

    @property
    def name(self) -> str:
        raise NotImplementedError

    def decide(self, current_stock: float, pending_orders: float, day: int) -> OrderDecision:
        raise NotImplementedError


# ── Reorder Point (s, Q) ──────────────────────────────────────────────────────

class ReorderPointPolicy(BasePolicy):
    """
    Classic (s, Q) policy.
    Place an order of fixed size `order_quantity` whenever the inventory
    position (on-hand + on-order) falls to or below `reorder_point`.
    """

    def __init__(self, reorder_point: float, order_quantity: float):
        self.reorder_point = reorder_point
        self.order_quantity = order_quantity

    @property
    def name(self) -> str:
        return f"Reorder Point (s, Q) [s={self.reorder_point}, Q={self.order_quantity}]"

    def decide(self, current_stock: float, pending_orders: float, day: int) -> OrderDecision:
        inventory_position = current_stock + pending_orders
        if inventory_position <= self.reorder_point:
            return OrderDecision(should_order=True, quantity=self.order_quantity)
        return OrderDecision(should_order=False, quantity=0.0)


# ── Min-Max (s, S) ────────────────────────────────────────────────────────────

class MinMaxPolicy(BasePolicy):
    """
    (s, S) Min-Max policy.
    When inventory position falls to or below `min_level`, order enough
    to bring it up to `max_level`.
    """

    def __init__(self, min_level: float, max_level: float):
        if min_level >= max_level:
            raise ValueError(
                f"min_level ({min_level}) must be strictly less than max_level ({max_level})"
            )
        self.min_level = min_level
        self.max_level = max_level

    @property
    def name(self) -> str:
        return f"Min-Max (s, S) [s={self.min_level}, S={self.max_level}]"

    def decide(self, current_stock: float, pending_orders: float, day: int) -> OrderDecision:
        inventory_position = current_stock + pending_orders
        if inventory_position <= self.min_level:
            quantity = max(0.0, self.max_level - inventory_position)
            return OrderDecision(should_order=quantity > 0, quantity=quantity)
        return OrderDecision(should_order=False, quantity=0.0)


# ── Periodic Review (R, S) ────────────────────────────────────────────────────

class PeriodicReviewPolicy(BasePolicy):
    """
    (R, S) Periodic Review policy.
    Review inventory every `review_period` days (including day 0).
    On review days, order enough to bring inventory position up to `target_level`.
    """

    def __init__(self, review_period: int, target_level: float):
        self.review_period = review_period
        self.target_level = target_level

    @property
    def name(self) -> str:
        return f"Periodic Review (R={self.review_period}, S={self.target_level})"

    def decide(self, current_stock: float, pending_orders: float, day: int) -> OrderDecision:
        # Only review on multiples of review_period (day 0 counts)
        if day % self.review_period != 0:
            return OrderDecision(should_order=False, quantity=0.0)

        inventory_position = current_stock + pending_orders
        quantity = max(0.0, self.target_level - inventory_position)
        if quantity > 0:
            return OrderDecision(should_order=True, quantity=quantity)
        return OrderDecision(should_order=False, quantity=0.0)
