from __future__ import annotations

from typing import Dict

import pandas as pd

from src.config import DEFAULT_MONTHLY_SKILL_RATES, DEFAULT_OVERTIME_PREMIUM


def normalise_skill(skill: str | None) -> str:
    text = str(skill or "Semi-skilled").strip().lower()
    if "senior" in text:
        return "Senior"
    if "professional" in text or "engineer" in text or "manager" in text:
        return "Professional"
    if "supervisor" in text:
        return "Supervisor"
    if "semi" in text:
        return "Semi-skilled"
    if "unskilled" in text or "helper" in text:
        return "Unskilled"
    if "skill" in text:
        return "Skilled"
    return "Semi-skilled"


def skill_rate_map(user_rates: Dict[str, float] | None = None) -> Dict[str, float]:
    rates = DEFAULT_MONTHLY_SKILL_RATES.copy()
    if user_rates:
        rates.update({k: float(v) for k, v in user_rates.items()})
    return rates


def annual_rate_for_skill(skill: str | None, monthly_rates: Dict[str, float] | None = None) -> float:
    rates = skill_rate_map(monthly_rates)
    return float(rates.get(normalise_skill(skill), rates["Semi-skilled"])) * 12


def estimate_station_labour_delta(
    current_workers: Dict[str, int],
    proposed_workers: Dict[str, int],
    station_skill: Dict[str, str],
    monthly_rates: Dict[str, float] | None = None,
) -> Dict[str, float]:
    rows = []
    added_workers = 0
    annual_delta = 0.0
    for station, proposed in proposed_workers.items():
        current = int(current_workers.get(station, 1))
        add = max(0, int(proposed) - current)
        skill = normalise_skill(station_skill.get(station, "Semi-skilled"))
        annual_rate = annual_rate_for_skill(skill, monthly_rates)
        cost = add * annual_rate
        added_workers += add
        annual_delta += cost
        rows.append({
            "Station": station,
            "Current Workers": current,
            "Recommended Workers": int(proposed),
            "Added Workers": add,
            "Skill": skill,
            "Annual Labour Delta": cost,
        })
    return {"added_workers": added_workers, "annual_labour_delta": annual_delta, "breakdown": pd.DataFrame(rows)}


def estimate_overtime_cost(
    total_station_workers: int,
    overtime_minutes_per_day: int,
    working_days: int,
    monthly_rates: Dict[str, float] | None = None,
    premium: float = DEFAULT_OVERTIME_PREMIUM,
) -> float:
    rates = skill_rate_map(monthly_rates)
    # Conservative blended hourly rate using semi-skilled salary.
    monthly = rates["Semi-skilled"]
    hourly_rate = monthly / 26 / 8
    return total_station_workers * (overtime_minutes_per_day / 60) * working_days * hourly_rate * premium


def labour_summary(labour_df: pd.DataFrame, annual_target: float) -> dict:
    if labour_df is None or labour_df.empty:
        return {"monthly_cost": 0.0, "annual_cost": 0.0, "cost_per_bike": 0.0, "headcount": 0}
    monthly = float(labour_df.get("monthly_cost_pkr", pd.Series(dtype=float)).sum())
    annual = float(labour_df.get("annual_cost_pkr", pd.Series(dtype=float)).sum())
    count = int(labour_df.get("count", pd.Series(dtype=float)).sum())
    per_bike = annual / annual_target if annual_target else 0.0
    return {"monthly_cost": monthly, "annual_cost": annual, "cost_per_bike": per_bike, "headcount": count}
