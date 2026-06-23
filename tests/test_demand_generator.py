"""
Tests for simulation.demand_generator
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from simulation.demand_generator import DemandGenerator


class TestDemandGeneratorInit:
    def test_valid_normal(self):
        dg = DemandGenerator(pattern="normal", mean=20, std=5)
        assert dg.pattern == "normal"

    def test_invalid_pattern_raises(self):
        with pytest.raises(ValueError, match="Unknown demand pattern"):
            DemandGenerator(pattern="zigzag")

    def test_demand_multiplier_scales_mean(self):
        dg = DemandGenerator(mean=20, demand_multiplier=2.0)
        assert dg.mean == pytest.approx(40.0)

    def test_demand_multiplier_scales_std(self):
        dg = DemandGenerator(mean=20, std=5, demand_multiplier=1.5)
        assert dg.std == pytest.approx(7.5)


class TestNormalDemand:
    def test_non_negative(self):
        dg = DemandGenerator(pattern="normal", mean=10, std=3, seed=0)
        values = [dg.generate(d) for d in range(500)]
        assert all(v >= 0 for v in values)

    def test_roughly_centred_on_mean(self):
        dg = DemandGenerator(pattern="normal", mean=20, std=5, seed=42)
        values = np.array([dg.generate(d) for d in range(5000)])
        assert 18 < values.mean() < 22


class TestPoissonDemand:
    def test_non_negative_integers(self):
        dg = DemandGenerator(pattern="poisson", mean=15, seed=1)
        values = [dg.generate(d) for d in range(200)]
        assert all(v >= 0 for v in values)
        assert all(v == int(v) for v in values)

    def test_mean_close_to_lambda(self):
        dg = DemandGenerator(pattern="poisson", mean=10, seed=7)
        values = np.array([dg.generate(d) for d in range(5000)])
        assert abs(values.mean() - 10) < 0.5


class TestSeasonalDemand:
    def test_non_negative(self):
        dg = DemandGenerator(pattern="seasonal", mean=20, std=4, seed=2)
        values = [dg.generate(d) for d in range(365)]
        assert all(v >= 0 for v in values)

    def test_seasonal_peak_gt_trough(self):
        dg = DemandGenerator(pattern="seasonal", mean=20, std=1, seed=3)
        summer = np.mean([dg.generate(d) for d in range(150, 210)])
        dg2 = DemandGenerator(pattern="seasonal", mean=20, std=1, seed=3)
        winter_days = list(range(0, 30)) + list(range(335, 365))
        winter = np.mean([dg2.generate(d) for d in winter_days])
        assert summer > winter


class TestSporadicDemand:
    def test_non_negative(self):
        dg = DemandGenerator(pattern="sporadic", mean=10, std=3, seed=4)
        values = [dg.generate(d) for d in range(500)]
        assert all(v >= 0 for v in values)

    def test_has_spikes(self):
        """Sporadic demand should occasionally produce values well above mean."""
        dg = DemandGenerator(pattern="sporadic", mean=10, std=2, seed=5)
        values = np.array([dg.generate(d) for d in range(1000)])
        # Some values should exceed 2× mean (spike region)
        assert (values > 20).sum() > 0


class TestConstantDemand:
    def test_always_returns_mean(self):
        dg = DemandGenerator(pattern="constant", mean=15)
        values = [dg.generate(d) for d in range(100)]
        assert all(v == pytest.approx(15.0) for v in values)


class TestGenerateSeries:
    def test_length(self):
        dg = DemandGenerator(mean=10, seed=0)
        series = dg.generate_series(100)
        assert len(series) == 100

    def test_all_non_negative(self):
        dg = DemandGenerator(mean=10, std=3, seed=0)
        assert all(v >= 0 for v in dg.generate_series(500))

    def test_start_day_offset(self):
        """Two generators with same seed but different start_day should differ."""
        dg1 = DemandGenerator(mean=20, std=5, seed=0)
        dg2 = DemandGenerator(mean=20, std=5, seed=0)
        s1 = dg1.generate_series(10, start_day=0)
        s2 = dg2.generate_series(10, start_day=100)
        # Seasonal pattern makes them different; normal may not — use seasonal
        dg3 = DemandGenerator(pattern="seasonal", mean=20, std=5, seed=0)
        dg4 = DemandGenerator(pattern="seasonal", mean=20, std=5, seed=0)
        s3 = dg3.generate_series(5, start_day=0)
        s4 = dg4.generate_series(5, start_day=180)
        assert not np.allclose(s3, s4)
