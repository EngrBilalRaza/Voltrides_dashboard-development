from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import pandas as pd

from src.config import (
    CAPEX_ANNUALIZATION_YEARS,
    DEFAULT_PARALLEL_STATION_AREA_SQFT,
    DEFAULT_PARALLEL_STATION_CAPEX,
    MAX_OVERTIME_MINUTES_PER_DAY,
    SHIFT_MINUTES,
    WORKING_DAYS_YEAR,
)
from src.labour_model import annual_rate_for_skill, estimate_overtime_cost
from src.production_model import calculate_capacity, calculate_line_balance


@dataclass
class SolverSettings:
    max_workers_per_station: int = 4
    max_shifts_per_day: int = 3
    max_overtime_minutes_per_day: int = MAX_OVERTIME_MINUTES_PER_DAY
    uptime: float = 0.90
    allow_parallel_stations: bool = True
    available_expansion_area_sqft: float = 1200.0
    parallel_station_capex: float = DEFAULT_PARALLEL_STATION_CAPEX
    max_parallel_stations: int = 2
    parallel_station_area_sqft: float = DEFAULT_PARALLEL_STATION_AREA_SQFT
    capex_annualization_years: int = CAPEX_ANNUALIZATION_YEARS


def _objective_weights(objective: str) -> Dict[str, float]:
    text = str(objective).lower()
    if "workers" in text:
        return {"cost": 0.001, "workers": 1_000_000, "capex": 0.05, "utilization": 0.0}
    if "capex" in text:
        return {"cost": 0.002, "workers": 100_000, "capex": 1.0, "utilization": 0.0}
    if "utilization" in text:
        return {"cost": 0.01, "workers": 30_000, "capex": 0.10, "utilization": 250_000}
    if "balanced" in text:
        return {"cost": 1.0, "workers": 250_000, "capex": 0.30, "utilization": 30_000}
    return {"cost": 1.0, "workers": 60_000, "capex": 0.20, "utilization": 0.0}


def _candidate_worker_options(station: str, min_workers: int, max_workers: int, allow_parallel: bool) -> list[dict]:
    options = []
    for workers in range(max(1, min_workers), max_workers + 1):
        parallel_values = [0, 1] if allow_parallel else [0]
        for parallel in parallel_values:
            # Avoid unrealistic expensive duplication for low-staff options unless it is the only way to meet target.
            options.append({"workers": workers, "parallel": parallel})
    return options


