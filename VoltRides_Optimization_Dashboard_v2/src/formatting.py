from __future__ import annotations

import textwrap
from typing import Any

import pandas as pd


def pkr(value: Any, decimals: int = 0) -> str:
    try:
        val = float(value)
    except Exception:
        return "PKR 0"
    return f"PKR {val:,.{decimals}f}"


def pkr_short(value: Any) -> str:
    try:
        val = float(value)
    except Exception:
        return "PKR 0"
    sign = "-" if val < 0 else ""
    val = abs(val)
    if val >= 1_000_000_000:
        return f"{sign}PKR {val / 1_000_000_000:.1f}B"
    if val >= 1_000_000:
        return f"{sign}PKR {val / 1_000_000:.1f}M"
    if val >= 1_000:
        return f"{sign}PKR {val / 1_000:.1f}K"
    return f"{sign}PKR {val:,.0f}"


def num(value: Any, decimals: int = 0, suffix: str = "") -> str:
    try:
        val = float(value)
    except Exception:
        return f"0{suffix}"
    return f"{val:,.{decimals}f}{suffix}"


def pct(value: Any, decimals: int = 1) -> str:
    try:
        val = float(value)
    except Exception:
        return "0.0%"
    return f"{val:.{decimals}f}%"


def wrap_label(value: Any, width: int = 24) -> str:
    text = "" if pd.isna(value) else str(value)
    return "<br>".join(textwrap.wrap(text, width=width)) or text


def short_label(text: Any, max_chars: int = 38) -> str:
    value = "" if pd.isna(text) else str(text)
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 1].rstrip() + "…"
