"""Solve the multi-warehouse transportation LP and export dashboard-ready outputs."""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "input"
OUTPUT = ROOT / "data" / "output"
OUTPUT.mkdir(parents=True, exist_ok=True)
TARGET_FILL_RATE = 0.96


def load_inputs():
    warehouses = pd.read_csv(INPUT / "warehouses.csv")
    zones = pd.read_csv(INPUT / "demand_zones.csv")
    scenarios = pd.read_csv(INPUT / "scenario_inputs.csv")
    costs_long = pd.read_csv(INPUT / "shipping_costs.csv")
    cost_matrix = costs_long.set_index("warehouse_id")[zones["zone_id"].tolist()]
    # Ensure matrix order matches warehouse input row order.
    cost_matrix = cost_matrix.loc[warehouses["warehouse_id"]]
    return warehouses, zones, scenarios, cost_matrix


def solve_lp(warehouses, zones, demand, capacity, cost_matrix):
    """Minimize freight cost, honoring facility capacity and zone service floors."""
    n_w = len(warehouses)
    n_z = len(zones)
    costs = cost_matrix.to_numpy(dtype=float)
    n_vars = n_w * n_z
    c = costs.reshape(-1)

    # Each warehouse's outbound volume cannot exceed its scenario capacity.
    a_ub = []
    b_ub = []
    for w in range(n_w):
        row = np.zeros((n_w, n_z))
        row[w, :] = 1.0
        a_ub.append(row.reshape(-1))
        b_ub.append(float(capacity[w]))

    # Demand upper bound for each zone: do not ship more than requested.
    for z in range(n_z):
        row = np.zeros((n_w, n_z))
        row[:, z] = 1.0
        a_ub.append(row.reshape(-1))
        b_ub.append(float(demand[z]))

    # Minimum local service floor (90% by default) prevents abandoning a zone.
    for z, zone in enumerate(zones.itertuples(index=False)):
        row = np.zeros((n_w, n_z))
        row[:, z] = -1.0
        a_ub.append(row.reshape(-1))
        b_ub.append(-float(zone.minimum_zone_fill_rate) * float(demand[z]))

    # Network-wide fill rate must be at least 96% of total demand.
    a_ub.append(-np.ones(n_vars))
    b_ub.append(-TARGET_FILL_RATE * float(np.sum(demand)))

    result = linprog(
        c,
        A_ub=np.asarray(a_ub),
        b_ub=np.asarray(b_ub),
        bounds=(0, None),
        method="highs",
    )
    if not result.success:
        raise RuntimeError(f"LP failed: {result.message}")
    return result.x.reshape(n_w, n_z), float(result.fun)


def greedy_baseline(warehouses, zones, demand, capacity, cost_matrix):
    """A simple zone-by-zone cheapest-available-warehouse benchmark.

    This transparent heuristic handles zones in descending demand order and
    uses the cheapest remaining-capacity warehouse for each zone. It is a
    comparison baseline, not a representation of any real company's process.
    """
    n_w = len(warehouses)
    n_z = len(zones)
    costs = cost_matrix.to_numpy(dtype=float)
    remaining = np.asarray(capacity, dtype=float).copy()
    shipped = np.zeros((n_w, n_z), dtype=float)
    targets = TARGET_FILL_RATE * np.asarray(demand, dtype=float)

    # Largest demand zones are processed first; ties are stable by input order.
    order = sorted(range(n_z), key=lambda z: (-demand[z], z))
    for z in order:
        need = targets[z]
        for w in np.argsort(costs[:, z], kind="stable"):
            quantity = min(need, remaining[w])
            if quantity > 0:
                shipped[w, z] += quantity
                remaining[w] -= quantity
                need -= quantity
            if need <= 1e-8:
                break
        if need > 1e-6:
            raise RuntimeError(
                "Greedy benchmark could not meet its 96% zone targets. "
                "Adjust scenario capacities or benchmark policy."
            )
    baseline_cost = float(np.sum(shipped * costs))
    return shipped, baseline_cost