def _solve_with_pulp(
    target_daily_output: float,
    target_annual_output: float,
    station_times: Dict[str, float],
    current_workers: Dict[str, int],
    station_min_workers: Dict[str, int],
    station_skill: Dict[str, str],
    settings: SolverSettings,
    objective: str,
    monthly_rates: Optional[Dict[str, float]] = None,
) -> Optional[dict]:
    try:
        import pulp
    except Exception:
        return None

    model = pulp.LpProblem("VoltRides_Production_Optimization", pulp.LpMinimize)
    station_option_vars = {}

    weights = _objective_weights(objective)
    cost_terms = []
    worker_terms = []
    capex_terms = []
    selected_option_records = {}

    for station, base_time in station_times.items():
        min_w = int(station_min_workers.get(station, 1))
        opts = _candidate_worker_options(station, min_w, settings.max_workers_per_station, settings.allow_parallel_stations)
        selected_option_records[station] = []
        option_vars = []
        for idx, option in enumerate(opts):
            var = pulp.LpVariable(f"x_{station}_{idx}", cat="Binary")
            option_vars.append(var)
            station_option_vars[(station, idx)] = var

            workers = int(option["workers"])
            parallel = int(option["parallel"])
            effective_time = float(base_time) / workers / (1 + parallel)
            added_workers = max(0, workers - int(current_workers.get(station, 1)))
            skill = station_skill.get(station, "Semi-skilled")
            labour_cost = added_workers * annual_rate_for_skill(skill, monthly_rates)
            capex_cost = parallel * settings.parallel_station_capex / max(1, settings.capex_annualization_years)

            selected_option_records[station].append({
                "idx": idx,
                "workers": workers,
                "parallel": parallel,
                "effective_time": effective_time,
                "added_workers": added_workers,
                "annual_labour_delta": labour_cost,
                "annualized_capex": capex_cost,
                "area_sqft": parallel * settings.parallel_station_area_sqft,
            })
            cost_terms.append(labour_cost * var)
            worker_terms.append(added_workers * var)
            capex_terms.append(capex_cost * var)
        model += pulp.lpSum(option_vars) == 1, f"choose_one_option_{station}"

    shift_vars = {}
    for shifts in range(1, settings.max_shifts_per_day + 1):
        shift_vars[shifts] = pulp.LpVariable(f"shift_{shifts}", cat="Binary")
    model += pulp.lpSum(shift_vars.values()) == 1, "choose_one_shift_count"

    overtime_options = list(range(0, settings.max_overtime_minutes_per_day + 1, 30))
    overtime_vars = {m: pulp.LpVariable(f"ot_{m}", cat="Binary") for m in overtime_options}
    model += pulp.lpSum(overtime_vars.values()) == 1, "choose_overtime"

    available_minutes_expr = (
        pulp.lpSum([(SHIFT_MINUTES * s * settings.uptime) * v for s, v in shift_vars.items()])
        + pulp.lpSum([m * v for m, v in overtime_vars.items()])
    )

    # Capacity feasibility: daily demand multiplied by every selected station time must fit into daily available minutes.
    for station in station_times:
        effective_time_expr = pulp.lpSum([
            selected_option_records[station][idx]["effective_time"] * station_option_vars[(station, idx)]
            for idx in range(len(selected_option_records[station]))
        ])
        model += target_daily_output * effective_time_expr <= available_minutes_expr, f"capacity_{station}"

    # Space feasibility for added parallel stations.
    parallel_expr = pulp.lpSum([
        rec["parallel"] * station_option_vars[(station, rec["idx"])]
        for station, records in selected_option_records.items()
        for rec in records
    ])
    model += pulp.lpSum([
        rec["area_sqft"] * station_option_vars[(station, rec["idx"])]
        for station, records in selected_option_records.items()
        for rec in records
    ]) <= settings.available_expansion_area_sqft, "expansion_area"
    model += parallel_expr <= settings.max_parallel_stations, "max_parallel_stations"

    # Use a soft utilization term. Lower objective means less over-capacity in utilization mode.
    # We approximate by penalizing extra shifts and overtime when utilization is the objective.
    shift_cost_terms = []
    for shifts, var in shift_vars.items():
        shift_cost_terms.append(max(0, shifts - 1) * 3_500_000 * var)
    overtime_cost_terms = []
    for minutes, var in overtime_vars.items():
        overtime_cost_terms.append(minutes * WORKING_DAYS_YEAR * 120 * var)

    model += (
        weights["cost"] * (pulp.lpSum(cost_terms) + pulp.lpSum(shift_cost_terms) + pulp.lpSum(overtime_cost_terms))
        + weights["workers"] * pulp.lpSum(worker_terms)
        + weights["capex"] * pulp.lpSum(capex_terms)
        + weights["utilization"] * (pulp.lpSum([(s - 1) * v for s, v in shift_vars.items()]) + pulp.lpSum([m / 30 * v for m, v in overtime_vars.items()]))
    )

    solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=8)
    model.solve(solver)
    status = pulp.LpStatus.get(model.status, "Unknown")
    if status not in {"Optimal", "Feasible"}:
        return {"feasible": False, "status": status, "reason": "No feasible MILP solution under selected constraints."}

    selected_workers = {}
    selected_parallel = {}
    selected_rows = []
    annual_labour_delta = 0.0
    annualized_capex = 0.0
    added_workers = 0
    expansion_area = 0.0

    for station, records in selected_option_records.items():
        for rec in records:
            val = pulp.value(station_option_vars[(station, rec["idx"])])
            if val and val > 0.5:
                selected_workers[station] = int(rec["workers"])
                selected_parallel[station] = int(rec["parallel"])
                annual_labour_delta += rec["annual_labour_delta"]
                annualized_capex += rec["annualized_capex"]
                added_workers += int(rec["added_workers"])
                expansion_area += rec["area_sqft"]
                selected_rows.append({"Station": station, **{k: v for k, v in rec.items() if k != "idx"}})
                break

    selected_shifts = next((s for s, v in shift_vars.items() if pulp.value(v) and pulp.value(v) > 0.5), 1)
    selected_overtime = next((m for m, v in overtime_vars.items() if pulp.value(v) and pulp.value(v) > 0.5), 0)
    overtime_cost = estimate_overtime_cost(sum(selected_workers.values()), selected_overtime, WORKING_DAYS_YEAR, monthly_rates)

    balance = calculate_line_balance(station_times, selected_workers, selected_parallel)
    capacity = calculate_capacity(balance["cycle_time"], SHIFT_MINUTES, selected_shifts, WORKING_DAYS_YEAR, settings.uptime, selected_overtime)

    return {
        "feasible": True,
        "status": status,
        "workers": selected_workers,
        "parallel": selected_parallel,
        "shifts": selected_shifts,
        "overtime_minutes": selected_overtime,
        "annual_labour_delta": annual_labour_delta,
        "annualized_capex": annualized_capex,
        "overtime_cost": overtime_cost,
        "added_workers": added_workers,
        "expansion_area_sqft": expansion_area,
        "balance": balance,
        "capacity": capacity,
        "selected_options": pd.DataFrame(selected_rows),
    }


