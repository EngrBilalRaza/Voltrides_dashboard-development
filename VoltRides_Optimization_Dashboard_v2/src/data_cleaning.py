from __future__ import annotations

import re
from typing import Any, Dict

import numpy as np
import pandas as pd

from src.config import DEFAULT_MA_TIMES, DEFAULT_SA_TIMES, SA10_MIN_WORKERS


def _slug(value: Any) -> str:
    value = "" if pd.isna(value) else str(value).strip()
    value = value.replace("%", "percent")
    value = re.sub(r"[^0-9a-zA-Z]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_").lower()
    return value or "unnamed"


def _find_header_row(raw_df: pd.DataFrame, required_tokens: list[str], fallback: int = 4) -> int:
    """Find likely header row by matching required header tokens."""
    tokens = {t.lower() for t in required_tokens}
    for idx in range(min(len(raw_df), 40)):
        row_tokens = {_slug(x) for x in raw_df.iloc[idx].tolist() if pd.notna(x)}
        if len(tokens.intersection(row_tokens)) >= max(1, min(len(tokens), 2)):
            return idx
    return fallback


def _table_from_header(raw_df: pd.DataFrame, header_row: int) -> pd.DataFrame:
    headers = [_slug(x) for x in raw_df.iloc[header_row].tolist()]
    df = raw_df.iloc[header_row + 1 :].copy()
    df.columns = headers
    df = df.dropna(how="all")
    # Keep duplicate unnamed columns out.
    keep_cols = []
    seen = set()
    for col in df.columns:
        if col.startswith("unnamed"):
            continue
        new_col = col
        counter = 2
        while new_col in seen:
            new_col = f"{col}_{counter}"
            counter += 1
        seen.add(new_col)
        keep_cols.append((col, new_col))
    df = df[[old for old, _ in keep_cols]]
    df.columns = [new for _, new in keep_cols]
    return df.reset_index(drop=True)


def _numeric(series: pd.Series | Any, default: float = 0.0) -> pd.Series:
    if not isinstance(series, pd.Series):
        series = pd.Series(dtype=float)
    return pd.to_numeric(series, errors="coerce").fillna(default)