def build_inventory_policy(demand_history: pd.DataFrame, inventory: pd.DataFrame) -> pd.DataFrame:
    """Calculate reorder points and priority bands from a 95% service target.

    Assumptions: independent daily demand, a fixed lead time by zone, and a
    normal-approximation safety stock of z * daily demand standard deviation *
    square root of lead time. This is an instructional policy, not a production
    inventory system.
    """
    z_score_95 = 1.645
    demand_stats = demand_history.groupby("zone_id")["demand_units"].agg(
        average_daily_demand="mean", daily_demand_std="std"
    ).reset_index()
    policy = inventory.merge(demand_stats, on="zone_id", how="left", validate="one_to_one")
    policy["target_service_level"] = 0.95
    policy["safety_stock_units"] = np.ceil(
        z_score_95 * policy["daily_demand_std"] * np.sqrt(policy["lead_time_days"])
    ).astype(int)
    policy["reorder_point_units"] = np.ceil(
        policy["average_daily_demand"] * policy["lead_time_days"]
        + policy["safety_stock_units"]
    ).astype(int)
    policy["inventory_position_units"] = policy["on_hand_units"] + policy["on_order_units"]
    policy["reorder_gap_units"] = np.maximum(
        0, policy["reorder_point_units"] - policy["inventory_position_units"]
    ).astype(int)
    policy["days_of_cover"] = (
        policy["inventory_position_units"] / policy["average_daily_demand"]
    ).round(2)

    def priority(row):
        if row["inventory_position_units"] <= row["safety_stock_units"]:
            return "Critical"
        if row["inventory_position_units"] <= row["reorder_point_units"]:
            return "High"
        if row["inventory_position_units"] <= 1.25 * row["reorder_point_units"]:
            return "Medium"
        return "Low"

    policy["replenishment_priority"] = policy.apply(priority, axis=1)
    numeric_cols = ["average_daily_demand", "daily_demand_std"]
    policy[numeric_cols] = policy[numeric_cols].round(2)
    columns = [
        "zone_id", "average_daily_demand", "daily_demand_std", "lead_time_days",
        "target_service_level", "safety_stock_units", "reorder_point_units",
        "on_hand_units", "on_order_units", "inventory_position_units",
        "reorder_gap_units", "days_of_cover", "replenishment_priority",
    ]
    priority_rank = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    policy["_priority_rank"] = policy["replenishment_priority"].map(priority_rank)
    return policy.sort_values(
        ["_priority_rank", "reorder_gap_units"], ascending=[True, False]
    )[columns].reset_index(drop=True)


def summarize_shipments(shipped, warehouses, zones, demand, capacity, cost_matrix, scenario_id):
    costs = cost_matrix.to_numpy(dtype=float)
    records = []
    for w, warehouse in enumerate(warehouses.itertuples(index=False)):
        for z, zone in enumerate(zones.itertuples(index=False)):
            units = float(shipped[w, z])
            if units > 1e-7:
                records.append({
                    "scenario_id": scenario_id,
                    "warehouse_id": warehouse.warehouse_id,
                    "zone_id": zone.zone_id,
                    "demand_units": float(demand[z]),
                    "units_shipped": round(units, 3),
                    "unit_shipping_cost": float(costs[w, z]),
                    "logistics_cost": round(units * costs[w, z], 3),
                })
    return records


