from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from src.optimizer import run_optimization
from src.production_model import normalize_target


def target_sensitivity(
    base_target_units: float,
    target_period: str,
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
    miscellaneous_cost_pct: float = 0.0,
    base_labour_annual: float = 0.0,
) -> pd.DataFrame:
    multipliers = [0.7, 0.85, 1.0, 1.15, 1.3, 1.5]
    rows = []
    for m in multipliers:
        units = max(1, base_target_units * m)
        target = normalize_target(units, target_period)
        best, _, _, _ = run_optimization(
            target=target,
            station_times=station_times,
            current_workers=current_workers,
            station_min_workers=station_min_workers,
            station_skill=station_skill,
            station_type=station_type,
            opex_df=opex_df,
            objective=objective,
            uptime=uptime,
            max_workers_per_station=max_workers_per_station,
            max_shifts_per_day=max_shifts_per_day,
            max_overtime_minutes_per_day=max_overtime_minutes_per_day,
            scrap_rate=scrap_rate,
            allow_parallel_stations=allow_parallel_stations,
            available_expansion_area_sqft=available_expansion_area_sqft,
            monthly_rates=monthly_rates,
            energy_escalation_pct=energy_escalation_pct,
            miscellaneous_cost_pct=miscellaneous_cost_pct,
            base_labour_annual=base_labour_annual,
        )
        rows.append({
            "Target Units": units,
            "Annual Target": target["annual_target"],
            "Feasible": bool(best),
            "Operating Cost / Bike": best.get("Operating Cost per Bike", 0) if best else 0,
            "OPEX / Bike": best.get("OPEX per Bike", 0) if best else 0,
            "Shifts": best.get("Required Shifts", 0) if best else 0,
            "Added Workers": best.get("Added Workers", 0) if best else 0,
            "Parallel Stations": best.get("Parallel Stations Added", 0) if best else 0,
            "Risk Level": best.get("Risk Level", "High") if best else "High",
        })
    return pd.DataFrame(rows)


def driver_sensitivity(best: dict | None, base_scrap_rate: float, base_uptime: float) -> pd.DataFrame:
    if not best:
        return pd.DataFrame(columns=["Driver", "Low Case", "Base Case", "High Case", "Management Reading"])
    base_cost = float(best.get("Operating Cost per Bike", 0))
    rows = [
        {
            "Driver": "Uptime",
            "Low Case": f"{max(0, base_uptime - 0.10):.0%}",
            "Base Case": f"{base_uptime:.0%}",
            "High Case": f"{min(1, base_uptime + 0.05):.0%}",
            "Management Reading": "Lower uptime reduces capacity and can push the model into overtime or extra shift.",
        },
        {
            "Driver": "Scrap / rework",
            "Low Case": f"{max(0, base_scrap_rate - 0.01):.1%}",
            "Base Case": f"{base_scrap_rate:.1%}",
            "High Case": f"{base_scrap_rate + 0.03:.1%}",
            "Management Reading": "Higher scrap directly increases quality-variable OPEX and can hide true capacity loss.",
        },
        {
            "Driver": "Target volume",
            "Low Case": "-15%",
            "Base Case": "Selected target",
            "High Case": "+30%",
            "Management Reading": f"At base case, operating cost is about PKR {base_cost:,.0f}/bike.",
        },
    ]
    return pd.DataFrame(rows)