def extract_summary_metrics(raw: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    sheet = raw.get("1. Cover & Summary", pd.DataFrame())
    metrics: Dict[str, Any] = {}
    for _, row in sheet.iterrows():
        cells = row.tolist()
        for idx in range(0, max(0, len(cells) - 1)):
            key = cells[idx]
            val = cells[idx + 1] if idx + 1 < len(cells) else None
            if pd.notna(key) and pd.notna(val) and str(key).strip():
                slug = _slug(key)
                if slug not in metrics:
                    metrics[slug] = val
    return metrics


def clean_space_schedule(raw: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    source = raw.get("3. Space Schedule", pd.DataFrame())
    header = _find_header_row(source, ["zone", "area_sq_ft"], 4)
    df = _table_from_header(source, header)
    df = df.rename(columns={
        "zone": "zone",
        "length_ft": "length_ft",
        "width_ft": "width_ft",
        "area_sq_ft": "area_sqft",
        "area_sqft": "area_sqft",
        "percent_of_building": "pct_building",
        "notes": "notes",
    })
    if "zone" not in df.columns:
        return pd.DataFrame(columns=["zone", "area_sqft", "pct_building", "notes"])
    df = df.dropna(subset=["zone"]).copy()
    df = df[df["zone"].astype(str).str.strip() != ""]
    if "area_sqft" not in df.columns:
        df["area_sqft"] = 0
    df["area_sqft"] = _numeric(df["area_sqft"])
    if "pct_building" not in df.columns:
        total = df["area_sqft"].sum()
        df["pct_building"] = np.where(total > 0, df["area_sqft"] / total, 0)
    else:
        df["pct_building"] = _numeric(df["pct_building"])
    if "notes" not in df.columns:
        df["notes"] = ""
    return df[["zone", "area_sqft", "pct_building", "notes"]].reset_index(drop=True)


def clean_sub_assemblies(raw: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    source = raw.get("4. Sub-Assemblies", pd.DataFrame())
    header = _find_header_row(source, ["station", "feeds_into", "headcount"], 4)
    df = _table_from_header(source, header)
    df = df.rename(columns={
        "station": "station",
        "description": "description",
        "sub_assembly": "description",
        "feeds_into": "feeds_into",
        "feeds": "feeds_into",
        "skill_level": "skill_level",
        "headcount": "workers",
        "count": "workers",
        "notes": "notes",
    })
    if "station" not in df.columns:
        return pd.DataFrame(columns=["station", "description", "feeds_into", "skill_level", "workers", "notes", "base_time_min", "safety_critical", "min_workers", "type"])
    df = df[df["station"].astype(str).str.match(r"^SA-\d+", na=False)].copy()
    for col in ["description", "feeds_into", "skill_level", "notes"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype(str).str.strip()
    df["station"] = df["station"].astype(str).str.strip()
    if "workers" not in df.columns:
        df["workers"] = 1
    df["workers"] = _numeric(df["workers"], default=1).astype(int)
    df["base_time_min"] = df["station"].map(DEFAULT_SA_TIMES).fillna(24.0).astype(float)
    df["safety_critical"] = df["station"].eq("SA-10") | df["notes"].astype(str).str.contains("Safety|critical|★|never", case=False, na=False)
    df["min_workers"] = np.where(df["station"].eq("SA-10"), SA10_MIN_WORKERS, 1).astype(int)
    df["workers"] = np.maximum(df["workers"], df["min_workers"])
    df["type"] = "SA"
    return df.reset_index(drop=True)


def clean_main_assembly(raw: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    source = raw.get("5. Main Assembly Line", pd.DataFrame())
    header = _find_header_row(source, ["station", "operations", "worker_tag"], 4)
    df = _table_from_header(source, header)
    df = df.rename(columns={
        "station": "station",
        "operations": "operations",
        "operation": "operations",
        "skill_level": "skill_level",
        "receives_from_sa": "receives_from_sa",
        "worker_tag": "worker_tag",
        "notes": "notes",
    })
    if "station" not in df.columns:
        return pd.DataFrame(columns=["station", "operations", "skill_level", "receives_from_sa", "worker_tag", "notes", "base_time_min", "workers", "min_workers", "type"])
    df = df[df["station"].astype(str).str.match(r"^MA-\d+", na=False)].copy()
    for col in ["operations", "skill_level", "receives_from_sa", "worker_tag", "notes"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype(str).str.strip()
    df["station"] = df["station"].astype(str).str.strip()
    df["base_time_min"] = df["station"].map(DEFAULT_MA_TIMES).fillna(10.0).astype(float)
    df["workers"] = 1
    df["min_workers"] = 1
    df["type"] = "MA"
    return df.reset_index(drop=True)


def clean_headcount(raw: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    source = raw.get("6. Headcount", pd.DataFrame())
    header = _find_header_row(source, ["section", "role_station", "count"], 4)
    df = _table_from_header(source, header)
    df = df.rename(columns={
        "section": "section",
        "role_station": "role_station",
        "role": "role_station",
        "skill_level": "skill_level",
        "count": "count",
        "notes": "notes",
    })
    if "count" not in df.columns:
        return pd.DataFrame(columns=["section", "role_station", "skill_level", "count", "notes"])
    df["count"] = pd.to_numeric(df["count"], errors="coerce")
    df = df.dropna(subset=["count"]).copy()
    df["count"] = df["count"].astype(int)
    for col in ["section", "role_station", "skill_level", "notes"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype(str).str.strip()
    return df.reset_index(drop=True)


def clean_labour_cost(raw: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    source = raw.get("7. Labour Cost", pd.DataFrame())
    header = _find_header_row(source, ["role_station", "monthly_cost_pkr", "monthly_rate_pkr"], 25)
    df = _table_from_header(source, header)
    df = df.rename(columns={
        "role_station": "role_station",
        "role": "role_station",
        "skill": "skill",
        "skill_level": "skill",
        "count": "count",
        "monthly_rate_pkr": "monthly_rate_pkr",
        "monthly_cost_pkr": "monthly_cost_pkr",
        "notes": "notes",
    })
    if "count" not in df.columns:
        return pd.DataFrame(columns=["role_station", "skill", "count", "monthly_rate_pkr", "monthly_cost_pkr", "annual_cost_pkr", "notes"])
    df = df[pd.to_numeric(df["count"], errors="coerce").notna()].copy()
    df["count"] = _numeric(df["count"]).astype(int)
    df["monthly_rate_pkr"] = _numeric(df.get("monthly_rate_pkr", pd.Series(dtype=float)))
    df["monthly_cost_pkr"] = _numeric(df.get("monthly_cost_pkr", pd.Series(dtype=float)))
    if df["monthly_cost_pkr"].sum() == 0 and df["monthly_rate_pkr"].sum() > 0:
        df["monthly_cost_pkr"] = df["monthly_rate_pkr"] * df["count"]
    df["annual_cost_pkr"] = df["monthly_cost_pkr"] * 12
    for col in ["role_station", "skill", "notes"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype(str).str.strip()
    return df.reset_index(drop=True)


def clean_capex_summary(raw: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    source = raw.get("10. CapEx Summary", pd.DataFrame())
    header = _find_header_row(source, ["category", "amount_pkr"], 4)
    df = _table_from_header(source, header)
    df = df.rename(columns={
        "category": "category",
        "amount_pkr": "amount_pkr",
        "percent_of_total": "pct_total",
        "notes": "notes",
    })
    if "category" not in df.columns:
        return pd.DataFrame(columns=["category", "amount_pkr", "pct_total", "notes"])
    df = df.dropna(subset=["category"]).copy()
    df["amount_pkr"] = _numeric(df.get("amount_pkr", pd.Series(dtype=float)))
    df["pct_total"] = _numeric(df.get("pct_total", pd.Series(dtype=float)))
    if "notes" not in df.columns:
        df["notes"] = ""
    return df[["category", "amount_pkr", "pct_total", "notes"]].reset_index(drop=True)


def clean_assumptions(raw: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    sheet = raw.get("11. Assumptions & Notes", pd.DataFrame()).copy()
    rows = []
    current_section = "General"
    for _, row in sheet.iterrows():
        vals = [x for x in row.tolist() if pd.notna(x) and str(x).strip()]
        if not vals:
            continue
        if len(vals) == 1 and str(vals[0]).strip().isupper():
            current_section = str(vals[0]).strip()
            continue
        if len(vals) >= 2:
            rows.append({"section": current_section, "item": vals[0], "value": vals[1], "note": vals[2] if len(vals) > 2 else ""})
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["section", "item", "value", "note"])


def clean_opex(raw: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    source = raw.get("14. Operating Cost (OPEX)", pd.DataFrame())
    header = _find_header_row(source, ["cost_line", "annual_pkr", "basis"], 4)
    df = _table_from_header(source, header)
    df = df.rename(columns={
        "cost_line": "cost_line",
        "annual_pkr": "annual_pkr",
        "basis": "basis",
        "note": "note",
    })
    if "annual_pkr" not in df.columns:
        return pd.DataFrame(columns=["cost_line", "annual_pkr", "basis", "note"])
    df = df[pd.to_numeric(df["annual_pkr"], errors="coerce").notna()].copy()
    df["annual_pkr"] = _numeric(df["annual_pkr"])
    for col in ["cost_line", "basis", "note"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype(str).str.strip()
    return df.reset_index(drop=True)


def station_table(sub_assemblies: pd.DataFrame, main_assembly: pd.DataFrame) -> pd.DataFrame:
    sa = sub_assemblies.rename(columns={"description": "name", "feeds_into": "linked_station"})[
        ["station", "type", "name", "linked_station", "skill_level", "workers", "min_workers", "base_time_min", "safety_critical"]
    ]
    ma = main_assembly.rename(columns={"operations": "name", "receives_from_sa": "linked_station"})[
        ["station", "type", "name", "linked_station", "skill_level", "workers", "min_workers", "base_time_min"]
    ]
    ma["safety_critical"] = ma["station"].eq("MA-06")
    table = pd.concat([ma, sa], ignore_index=True)
    table["skill_level"] = table["skill_level"].replace({"nan": "Semi-skilled", "": "Semi-skilled"}).fillna("Semi-skilled")
    return table.sort_values(["type", "station"]).reset_index(drop=True)


def clean_all_data(raw: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    summary = extract_summary_metrics(raw)
    sub_assemblies = clean_sub_assemblies(raw)
    main_assembly = clean_main_assembly(raw)
    stations = station_table(sub_assemblies, main_assembly)

    return {
        "summary": summary,
        "space": clean_space_schedule(raw),
        "sub_assemblies": sub_assemblies,
        "main_assembly": main_assembly,
        "stations": stations,
        "headcount": clean_headcount(raw),
        "labour_cost": clean_labour_cost(raw),
        "capex_summary": clean_capex_summary(raw),
        "assumptions": clean_assumptions(raw),
        "opex": clean_opex(raw),
        "ma_station_times": dict(zip(main_assembly["station"], main_assembly["base_time_min"])),
        "ma_workers": dict(zip(main_assembly["station"], main_assembly["workers"])),
        "sa_station_times": dict(zip(sub_assemblies["station"], sub_assemblies["base_time_min"])),
        "sa_workers": dict(zip(sub_assemblies["station"], sub_assemblies["workers"])),
        "station_times": dict(zip(stations["station"], stations["base_time_min"])),
        "station_workers": dict(zip(stations["station"], stations["workers"])),
        "station_min_workers": dict(zip(stations["station"], stations["min_workers"])),
        "station_skill": dict(zip(stations["station"], stations["skill_level"])),
        "station_type": dict(zip(stations["station"], stations["type"])),
    }
