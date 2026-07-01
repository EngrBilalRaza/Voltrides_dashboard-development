from __future__ import annotations

from typing import Dict

import pandas as pd

from src.config import BASE_ANNUAL_OUTPUT, SA10_MIN_WORKERS


def run_data_checks(data: dict, target_annual_output: float) -> pd.DataFrame:
    rows = []
    stations = data.get("stations", pd.DataFrame())
    opex = data.get("opex", pd.DataFrame())
    labour = data.get("labour_cost", pd.DataFrame())
    headcount = data.get("headcount", pd.DataFrame())
    space = data.get("space", pd.DataFrame())
    station_min_workers: Dict[str, int] = data.get("station_min_workers", {})
    station_workers: Dict[str, int] = data.get("station_workers", {})

    def add(status, check, detail, fix=""):
        rows.append({"Status": status, "Check": check, "Detail": detail, "Suggested Fix": fix})

    if stations.empty:
        add("Error", "Station master", "No MA/SA station data was loaded.", "Check Excel sheets 4 and 5.")
    else:
        add("OK", "Station master", f"Loaded {len(stations)} MA/SA stations.", "")

    if station_workers.get("SA-10", 0) < SA10_MIN_WORKERS or station_min_workers.get("SA-10", 0) < SA10_MIN_WORKERS:
        add("Error", "SA-10 safety staffing", "SA-10 Battery Box is below minimum 2-worker rule.", "Set SA-10 minimum and current workers to at least 2.")
    else:
        add("OK", "SA-10 safety staffing", "SA-10 minimum staffing rule is present.", "")

    if opex.empty:
        add("Warning", "OPEX workbook", "No OPEX lines were loaded.", "Check Opex.xlsx sheet name and columns.")
    else:
        annual_opex = float(opex.get("annual_pkr", pd.Series(dtype=float)).sum())
        add("OK", "OPEX workbook", f"Loaded annual non-labour OPEX of PKR {annual_opex:,.0f}.", "")
        if target_annual_output and abs(target_annual_output - BASE_ANNUAL_OUTPUT) / BASE_ANNUAL_OUTPUT > 0.05:
            add("Warning", "OPEX denominator", f"Target {target_annual_output:,.0f}/yr differs from base design {BASE_ANNUAL_OUTPUT:,.0f}/yr.", "Use dynamic OPEX per bike, not the static workbook denominator.")

    headcount_total = int(headcount.get("count", pd.Series(dtype=float)).sum()) if not headcount.empty else 0
    labour_count = int(labour.get("count", pd.Series(dtype=float)).sum()) if not labour.empty else 0
    if headcount_total and labour_count and headcount_total != labour_count:
        add("Warning", "Headcount consistency", f"Headcount sheet total is {headcount_total}, labour-cost total is {labour_count}.", "Reconcile workbook totals before management sign-off.")
    elif headcount_total or labour_count:
        add("OK", "Headcount consistency", f"Headcount/labour total available: {max(headcount_total, labour_count)} people.", "")
    else:
        add("Warning", "Headcount consistency", "No headcount or labour count loaded.", "Check sheets 6 and 7.")

    if not space.empty:
        area = float(space.get("area_sqft", pd.Series(dtype=float)).sum())
        add("OK", "Space schedule", f"Loaded {area:,.0f} sq ft across {len(space)} zones.", "")
    else:
        add("Warning", "Space schedule", "No space schedule loaded.", "Check sheet 3.")

    return pd.DataFrame(rows)
