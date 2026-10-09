"""One-command runner for the last-mile delivery optimization project."""
from generate_data import generate
from optimize_routes import run_all


def main() -> None:
    generate()
    result = run_all()
    summary = result["summary"]
    print("\nProject completed.")
    print(f"Scenarios evaluated: {len(summary)}")
    print(f"Average distance reduction: {summary['distance_reduction_pct'].mean():.2f}%")
    print(f"Minimum active-fleet utilization: {summary['active_fleet_utilization_pct'].min():.1f}%")
    print("Scenario summary: data/output/scenario_summary.csv")
    print("Optimized stop assignments: data/output/optimized_stop_assignments.csv")


if __name__ == "__main__":
    main()