def _greedy_fallback(
    target_daily_output: float,
    station_times: Dict[str, float],
    current_workers: Dict[str, int],
    station_min_workers: Dict[str, int],
    settings: SolverSettings,
) -> dict:
    """Fallback when PuLP is unavailable locally.

    It is intentionally conservative: increase workers to meet one-shift takt, then add
    overtime/extra shift if required.
    """
    workers = {s: max(int(current_workers.get(s, 1)), int(station_min_workers.get(s, 1))) for s in station_times}
    parallel = {s: 0 for s in station_times}
    shifts = 1
    overtime = 0

    while shifts <= settings.max_shifts_per_day:
        available = SHIFT_MINUTES * shifts * settings.uptime + overtime
        takt = available / target_daily_output if target_daily_output else 9999
        changed = False
        for station, base_time in station_times.items():
            while float(base_time) / workers[station] / (1 + parallel[station]) > takt and workers[station] < settings.max_workers_per_station:
                workers[station] += 1
                changed = True
            if float(base_time) / workers[station] / (1 + parallel[station]) > takt and settings.allow_parallel_stations and parallel[station] == 0:
                parallel[station] = 1
                changed = True
        balance = calculate_line_balance(station_times, workers, parallel)
        capacity = calculate_capacity(balance["cycle_time"], SHIFT_MINUTES, shifts, WORKING_DAYS_YEAR, settings.uptime, overtime)
        if capacity["annual_capacity"] >= target_daily_output * WORKING_DAYS_YEAR:
            added = sum(max(0, workers[s] - current_workers.get(s, 1)) for s in workers)
            return {
                "feasible": True,
                "status": "Greedy fallback",
                "workers": workers,
                "parallel": parallel,
                "shifts": shifts,
                "overtime_minutes": overtime,
                "annual_labour_delta": 0.0,
                "annualized_capex": sum(parallel.values()) * settings.parallel_station_capex / settings.capex_annualization_years,
                "overtime_cost": 0.0,
                "added_workers": added,
                "expansion_area_sqft": sum(parallel.values()) * settings.parallel_station_area_sqft,
                "balance": balance,
                "capacity": capacity,
                "selected_options": pd.DataFrame(),
            }
        if overtime < settings.max_overtime_minutes_per_day:
            overtime += 30
        else:
            shifts += 1
            overtime = 0
        if not changed and shifts > settings.max_shifts_per_day:
            break
    return {"feasible": False, "status": "Infeasible", "reason": "No fallback solution under selected worker, shift, and overtime limits."}


def solve_capacity_optimization(
    target_daily_output: float,
    target_annual_output: float,
    station_times: Dict[str, float],
    current_workers: Dict[str, int],
    station_min_workers: Dict[str, int],
    station_skill: Dict[str, str],
    settings: SolverSettings,
    objective: str,
    monthly_rates: Optional[Dict[str, float]] = None,
) -> dict:
    result = _solve_with_pulp(
        target_daily_output=target_daily_output,
        target_annual_output=target_annual_output,
        station_times=station_times,
        current_workers=current_workers,
        station_min_workers=station_min_workers,
        station_skill=station_skill,
        settings=settings,
        objective=objective,
        monthly_rates=monthly_rates,
    )
    if result is None:
        result = _greedy_fallback(target_daily_output, station_times, current_workers, station_min_workers, settings)
    return result
