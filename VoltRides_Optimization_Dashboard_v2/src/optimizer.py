from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from src.config import BASE_ANNUAL_OUTPUT, BASE_SCRAP_RATE, BASE_SHIFTS_PER_DAY, SHIFT_MINUTES, WORKING_DAYS_YEAR
from src.labour_model import estimate_station_labour_delta, estimate_overtime_cost
from src.opex_model import calculate_opex
from src.production_model import calculate_capacity, calculate_line_balance
from src.solver_model import SolverSettings, solve_capacity_optimization


ALTERNATIVE_OBJECTIVES = [
    "Minimize total operating cost",
    "Minimize additional workers",
    "Minimize CapEx",
    "Maximize utilization",
    "Balanced decision score",
]


def _scenario_from_solution(
    label: str,
    solution: dict,
    target_annual_output: float,
    station_times: Dict[str, float],
    current_workers: Dict[str, int],
    station_skill: Dict[str, str],
    opex_df: pd.DataFrame,
    uptime: float,
    scrap_rate: float,
    objective: str,
    monthly_rates: Optional[Dict[str, float]] = None,
    energy_escalation_pct: float = 0.0,
    base_labour_annual: float = 0.0,
) -> dict:
    workers = solution.get("workers", current_workers).copy()
    parallel = solution.get("parallel", {s: 0 for s in station_times}).copy()
    shifts = int(solution.get("shifts", 1))
    overtime = int(solution.get("overtime_minutes", 0))
    balance = calculate_line_balance(station_times, workers, parallel)
    capacity = calculate_capacity(balance["cycle_time"], SHIFT_MINUTES, shifts, WORKING_DAYS_YEAR, uptime, overtime)
    labour = estimate_station_labour_delta(current_workers, workers, station_skill, monthly_rates)
    overtime_cost = estimate_overtime_cost(sum(workers.values()), overtime, WORKING_DAYS_YEAR, monthly_rates)
    annual_opex, opex_breakdown = calculate_opex(
        opex_df=opex_df,
        target_annual_output=target_annual_output,
        base_annual_output=BASE_ANNUAL_OUTPUT,
        shifts_per_day=shifts,
        base_shifts_per_day=BASE_SHIFTS_PER_DAY,
        overtime_minutes_per_day=overtime,
        scrap_rate=scrap_rate,
        base_scrap_rate=BASE_SCRAP_RATE,
        energy_escalation_pct=energy_escalation_pct,
    )
    annualized_capex = float(solution.get("annualized_capex", 0.0))
    operating_cost = annual_opex + base_labour_annual + labour["annual_labour_delta"] + overtime_cost + annualized_capex
    feasible = capacity["annual_capacity"] >= target_annual_output
    utilization = (target_annual_output / capacity["annual_capacity"] * 100) if capacity["annual_capacity"] else 0.0
    added_workers = int(labour["added_workers"])
    parallel_count = int(sum(int(v) for v in parallel.values()))
    risk_level = "Low"
    if not feasible:
        risk_level = "High"
    elif utilization > 95 or overtime > 0:
        risk_level = "Medium"
    elif shifts > 1 or parallel_count > 0:
        risk_level = "Medium"

    return {
        "Scenario": label,
        "Objective Used": objective,
        "Feasible": feasible,
        "Decision Status": "Feasible" if feasible else "Infeasible",
        "Annual Capacity": capacity["annual_capacity"],
        "Daily Capacity": capacity["daily_capacity"],
        "Target Output": target_annual_output,
        "Capacity Gap": capacity["annual_capacity"] - target_annual_output,
        "Cycle Time": balance["cycle_time"],
        "Required Shifts": shifts,
        "Overtime Min/Day": overtime,
        "Bottleneck": ", ".join(balance["bottlenecks"]),
        "Total Station Workers": sum(workers.values()),
        "Added Workers": added_workers,
        "Parallel Stations Added": parallel_count,
        "Expansion Area SqFt": float(solution.get("expansion_area_sqft", 0.0)),
        "Annual OPEX": annual_opex,
        "Base Annual Labour": base_labour_annual,
        "Annual Labour Delta": labour["annual_labour_delta"],
        "Annualized CapEx": annualized_capex,
        "Annual Overtime Cost": overtime_cost,
        "Annual Operating Cost": operating_cost,
        "OPEX per Bike": annual_opex / target_annual_output if target_annual_output else 0,
        "Operating Cost per Bike": operating_cost / target_annual_output if target_annual_output else 0,
        "Utilization %": utilization,
        "Risk Level": risk_level,
        "Workers": workers,
        "Parallel": parallel,
        "Effective Times": balance["effective_times"],
        "OPEX Breakdown": opex_breakdown,
        "Labour Breakdown": labour["breakdown"],
        "Solver Status": solution.get("status", "Unknown"),
    }


