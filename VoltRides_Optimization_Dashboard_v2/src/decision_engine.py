from __future__ import annotations

from typing import Dict, List

import pandas as pd

from src.config import BASE_ANNUAL_OUTPUT, SA10_MIN_WORKERS


def decision_status(best: dict | None, current: dict | None, target: dict) -> dict:
    if best is None:
        return {
            "level": "danger",
            "headline": "Not feasible under selected constraints",
            "message": "The optimizer could not find a feasible setup. Relax worker, overtime, shift, CapEx, or space constraints.",
        }
    if current and current.get("Feasible"):
        return {
            "level": "success",
            "headline": "Feasible with current or near-current setup",
            "message": "The selected target can be achieved without major structural expansion. Focus on OPEX per bike, quality yield, and energy discipline.",
        }
    if best.get("Parallel Stations Added", 0) > 0 or best.get("Annualized CapEx", 0) > 0:
        return {
            "level": "warning",
            "headline": "Feasible with CapEx / parallel capacity",
            "message": "The target can be achieved, but the recommended solution needs duplicated bottleneck capacity or additional equipment.",
        }
    if best.get("Required Shifts", 1) > 1 or best.get("Overtime Min/Day", 0) > 0:
        return {
            "level": "warning",
            "headline": "Feasible with overtime or extra shift",
            "message": "The target can be achieved, but hour-driven OPEX and supervision burden will increase. Compare with bottleneck labour or CapEx options.",
        }
    return {
        "level": "success",
        "headline": "Feasible with labour rebalancing",
        "message": "The target can be achieved by changing station staffing while staying within selected operating constraints.",
    }


def generate_recommendations(
    best: dict | None,
    scenario_df: pd.DataFrame,
    target: dict,
    current_balance: dict,
    required_takt: float,
    station_min_workers: Dict[str, int],
) -> pd.DataFrame:
    recs: List[dict] = []
    annual_target = float(target.get("annual_target", 0))

    if best is None:
        recs.append({
            "Priority": "Critical",
            "Area": "Feasibility",
            "Recommendation": "No feasible setup was found under the current limits. Increase max shifts, allow overtime, increase worker cap, or allow parallel stations.",
            "Why it matters": "The optimizer cannot satisfy station capacity constraints for the selected target.",
        })
        return pd.DataFrame(recs)

    if current_balance.get("cycle_time", 0) > required_takt:
        recs.append({
            "Priority": "High",
            "Area": "Capacity",
            "Recommendation": f"Current cycle time exceeds required takt. Focus first on bottlenecks: {', '.join(current_balance.get('bottlenecks', []))}.",
            "Why it matters": "Improving non-bottleneck stations will not increase output until the bottleneck is relieved.",
        })

    if best.get("Added Workers", 0) > 0:
        recs.append({
            "Priority": "High",
            "Area": "Workforce",
            "Recommendation": f"Add/reallocate {best['Added Workers']:.0f} station worker(s) in the recommended setup.",
            "Why it matters": "The selected objective found this worker allocation as the lowest-risk route to hit target capacity.",
        })

    if best.get("Required Shifts", 1) > 1:
        recs.append({
            "Priority": "Medium",
            "Area": "OPEX",
            "Recommendation": "Extra shift is selected. Track electricity, gas/fuel, supervision, maintenance, and indirect labour before approving.",
            "Why it matters": "Second/third shift can solve capacity but may increase operating cost per bike.",
        })

    if best.get("Overtime Min/Day", 0) > 0:
        recs.append({
            "Priority": "Medium",
            "Area": "Overtime",
            "Recommendation": f"Use up to {best['Overtime Min/Day']:.0f} minutes/day overtime only as a controlled bridge, not a permanent capacity plan.",
            "Why it matters": "Overtime protects short-term output but can raise fatigue and quality risk.",
        })

    if best.get("Parallel Stations Added", 0) > 0:
        recs.append({
            "Priority": "High",
            "Area": "CapEx",
            "Recommendation": f"Add {best['Parallel Stations Added']:.0f} parallel/bottleneck capacity point(s) only after confirming layout space and equipment quotation.",
            "Why it matters": "CapEx should only be approved when labour and shift levers cannot meet takt economically.",
        })

    if annual_target < BASE_ANNUAL_OUTPUT:
        recs.append({
            "Priority": "High",
            "Area": "OPEX per bike",
            "Recommendation": "Target is below base plant design. Avoid adding fixed overhead and maximize utilization of the existing single-shift setup.",
            "Why it matters": "Fixed costs are spread across fewer bikes, increasing cost per unit.",
        })
    elif annual_target > BASE_ANNUAL_OUTPUT:
        recs.append({
            "Priority": "High",
            "Area": "Scale-up",
            "Recommendation": "Target exceeds base design. Compare labour, overtime, extra shift, and parallel station options before final approval.",
            "Why it matters": "Past the base design point, hidden constraints such as test capacity, battery handling, and finished goods space can appear.",
        })

    if station_min_workers.get("SA-10", 0) >= SA10_MIN_WORKERS:
        recs.append({
            "Priority": "Critical",
            "Area": "Safety",
            "Recommendation": "Maintain SA-10 Battery Box at minimum 2 workers in all scenarios.",
            "Why it matters": "Battery handling is safety-critical and should not be optimized below the minimum staffing rule.",
        })

    if not scenario_df.empty:
        alt_count = int(scenario_df[scenario_df["Feasible"] == True].shape[0])
        recs.append({
            "Priority": "Medium",
            "Area": "Decision governance",
            "Recommendation": f"Review the top {min(3, alt_count)} feasible scenarios, not only the cheapest scenario.",
            "Why it matters": "Management may prefer lower hiring, lower CapEx, or lower operational risk over the absolute lowest model cost.",
        })

    return pd.DataFrame(recs)


def constraint_diagnostics(
    best: dict | None,
    station_balance_df: pd.DataFrame,
    required_takt: float,
    max_workers: int,
    max_shifts: int,
    allow_parallel: bool,
) -> pd.DataFrame:
    rows = []
    if station_balance_df is not None and not station_balance_df.empty:
        above = station_balance_df[station_balance_df["Effective Time"] > required_takt]
        for _, row in above.iterrows():
            rows.append({
                "Constraint": f"{row['Station']} takt",
                "Status": "Violated",
                "Diagnostic": f"Effective time {row['Effective Time']:.1f} min exceeds takt {required_takt:.1f} min.",
                "Possible Fix": "Add worker, reduce process time, allow overtime, or add parallel station.",
            })
    if best is None:
        rows.append({
            "Constraint": "Optimization feasibility",
            "Status": "Violated",
            "Diagnostic": "No feasible scenario found.",
            "Possible Fix": f"Increase max workers above {max_workers}, max shifts above {max_shifts}, or allow parallel stations = {allow_parallel}.",
        })
    elif best.get("Risk Level") == "Medium":
        rows.append({
            "Constraint": "Operational risk",
            "Status": "Watch",
            "Diagnostic": "Feasible scenario uses overtime, extra shift, or CapEx.",
            "Possible Fix": "Use a management approval gate and compare next-best alternatives.",
        })
    if not rows:
        rows.append({"Constraint": "All major constraints", "Status": "OK", "Diagnostic": "No major capacity violation in recommended scenario.", "Possible Fix": "Continue monitoring takt, uptime, and quality."})
    return pd.DataFrame(rows)