def main() -> None:
    warehouses, zones, scenarios, cost_matrix = load_inputs()
    demand_history = pd.read_csv(INPUT / "daily_demand_history.csv")
    current_inventory = pd.read_csv(INPUT / "current_inventory.csv")
    inventory_policy = build_inventory_policy(demand_history, current_inventory)
    base_demand = zones["base_demand_units"].to_numpy(dtype=float)
    weights = warehouses["capacity_weight"].to_numpy(dtype=float)
    # Total nominal capacity is 98% of base demand; scenario multipliers vary it.
    nominal_capacity_total = 0.98 * float(base_demand.sum())
    base_capacity = nominal_capacity_total * weights / weights.sum()

    scenario_rows = []
    optimized_rows = []
    baseline_rows = []
    warehouse_rows = []
    zone_rows = []

    for sc in scenarios.itertuples(index=False):
        demand = base_demand * float(sc.demand_multiplier)
        capacity = base_capacity * float(sc.capacity_multiplier)

        optimized, optimized_cost = solve_lp(
            warehouses, zones, demand, capacity, cost_matrix
        )
        baseline, baseline_cost = greedy_baseline(
            warehouses, zones, demand, capacity, cost_matrix
        )

        demand_total = float(demand.sum())
        opt_units = float(optimized.sum())
        base_units = float(baseline.sum())
        opt_fill = opt_units / demand_total
        base_fill = base_units / demand_total
        savings_pct = (baseline_cost - optimized_cost) / baseline_cost * 100.0

        scenario_rows.append({
            "scenario_id": sc.scenario_id,
            "demand_multiplier": float(sc.demand_multiplier),
            "capacity_multiplier": float(sc.capacity_multiplier),
            "total_demand_units": round(demand_total, 2),
            "optimized_units_filled": round(opt_units, 2),
            "optimized_fill_rate": round(opt_fill, 6),
            "baseline_units_filled": round(base_units, 2),
            "baseline_fill_rate": round(base_fill, 6),
            "baseline_logistics_cost": round(baseline_cost, 2),
            "optimized_logistics_cost": round(optimized_cost, 2),
            "cost_savings_pct": round(savings_pct, 4),
            "lp_status": "Optimal",
        })

        optimized_rows.extend(summarize_shipments(
            optimized, warehouses, zones, demand, capacity, cost_matrix, sc.scenario_id
        ))
        baseline_rows.extend(summarize_shipments(
            baseline, warehouses, zones, demand, capacity, cost_matrix, sc.scenario_id
        ))

        opt_by_wh = optimized.sum(axis=1)
        for w, wh in enumerate(warehouses.itertuples(index=False)):
            warehouse_rows.append({
                "scenario_id": sc.scenario_id,
                "warehouse_id": wh.warehouse_id,
                "capacity_units": round(float(capacity[w]), 2),
                "optimized_units_shipped": round(float(opt_by_wh[w]), 2),
                "utilization_rate": round(float(opt_by_wh[w] / capacity[w]), 6),
            })
        opt_by_zone = optimized.sum(axis=0)
        for z, zone in enumerate(zones.itertuples(index=False)):
            zone_rows.append({
                "scenario_id": sc.scenario_id,
                "zone_id": zone.zone_id,
                "demand_units": round(float(demand[z]), 2),
                "optimized_units_filled": round(float(opt_by_zone[z]), 2),
                "fill_rate": round(float(opt_by_zone[z] / demand[z]), 6),
                "minimum_fill_rate": float(zone.minimum_zone_fill_rate),
            })

    summary = pd.DataFrame(scenario_rows)
    optimized_detail = pd.DataFrame(optimized_rows)
    baseline_detail = pd.DataFrame(baseline_rows)
    warehouse_util = pd.DataFrame(warehouse_rows)
    zone_service = pd.DataFrame(zone_rows)

    summary.to_csv(OUTPUT / "scenario_summary.csv", index=False)
    optimized_detail.to_csv(OUTPUT / "optimized_shipments.csv", index=False)
    baseline_detail.to_csv(OUTPUT / "baseline_shipments.csv", index=False)
    warehouse_util.to_csv(OUTPUT / "warehouse_utilization.csv", index=False)
    zone_service.to_csv(OUTPUT / "zone_service_levels.csv", index=False)
    inventory_policy.to_csv(OUTPUT / "inventory_policy_recommendations.csv", index=False)

    print("Scenario results")
    print(summary[["scenario_id", "optimized_fill_rate", "cost_savings_pct"]].to_string(index=False))
    print("\nAggregate checks")
    print(f"Scenarios solved: {len(summary)}")
    print(f"Minimum optimized fill rate: {summary['optimized_fill_rate'].min():.2%}")
    print(f"Average cost savings vs. greedy baseline: {summary['cost_savings_pct'].mean():.2f}%")
    print(f"Base-scenario savings: {summary.loc[summary['scenario_id'] == 'S01_Base', 'cost_savings_pct'].iloc[0]:.2f}%")
    print("Replenishment priorities:")
    print(inventory_policy["replenishment_priority"].value_counts().to_dict())
    print(f"Outputs written to: {OUTPUT}")


if __name__ == "__main__":
    main()