def _rank_key(scenario: dict, objective: str):
    text = str(objective).lower()
    if "workers" in text:
        return (scenario["Added Workers"], scenario["Annual Operating Cost"], -scenario["Utilization %"])
    if "capex" in text:
        return (scenario["Annualized CapEx"], scenario["Annual Operating Cost"], scenario["Added Workers"])
    if "utilization" in text:
        return (abs(90 - scenario["Utilization %"]), scenario["Annual Operating Cost"])
    if "total" in text:
        return (scenario["Annual Operating Cost"], scenario["Added Workers"])
    return (scenario["Operating Cost per Bike"], scenario["Added Workers"])


def run_optimization(
    target: dict,
    station_times: Dict[str, float],
    current_workers: Dict[str, int],
    station_min_workers: Dict[str, int],
    station_skill: Dict[str, str],
    station_type: Dict[str, str],
    opex_df: pd.DataFrame,
    objective: str,
    uptime: float,
    max_workers_per_station: int,
    max_shifts_per_day: int,
    max_overtime_minutes_per_day: int,
    scrap_rate: float,
    allow_parallel_stations: bool,
    available_expansion_area_sqft: float,
    monthly_rates: Optional[Dict[str, float]] = None,
    energy_escalation_pct: float = 0.0,
    base_labour_annual: float = 0.0,
) -> tuple[dict | None, list[dict], pd.DataFrame, dict]:
    settings = SolverSettings(
        max_workers_per_station=max_workers_per_station,
        max_shifts_per_day=max_shifts_per_day,
        max_overtime_minutes_per_day=max_overtime_minutes_per_day,
        uptime=uptime,
        allow_parallel_stations=allow_parallel_stations,
        available_expansion_area_sqft=available_expansion_area_sqft,
    )
    target_daily = float(target["daily_target"])
    target_annual = float(target["annual_target"])

    scenarios: list[dict] = []
    seen = set()

    # Current setup diagnostic.
    current_solution = {
        "status": "Current setup",
        "workers": current_workers,
        "parallel": {s: 0 for s in station_times},
        "shifts": 1,
        "overtime_minutes": 0,
        "annualized_capex": 0.0,
        "expansion_area_sqft": 0.0,
    }
    scenarios.append(_scenario_from_solution("Current setup", current_solution, target_annual, station_times, current_workers, station_skill, opex_df, uptime, scrap_rate, "Current", monthly_rates, energy_escalation_pct, base_labour_annual))

    # Preferred objective plus next-best management alternatives.
    objectives_to_solve = [objective] + [obj for obj in ALTERNATIVE_OBJECTIVES if obj != objective]
    solver_metadata = {"model": "MILP binary station-option model with greedy fallback", "solved_objectives": []}

    for obj in objectives_to_solve:
        sol = solve_capacity_optimization(
            target_daily_output=target_daily,
            target_annual_output=target_annual,
            station_times=station_times,
            current_workers=current_workers,
            station_min_workers=station_min_workers,
            station_skill=station_skill,
            settings=settings,
            objective=obj,
            monthly_rates=monthly_rates,
        )
        solver_metadata["solved_objectives"].append({"objective": obj, "status": sol.get("status", "Unknown"), "feasible": sol.get("feasible", False)})
        if not sol.get("feasible"):
            continue
        label = "Recommended optimum" if obj == objective else obj.replace("Minimize ", "Lowest ").replace("Maximize ", "Highest ")
        scenario = _scenario_from_solution(label, sol, target_annual, station_times, current_workers, station_skill, opex_df, uptime, scrap_rate, obj, monthly_rates, energy_escalation_pct, base_labour_annual)
        key = (scenario["Required Shifts"], scenario["Overtime Min/Day"], tuple(sorted(scenario["Workers"].items())), tuple(sorted(scenario["Parallel"].items())))
        if key not in seen:
            seen.add(key)
            scenarios.append(scenario)

    scenario_df = pd.DataFrame([{k: v for k, v in s.items() if k not in {"Workers", "Parallel", "Effective Times", "OPEX Breakdown", "Labour Breakdown"}} for s in scenarios])
    feasible = [s for s in scenarios if s["Feasible"]]
    best = min(feasible, key=lambda s: _rank_key(s, objective)) if feasible else None

    if not scenario_df.empty:
        scenario_df["Recommended"] = scenario_df["Scenario"].eq(best["Scenario"] if best else "")
        scenario_df = scenario_df.sort_values(["Feasible", "Recommended", "Operating Cost per Bike"], ascending=[False, False, True]).reset_index(drop=True)
        scenario_df.insert(0, "Rank", range(1, len(scenario_df) + 1))

    return best, scenarios, scenario_df, solver_metadata
