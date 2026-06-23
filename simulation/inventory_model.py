"""
simulation.inventory_model
===========================
Core discrete-event inventory simulation.

Classes
-------
Product        — product master data
DailyRecord    — one row of simulation output
InventoryModel — runs the day-by-day simulation
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional

import pandas as pd

from simulation.demand_generator import DemandGenerator
from simulation.reorder_policy import BasePolicy, OrderDecision


# ── Product ───────────────────────────────────────────────────────────────────

@dataclass
class Product:
    product_id: str
    product_name: str
    initial_stock: float
    mean_demand: float
    std_demand: float
    lead_time_min: int
    lead_time_max: int
    holding_cost: float          # cost per unit per day
    stockout_cost: float         # cost per unit of unmet demand
    ordering_cost: float         # fixed cost per order placed
    reorder_point: float
    order_quantity: float
    max_stock: float
    review_period: int
    demand_pattern: str = "normal"

    @classmethod
    def from_dict(cls, d: dict) -> "Product":
        """Construct a Product from a dict (e.g. a CSV row). All values are cast."""
        return cls(
            product_id=str(d["product_id"]),
            product_name=str(d["product_name"]),
            initial_stock=float(d["initial_stock"]),
            mean_demand=float(d["mean_demand"]),
            std_demand=float(d["std_demand"]),
            lead_time_min=int(d["lead_time_min"]),
            lead_time_max=int(d["lead_time_max"]),
            holding_cost=float(d["holding_cost"]),
            stockout_cost=float(d["stockout_cost"]),
            ordering_cost=float(d["ordering_cost"]),
            reorder_point=float(d["reorder_point"]),
            order_quantity=float(d["order_quantity"]),
            max_stock=float(d["max_stock"]),
            review_period=int(d["review_period"]),
            demand_pattern=str(d.get("demand_pattern", "normal")),
        )


# ── DailyRecord ───────────────────────────────────────────────────────────────

@dataclass
class DailyRecord:
    day: int
    stock_level: float
    demand: float
    units_sold: float
    unmet_demand: float
    order_placed: float        # quantity ordered today (0 if no order)
    order_received: float      # quantity received today
    holding_cost: float
    stockout_cost: float
    ordering_cost: float
    total_cost: float
    stockout_occurred: bool


# ── InventoryModel ────────────────────────────────────────────────────────────

class InventoryModel:
    """
    Discrete-time (daily) inventory simulation.

    Parameters
    ----------
    product : Product
    policy  : BasePolicy
    demand_generator : DemandGenerator
    num_days : int
    lead_time_multiplier : float
        Scales the product's lead-time range (scenario analysis).
    seed : int | None
        Seed for the lead-time RNG (demand seed is set on DemandGenerator).
    """

    def __init__(
        self,
        product: Product,
        policy: BasePolicy,
        demand_generator: DemandGenerator,
        num_days: int = 365,
        lead_time_multiplier: float = 1.0,
        seed: Optional[int] = None,
    ):
        self.product = product
        self.policy = policy
        self.demand_generator = demand_generator
        self.num_days = num_days
        self.lead_time_multiplier = lead_time_multiplier
        self._rng = random.Random(seed)
        self._records: List[DailyRecord] = []

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self) -> List[DailyRecord]:
        """Execute the simulation and return the list of DailyRecords."""
        p = self.product
        stock = p.initial_stock

        # pending_orders: dict {arrival_day -> quantity}
        pending: dict = {}
        pending_total = 0.0

        self._records = []

        for day in range(self.num_days):
            # 1. Receive any orders due today
            received = pending.pop(day, 0.0)
            stock += received
            pending_total -= received
            pending_total = max(0.0, pending_total)

            # 2. Generate demand
            demand = self.demand_generator.generate(day)

            # 3. Fulfil demand
            units_sold = min(stock, demand)
            unmet = max(0.0, demand - units_sold)
            stock = max(0.0, stock - units_sold)

            # 4. Compute costs
            h_cost = stock * p.holding_cost
            s_cost = unmet * p.stockout_cost
            stockout_flag = unmet > 0

            # 5. Policy decision
            decision: OrderDecision = self.policy.decide(
                current_stock=stock,
                pending_orders=pending_total,
                day=day,
            )

            o_cost = 0.0
            qty_ordered = 0.0
            if decision.should_order and decision.quantity > 0:
                qty_ordered = decision.quantity
                o_cost = p.ordering_cost
                lead_time = self._sample_lead_time()
                arrival = day + lead_time
                pending[arrival] = pending.get(arrival, 0.0) + qty_ordered
                pending_total += qty_ordered

            total = h_cost + s_cost + o_cost

            self._records.append(DailyRecord(
                day=day,
                stock_level=stock,
                demand=demand,
                units_sold=units_sold,
                unmet_demand=unmet,
                order_placed=qty_ordered,
                order_received=received,
                holding_cost=h_cost,
                stockout_cost=s_cost,
                ordering_cost=o_cost,
                total_cost=total,
                stockout_occurred=stockout_flag,
            ))

        return self._records

    def results_df(self) -> pd.DataFrame:
        """Run the simulation (if not already run) and return results as a DataFrame."""
        if not self._records:
            self.run()
        rows = [vars(r) for r in self._records]
        df = pd.DataFrame(rows)
        # Ensure bool column is proper bool dtype
        df["stockout_occurred"] = df["stockout_occurred"].astype(bool)
        return df

    # ── Internals ─────────────────────────────────────────────────────────────

    def _sample_lead_time(self) -> int:
        p = self.product
        lo = max(1, int(math.ceil(p.lead_time_min * self.lead_time_multiplier)))
        hi = max(lo, int(math.ceil(p.lead_time_max * self.lead_time_multiplier)))
        return self._rng.randint(lo, hi)
