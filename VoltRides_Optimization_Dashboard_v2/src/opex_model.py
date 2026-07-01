from __future__ import annotations

from typing import Tuple

import pandas as pd

from src.config import BASE_ANNUAL_OUTPUT, BASE_SCRAP_RATE, BASE_SHIFTS_PER_DAY, DEFAULT_EXTRA_SHIFT_FIXED_OPEX


def classify_opex_line(cost_line: str, basis: str = "") -> str:
    text = f"{cost_line} {basis}".lower()
    if any(x in text for x in ["rent", "lease", "it", "telecom", "software", "office"]):
        return "fixed"
    if any(x in text for x in ["electricity", "gas", "fuel", "water", "power"]):
        return "hour_driven"
    if any(x in text for x in ["paint", "chemical", "welding", "packaging", "dispatch", "freight", "clearing", "consumable"]):
        return "unit_variable"
    if any(x in text for x in ["maintenance", "spares", "insurance"]):
        return "capex_linked"
    if any(x in text for x in ["scrap", "rework", "defect"]):
        return "quality_variable"
    return "semi_fixed"


def prepare_opex(opex_df: pd.DataFrame) -> pd.DataFrame:
    df = opex_df.copy()
    if df.empty:
        return pd.DataFrame(columns=["cost_line", "annual_pkr", "basis", "note", "cost_type", "cost_driver", "optimization_lever"])
    if "cost_type" not in df.columns:
        df["cost_type"] = df.apply(lambda r: classify_opex_line(r.get("cost_line", ""), r.get("basis", "")), axis=1)
    df["cost_driver"] = df["cost_type"].map({
        "fixed": "time / facility",
        "unit_variable": "units produced",
        "hour_driven": "running hours",
        "capex_linked": "equipment value",
        "quality_variable": "defect / rework rate",
        "semi_fixed": "step threshold",
    }).fillna("mixed")
    df["optimization_lever"] = df["cost_type"].map({
        "fixed": "increase utilization, avoid excess floor area",
        "unit_variable": "vendor negotiation, usage standardization",
        "hour_driven": "batching, uptime, tariff control, shutdown discipline",
        "capex_linked": "preventive maintenance, equipment reliability",
        "quality_variable": "first-pass yield, process control, operator training",
        "semi_fixed": "avoid premature step-cost expansion",
    }).fillna("review cost driver")
    return df


def calculate_opex(
    opex_df: pd.DataFrame,
    target_annual_output: float,
    base_annual_output: float = BASE_ANNUAL_OUTPUT,
    shifts_per_day: int = 1,
    base_shifts_per_day: int = BASE_SHIFTS_PER_DAY,
    overtime_minutes_per_day: int = 0,
    scrap_rate: float = BASE_SCRAP_RATE,
    base_scrap_rate: float = BASE_SCRAP_RATE,
    energy_escalation_pct: float = 0.0,
    miscellaneous_cost_pct: float = 0.0,
    extra_shift_fixed_opex: float = DEFAULT_EXTRA_SHIFT_FIXED_OPEX,
) -> Tuple[float, pd.DataFrame]:
    df = prepare_opex(opex_df)
    if df.empty:
        return 0.0, pd.DataFrame()

    output_factor = target_annual_output / base_annual_output if base_annual_output else 1.0
    running_hours_factor = (shifts_per_day / base_shifts_per_day if base_shifts_per_day else 1.0) + (overtime_minutes_per_day / 480)
    scrap_factor = scrap_rate / base_scrap_rate if base_scrap_rate else 1.0
    energy_factor = 1 + energy_escalation_pct

    rows = []
    total = 0.0
    for _, row in df.iterrows():
        base_cost = float(row.get("annual_pkr", 0) or 0)
        cost_type = str(row.get("cost_type", "semi_fixed"))
        if cost_type == "fixed":
            optimized_cost = base_cost
        elif cost_type == "unit_variable":
            optimized_cost = base_cost * output_factor
        elif cost_type == "hour_driven":
            optimized_cost = base_cost * running_hours_factor * energy_factor
        elif cost_type == "quality_variable":
            optimized_cost = base_cost * output_factor * scrap_factor
        elif cost_type == "capex_linked":
            optimized_cost = base_cost
        else:
            if output_factor <= 1.00:
                optimized_cost = base_cost
            elif output_factor <= 1.25:
                optimized_cost = base_cost * 1.10
            elif output_factor <= 1.75:
                optimized_cost = base_cost * 1.25
            else:
                optimized_cost = base_cost * 1.50
        total += optimized_cost
        rows.append({
            "Cost Line": row.get("cost_line", ""),
            "Cost Type": cost_type,
            "Cost Driver": row.get("cost_driver", "mixed"),
            "Optimization Lever": row.get("optimization_lever", "review"),
            "Base Annual Cost": base_cost,
            "Optimized Annual Cost": optimized_cost,
            "Change": optimized_cost - base_cost,
        })

    # Add incremental shift-support burden as a separate line so management can see the penalty.
    if shifts_per_day > base_shifts_per_day:
        shift_delta = (shifts_per_day - base_shifts_per_day) * extra_shift_fixed_opex
        total += shift_delta
        rows.append({
            "Cost Line": "Incremental additional shift support",
            "Cost Type": "semi_fixed",
            "Cost Driver": "extra shift",
            "Optimization Lever": "avoid extra shift unless target requires it",
            "Base Annual Cost": 0.0,
            "Optimized Annual Cost": shift_delta,
            "Change": shift_delta,
        })


    # Add a user-controlled miscellaneous allowance as a transparent OPEX line.
    # The percentage is applied to the optimized OPEX subtotal after cost-driver scaling
    # and shift-support burden, so management can model unknown/contingency expenses.
    if miscellaneous_cost_pct:
        misc_pct = max(0.0, float(miscellaneous_cost_pct))
        misc_cost = total * misc_pct
        total += misc_cost
        rows.append({
            "Cost Line": "Miscellaneous cost allowance",
            "Cost Type": "miscellaneous",
            "Cost Driver": "percentage allowance",
            "Optimization Lever": "review and convert recurring miscellaneous costs into named cost drivers",
            "Base Annual Cost": 0.0,
            "Optimized Annual Cost": misc_cost,
            "Change": misc_cost,
        })

    out = pd.DataFrame(rows).sort_values("Optimized Annual Cost", ascending=False)
    return total, out


def opex_driver_summary(opex_breakdown: pd.DataFrame) -> pd.DataFrame:
    if opex_breakdown is None or opex_breakdown.empty:
        return pd.DataFrame(columns=["Cost Type", "Optimized Annual Cost", "Share %"])
    df = opex_breakdown.groupby("Cost Type", as_index=False)["Optimized Annual Cost"].sum()
    total = df["Optimized Annual Cost"].sum()
    df["Share %"] = df["Optimized Annual Cost"] / total * 100 if total else 0
    return df.sort_values("Optimized Annual Cost", ascending=False)
