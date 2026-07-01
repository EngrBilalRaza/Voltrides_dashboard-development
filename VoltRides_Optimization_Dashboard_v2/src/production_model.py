from __future__ import annotations

import math
from typing import Dict

import pandas as pd

from src.config import SHIFT_MINUTES, WORKING_DAYS_MONTH, WORKING_DAYS_YEAR


def normalize_target(
    target_units: float,
    target_period: str,
    working_days_year: int = WORKING_DAYS_YEAR,
    working_days_month: int = WORKING_DAYS_MONTH,
) -> Dict[str, float]:
    target_period = str(target_period).lower()
    if "year" in target_period:
        annual_target = float(target_units)
        monthly_target = annual_target / 12
        daily_target = annual_target / working_days_year
    elif "month" in target_period:
        monthly_target = float(target_units)
        annual_target = monthly_target * 12
        daily_target = monthly_target / working_days_month
    elif "day" in target_period:
        daily_target = float(target_units)
        monthly_target = daily_target * working_days_month
        annual_target = daily_target * working_days_year
    else:  # per shift
        daily_target = float(target_units)
        monthly_target = daily_target * working_days_month
        annual_target = daily_target * working_days_year
    return {"annual_target": annual_target, "monthly_target": monthly_target, "daily_target": daily_target}


def available_minutes_per_day(shift_minutes: float, shifts_per_day: int, uptime: float, overtime_minutes_per_day: int = 0) -> float:
    return (shift_minutes * shifts_per_day * uptime) + overtime_minutes_per_day


def calculate_required_takt(daily_target: float, shift_minutes: float, shifts_per_day: int, uptime: float, overtime_minutes_per_day: int = 0) -> float:
    if daily_target <= 0:
        return math.inf
    return available_minutes_per_day(shift_minutes, shifts_per_day, uptime, overtime_minutes_per_day) / daily_target


def effective_station_times(station_times: Dict[str, float], station_workers: Dict[str, int], station_parallel: Dict[str, int] | None = None) -> Dict[str, float]:
    station_parallel = station_parallel or {}
    output = {}
    for station, base_time in station_times.items():
        workers = max(1, int(station_workers.get(station, 1)))
        parallel_factor = 1 + max(0, int(station_parallel.get(station, 0)))
        output[station] = float(base_time) / workers / parallel_factor
    return output


def calculate_line_balance(
    station_times: Dict[str, float],
    station_workers: Dict[str, int],
    station_parallel: Dict[str, int] | None = None,
) -> Dict[str, object]:
    eff = effective_station_times(station_times, station_workers, station_parallel)
    if not eff:
        return {"effective_times": {}, "cycle_time": 0.0, "bottlenecks": [], "line_efficiency_pct": 0.0}
    cycle_time = max(eff.values())
    bottlenecks = [s for s, v in eff.items() if abs(v - cycle_time) < 1e-9]
    total_work = sum(eff.values())
    efficiency = total_work / (len(eff) * cycle_time) * 100 if cycle_time else 0.0
    return {"effective_times": eff, "cycle_time": cycle_time, "bottlenecks": bottlenecks, "line_efficiency_pct": efficiency}


def calculate_capacity(
    cycle_time: float,
    shift_minutes: float = SHIFT_MINUTES,
    shifts_per_day: int = 1,
    working_days: int = WORKING_DAYS_YEAR,
    uptime: float = 0.9,
    overtime_minutes_per_day: int = 0,
) -> Dict[str, float]:
    if cycle_time <= 0:
        return {"daily_capacity": 0.0, "annual_capacity": 0.0, "available_minutes": 0.0}
    available = available_minutes_per_day(shift_minutes, shifts_per_day, uptime, overtime_minutes_per_day)
    daily_capacity = math.floor(available / cycle_time)
    return {"daily_capacity": daily_capacity, "annual_capacity": daily_capacity * working_days, "available_minutes": available}


def required_workers_by_station(
    station_times: Dict[str, float],
    required_takt: float,
    min_workers: Dict[str, int] | None = None,
    max_workers: int = 4,
) -> pd.DataFrame:
    min_workers = min_workers or {}
    rows = []
    for station, base_time in station_times.items():
        raw_needed = math.ceil(float(base_time) / required_takt) if required_takt > 0 else max_workers + 1
        minimum = int(min_workers.get(station, 1))
        needed = max(raw_needed, minimum)
        recommended = min(needed, max_workers)
        rows.append({
            "Station": station,
            "Base Time": float(base_time),
            "Required Takt": required_takt,
            "Required Workers": needed,
            "Recommended Workers": recommended,
            "Feasible With Worker Cap": needed <= max_workers,
        })
    return pd.DataFrame(rows)


def station_balance_dataframe(
    station_times: Dict[str, float],
    station_workers: Dict[str, int],
    station_type: Dict[str, str],
    required_takt: float,
    station_parallel: Dict[str, int] | None = None,
) -> pd.DataFrame:
    eff = effective_station_times(station_times, station_workers, station_parallel)
    rows = []
    for station, value in eff.items():
        rows.append({
            "Station": station,
            "Type": station_type.get(station, "Station"),
            "Base Time": station_times[station],
            "Workers": station_workers.get(station, 1),
            "Parallel Stations": station_parallel.get(station, 0) if station_parallel else 0,
            "Effective Time": value,
            "Takt Gap": required_takt - value,
            "Status": "Above takt" if value > required_takt else "Within takt",
        })
    return pd.DataFrame(rows).sort_values(["Status", "Effective Time"], ascending=[True, False])


def worker_loads(main_assembly_df: pd.DataFrame, station_times: Dict[str, float]) -> Dict[str, float]:
    loads: Dict[str, float] = {}
    if main_assembly_df is None or main_assembly_df.empty or "worker_tag" not in main_assembly_df.columns:
        return loads
    for _, row in main_assembly_df.iterrows():
        tag = str(row.get("worker_tag", "Unassigned") or "Unassigned")
        station = row.get("station")
        loads[tag] = loads.get(tag, 0.0) + float(station_times.get(station, 0.0))
    return loads
