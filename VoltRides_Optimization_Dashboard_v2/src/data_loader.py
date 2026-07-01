from __future__ import annotations

from typing import Dict

import pandas as pd

try:
    import streamlit as st
except Exception:  # Allows non-Streamlit unit checks before deployment.
    class _CacheShim:
        def cache_data(self, *args, **kwargs):
            def deco(fn):
                return fn
            return deco
    st = _CacheShim()

from src.config import MASTER_FILE, OPEX_FILE


@st.cache_data(show_spinner=False)
def load_workbook_sheets(master_file: str | None = None, opex_file: str | None = None) -> Dict[str, pd.DataFrame]:
    """Load all dashboard workbooks as raw dataframes.

    The cleaning layer handles headers and merged cells, so this loader deliberately reads
    sheets with header=None.
    """
    master_path = master_file or str(MASTER_FILE)
    opex_path = opex_file or str(OPEX_FILE)

    master_xls = pd.ExcelFile(master_path)
    opex_xls = pd.ExcelFile(opex_path)

    raw: Dict[str, pd.DataFrame] = {}
    for sheet_name in master_xls.sheet_names:
        raw[sheet_name] = pd.read_excel(master_xls, sheet_name=sheet_name, header=None)
    for sheet_name in opex_xls.sheet_names:
        raw[sheet_name] = pd.read_excel(opex_xls, sheet_name=sheet_name, header=None)
    return raw
