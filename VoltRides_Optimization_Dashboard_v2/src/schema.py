from __future__ import annotations

import pandas as pd


REQUIRED_DATASETS = {
    "stations": ["station", "type", "base_time_min", "workers", "min_workers"],
    "opex": ["cost_line", "annual_pkr"],
    "space": ["zone", "area_sqft"],
}


def schema_report(data: dict) -> pd.DataFrame:
    rows = []
    for key, columns in REQUIRED_DATASETS.items():
        df = data.get(key, pd.DataFrame())
        missing = [c for c in columns if c not in df.columns]
        rows.append({
            "Dataset": key,
            "Rows": len(df),
            "Required Columns": ", ".join(columns),
            "Missing Columns": ", ".join(missing) if missing else "None",
            "Status": "OK" if not missing and len(df) > 0 else "Warning",
        })
    return pd.DataFrame(rows)
