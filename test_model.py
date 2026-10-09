"""Lightweight validation tests for the synthetic supply-chain model."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import optimize_network as model  # noqa: E402


class SupplyChainModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.warehouses, cls.zones, cls.scenarios, cls.costs = model.load_inputs()
        cls.base_demand = cls.zones["base_demand_units"].to_numpy(dtype=float)
        weights = cls.warehouses["capacity_weight"].to_numpy(dtype=float)
        cls.base_capacity = 0.98 * cls.base_demand.sum() * weights / weights.sum()
        cls.optimized, cls.optimized_cost = model.solve_lp(
            cls.warehouses,
            cls.zones,
            cls.base_demand,
            cls.base_capacity,
            cls.costs,
        )

    def test_network_fill_rate_meets_96_percent_target(self):
        fill_rate = self.optimized.sum() / self.base_demand.sum()
        self.assertGreaterEqual(fill_rate + 1e-8, model.TARGET_FILL_RATE)

    def test_zone_fill_rates_respect_minimum(self):
        zone_fills = self.optimized.sum(axis=0) / self.base_demand
        minimums = self.zones["minimum_zone_fill_rate"].to_numpy(dtype=float)
        self.assertTrue(np.all(zone_fills + 1e-8 >= minimums))

    def test_warehouse_capacity_is_respected(self):
        warehouse_outbound = self.optimized.sum(axis=1)
        self.assertTrue(np.all(warehouse_outbound <= self.base_capacity + 1e-6))

    def test_lp_cost_beats_greedy_benchmark(self):
        _, baseline_cost = model.greedy_baseline(
            self.warehouses,
            self.zones,
            self.base_demand,
            self.base_capacity,
            self.costs,
        )
        self.assertLess(self.optimized_cost, baseline_cost)

    def test_inventory_policy_has_nonnegative_reorder_gaps(self):
        history = pd.read_csv(ROOT / "data" / "input" / "daily_demand_history.csv")
        inventory = pd.read_csv(ROOT / "data" / "input" / "current_inventory.csv")
        policy = model.build_inventory_policy(history, inventory)
        self.assertEqual(len(policy), len(self.zones))
        self.assertTrue((policy["safety_stock_units"] >= 0).all())
        self.assertTrue((policy["reorder_gap_units"] >= 0).all())
        self.assertTrue(policy["replenishment_priority"].isin(
            ["Critical", "High", "Medium", "Low"]
        ).all())


if __name__ == "__main__":
    unittest.main()
