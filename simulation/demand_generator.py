"""
simulation.demand_generator
============================
Generates daily demand values according to several statistical patterns.

Supported patterns: normal, poisson, seasonal, sporadic, constant
"""

from __future__ import annotations

import math
from typing import List, Optional

import numpy as np

VALID_PATTERNS = {"normal", "poisson", "seasonal", "sporadic", "constant"}


class DemandGenerator:
    """
    Generates demand values for inventory simulation.

    Parameters
    ----------
    pattern : str
        One of 'normal', 'poisson', 'seasonal', 'sporadic', 'constant'.
    mean : float
        Base mean demand per day (before multiplier).
    std : float
        Base standard deviation (used by normal / sporadic / seasonal).
    seed : int | None
        Random seed for reproducibility.
    demand_multiplier : float
        Scales both mean and std uniformly (useful for scenario analysis).
    """

    def __init__(
        self,
        pattern: str = "normal",
        mean: float = 20.0,
        std: float = 5.0,
        seed: Optional[int] = None,
        demand_multiplier: float = 1.0,
    ):
        pattern = pattern.lower()
        if pattern not in VALID_PATTERNS:
            raise ValueError(
                f"Unknown demand pattern '{pattern}'. "
                f"Valid options: {sorted(VALID_PATTERNS)}"
            )
        self.pattern = pattern
        self.mean = mean * demand_multiplier
        self.std = std * demand_multiplier
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    # ── Public API ────────────────────────────────────────────────────────────

    def generate(self, day: int) -> float:
        """Return a single non-negative demand value for the given day."""
        return max(0.0, self._dispatch(day))

    def generate_series(self, num_days: int, start_day: int = 0) -> List[float]:
        """Return a list of `num_days` demand values starting at `start_day`."""
        return [self.generate(start_day + d) for d in range(num_days)]

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def _dispatch(self, day: int) -> float:
        if self.pattern == "normal":
            return self._normal()
        if self.pattern == "poisson":
            return self._poisson()
        if self.pattern == "seasonal":
            return self._seasonal(day)
        if self.pattern == "sporadic":
            return self._sporadic()
        if self.pattern == "constant":
            return self.mean
        raise ValueError(f"Unknown pattern: {self.pattern}")  # pragma: no cover

    # ── Pattern implementations ───────────────────────────────────────────────

    def _normal(self) -> float:
        return float(self._rng.normal(loc=self.mean, scale=max(self.std, 1e-9)))

    def _poisson(self) -> float:
        return float(self._rng.poisson(lam=max(self.mean, 0.0)))

    def _seasonal(self, day: int) -> float:
        """
        Sinusoidal seasonal pattern with annual period (365 days).
        Peak around day 180 (summer), trough around day 0/365 (winter).
        """
        amplitude = 0.4 * self.mean
        seasonal_mean = self.mean + amplitude * math.sin(2 * math.pi * day / 365)
        noise = float(self._rng.normal(loc=0.0, scale=max(self.std, 1e-9)))
        return seasonal_mean + noise

    def _sporadic(self) -> float:
        """
        Most days have near-zero demand; occasional large spikes.
        ~20 % chance of a spike day where demand is 3–6× mean.
        """
        if self._rng.random() < 0.20:
            # Spike: mean × uniform(3, 6)
            spike = self.mean * self._rng.uniform(3.0, 6.0)
            return float(spike)
        # Quiet day: small normal draw
        quiet = float(self._rng.normal(loc=self.mean * 0.3, scale=max(self.std * 0.3, 1e-9)))
        return quiet
