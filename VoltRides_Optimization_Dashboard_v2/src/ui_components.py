from __future__ import annotations

import html
from contextlib import contextmanager
from typing import Iterable

import pandas as pd
import streamlit as st

from src.config import COLORS
from src.formatting import pkr_short


def _escape(value) -> str:
    return html.escape("" if value is None else str(value))


def page_hero(title: str, subtitle: str, kicker: str = "VoltRides decision cockpit") -> None:
    st.markdown(
        f"""
        <div class="vr-page-hero">
            <div class="vr-kicker">{_escape(kicker)}</div>
            <h1>{_escape(title)}</h1>
            <p>{_escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(title: str, icon: str = "▣", level: int = 2) -> None:
    tag = "h2" if level == 2 else "h3"
    st.markdown(
        f"""
        <div class="vr-section-title">
            <span class="vr-section-icon">{_escape(icon)}</span>
            <{tag}>{_escape(title)}</{tag}>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_note(text: str) -> None:
    st.markdown(f'<div class="vr-section-note">{_escape(text)}</div>', unsafe_allow_html=True)


@contextmanager
def panel(title: str | None = None, icon: str = "▣", note: str | None = None):
    st.markdown('<div class="vr-panel">', unsafe_allow_html=True)
    if title:
        section_title(title, icon=icon, level=3)
    if note:
        section_note(note)
    try:
        yield
    finally:
        st.markdown('</div>', unsafe_allow_html=True)


def status_banner(level: str, headline: str, message: str) -> None:
    css = {
        "success": "vr-status-success",
        "warning": "vr-status-warning",
        "danger": "vr-status-danger",
        "info": "vr-status-info",
    }.get(level, "vr-status-warning")
    icon = {"success": "✅", "warning": "⚠️", "danger": "🔴", "info": "ℹ️"}.get(level, "ℹ️")
    st.markdown(
        f"""
        <div class="vr-status {css}">
            <div class="vr-pill">{icon} Decision status</div>
            <h3 style="margin:0;">{_escape(headline)}</h3>
            <p style="margin: 8px 0 0 0; color:#334155; line-height:1.45;">{_escape(message)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(title: str, value: str, subtitle: str | None = None, status: str = "neutral") -> None:
    status = status if status in {"good", "warning", "bad", "neutral", "info"} else "neutral"
    if status == "info":
        status = "neutral"
    st.markdown(
        f"""
        <div class="vr-metric-card {status}">
            <div class="vr-metric-title">{_escape(title)}</div>
            <div class="vr-metric-value">{_escape(value)}</div>
            <div class="vr-metric-subtitle">{_escape(subtitle or "")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_row(items: list[tuple[str, str, str | None]] | list[tuple[str, str, str | None, str]]) -> None:
    if not items:
        return
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        if len(item) == 4:
            label, value, subtitle, status = item
        else:
            label, value, subtitle = item
            status = "neutral"
        with col:
            metric_card(label, value, subtitle, status)


def recommendation_cards(recs_df: pd.DataFrame, limit: int = 6) -> None:
    if recs_df is None or recs_df.empty:
        st.info("No recommendations generated for the selected scenario.")
        return
    for _, row in recs_df.head(limit).iterrows():
        priority = str(row.get("Priority", "Medium"))
        css_priority = priority.lower().replace(" ", "-")
        if css_priority not in {"critical", "high", "medium", "low"}:
            css_priority = "medium"
        st.markdown(
            f"""
            <div class="vr-rec-card vr-rec-{css_priority}">
                <div class="vr-rec-priority">{_escape(priority)} Priority · {_escape(row.get('Area', ''))}</div>
                <div class="vr-rec-text">{_escape(row.get('Recommendation', ''))}</div>
                <div class="vr-rec-why">{_escape(row.get('Why it matters', ''))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def dashboard_input_summary(target: dict, controls: dict) -> None:
    kpi_row([
        ("Target", f"{target['monthly_target']:,.0f}/mo", f"{target['annual_target']:,.0f} annualized", "neutral"),
        ("Objective", str(controls.get("objective", "")), "Optimization preference", "neutral"),
        ("Uptime", f"{controls.get('uptime', 0):.0%}", "Operating assumption", "good"),
        ("Limits", f"{controls.get('max_shifts', 1)} shifts", f"Max {controls.get('max_workers', 1)} workers/station", "neutral"),
    ])


def dataframe_with_status(df: pd.DataFrame, height: int = 360) -> None:
    if df is None or df.empty:
        st.info("No records to display.")
        return
    display_df = df.copy()
    # Keep long text readable in Streamlit tables by trimming very long strings.
    for col in display_df.select_dtypes(include="object").columns:
        display_df[col] = display_df[col].apply(lambda x: x if len(str(x)) <= 140 else str(x)[:137] + "...")
    st.dataframe(display_df, width="stretch", hide_index=True, height=height)


def compact_money_table(df: pd.DataFrame, money_cols: Iterable[str]) -> pd.DataFrame:
    out = df.copy()
    for col in money_cols:
        if col in out.columns:
            out[col] = out[col].apply(pkr_short)
    return out
