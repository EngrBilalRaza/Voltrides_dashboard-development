from __future__ import annotations

from typing import Dict

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.config import BUILDING_LENGTH_FT, BUILDING_WIDTH_FT, COLORS, MA_COLORS
from src.design_system import apply_chart_layout
from src.formatting import short_label, wrap_label
from src.opex_model import opex_driver_summary


def status_color(status: str) -> str:
    text = str(status).lower()
    if "above" in text or "infeasible" in text or "high" in text:
        return COLORS["danger"]
    if "watch" in text or "medium" in text or "warning" in text:
        return COLORS["warning"]
    if "feasible" in text or "within" in text or "low" in text or "ok" in text:
        return COLORS["success"]
    return COLORS["primary"]


def station_time_chart(balance_df: pd.DataFrame, required_takt: float, title: str):
    df = balance_df.copy()
    if df.empty:
        return apply_chart_layout(go.Figure(), height=360, title=title)
    df["Display"] = df["Station"] + " • " + df["Type"].astype(str)
    df = df.sort_values("Effective Time", ascending=True)
    color_map = {"Within takt": COLORS["success"], "Above takt": COLORS["danger"]}
    fig = px.bar(
        df,
        x="Effective Time",
        y="Display",
        orientation="h",
        color="Status",
        color_discrete_map=color_map,
        custom_data=["Base Time", "Workers", "Parallel Stations", "Takt Gap"],
        text="Effective Time",
    )
    fig.add_vline(x=required_takt, line_dash="dash", line_color=COLORS["primary"], annotation_text=f"Takt {required_takt:.1f} min")
    fig.update_traces(
        texttemplate="%{text:.1f}",
        textposition="auto",
        cliponaxis=False,
        hovertemplate="%{y}<br>Effective: %{x:.1f} min<br>Base: %{customdata[0]:.1f} min<br>Workers: %{customdata[1]}<br>Parallel: %{customdata[2]}<br>Takt gap: %{customdata[3]:.1f} min<extra></extra>",
    )
    fig.update_layout(xaxis_title="Minutes", yaxis_title="")
    return apply_chart_layout(fig, height=max(420, 30 * len(df) + 120), title=title)


def scenario_cost_chart(scenario_df: pd.DataFrame):
    if scenario_df.empty:
        return apply_chart_layout(go.Figure(), height=360, title="Scenario cost comparison")
    df = scenario_df.copy().head(12)
    df["Scenario Short"] = df["Scenario"].apply(lambda x: short_label(x, 42))
    df = df.sort_values("Operating Cost per Bike", ascending=True)
    fig = px.bar(
        df,
        x="Operating Cost per Bike",
        y="Scenario Short",
        orientation="h",
        color="Recommended",
        color_discrete_map={True: COLORS["primary"], False: COLORS["muted"]},
        text="Operating Cost per Bike",
        custom_data=["Scenario", "Annual Capacity", "Added Workers", "Required Shifts", "Risk Level"],
    )
    fig.update_traces(
        texttemplate="PKR %{text:,.0f}",
        textposition="auto",
        cliponaxis=False,
        hovertemplate="%{customdata[0]}<br>Cost/bike: PKR %{x:,.0f}<br>Capacity: %{customdata[1]:,.0f}/yr<br>Added workers: %{customdata[2]}<br>Shifts: %{customdata[3]}<br>Risk: %{customdata[4]}<extra></extra>",
    )
    fig.update_layout(xaxis_title="Operating cost per bike", yaxis_title="", showlegend=False)
    return apply_chart_layout(fig, height=max(420, 35 * len(df) + 120), title="Scenario operating cost per bike")


def scenario_capacity_chart(scenario_df: pd.DataFrame, target_annual_output: float):
    if scenario_df.empty:
        return apply_chart_layout(go.Figure(), height=360, title="Scenario capacity comparison")
    df = scenario_df.copy().sort_values("Annual Capacity", ascending=True).tail(12)
    df["Scenario Short"] = df["Scenario"].apply(lambda x: short_label(x, 42))
    fig = px.bar(
        df,
        x="Annual Capacity",
        y="Scenario Short",
        orientation="h",
        color="Feasible",
        color_discrete_map={True: COLORS["success"], False: COLORS["danger"]},
        text="Annual Capacity",
        custom_data=["Scenario", "Capacity Gap", "Bottleneck", "Utilization %"],
    )
    fig.add_vline(x=target_annual_output, line_dash="dash", line_color=COLORS["primary"], annotation_text=f"Target {target_annual_output:,.0f}")
    fig.update_traces(
        texttemplate="%{text:,.0f}",
        textposition="auto",
        cliponaxis=False,
        hovertemplate="%{customdata[0]}<br>Capacity: %{x:,.0f}/yr<br>Gap: %{customdata[1]:,.0f}<br>Bottleneck: %{customdata[2]}<br>Utilization: %{customdata[3]:.1f}%<extra></extra>",
    )
    fig.update_layout(xaxis_title="Bikes/year", yaxis_title="")
    return apply_chart_layout(fig, height=max(420, 35 * len(df) + 120), title="Scenario capacity vs target")


def opex_breakdown_chart(opex_breakdown: pd.DataFrame):
    if opex_breakdown is None or opex_breakdown.empty:
        return apply_chart_layout(go.Figure(), height=360, title="OPEX breakdown")
    df = opex_breakdown.copy().sort_values("Optimized Annual Cost", ascending=True).tail(12)
    df["Cost Line Short"] = df["Cost Line"].apply(lambda x: short_label(x, 44))
    fig = px.bar(
        df,
        x="Optimized Annual Cost",
        y="Cost Line Short",
        orientation="h",
        color="Cost Type",
        text="Optimized Annual Cost",
        custom_data=["Cost Line", "Cost Driver", "Optimization Lever", "Change"],
    )
    fig.update_traces(
        texttemplate="PKR %{text:,.0f}",
        textposition="auto",
        cliponaxis=False,
        hovertemplate="%{customdata[0]}<br>Cost: PKR %{x:,.0f}<br>Driver: %{customdata[1]}<br>Lever: %{customdata[2]}<br>Change: PKR %{customdata[3]:,.0f}<extra></extra>",
    )
    fig.update_layout(xaxis_title="PKR/year", yaxis_title="")
    return apply_chart_layout(fig, height=max(420, 34 * len(df) + 120), title="Top optimized OPEX cost lines")


def opex_driver_chart(opex_breakdown: pd.DataFrame):
    df = opex_driver_summary(opex_breakdown)
    if df.empty:
        return apply_chart_layout(go.Figure(), height=360, title="OPEX by cost driver")
    fig = px.pie(df, values="Optimized Annual Cost", names="Cost Type", hole=0.48, custom_data=["Share %"])
    fig.update_traces(textinfo="percent+label", hovertemplate="%{label}<br>PKR %{value:,.0f}<br>Share %{customdata[0]:.1f}%<extra></extra>")
    return apply_chart_layout(fig, height=420, title="OPEX by cost driver")


def worker_recommendation_chart(best: dict | None, current_workers: Dict[str, int], station_type: Dict[str, str]):
    if not best:
        return apply_chart_layout(go.Figure(), height=360, title="Worker recommendation")
    rows = []
    for station, recommended in best.get("Workers", {}).items():
        rows.append({
            "Station": station,
            "Type": station_type.get(station, "Station"),
            "Current": int(current_workers.get(station, 1)),
            "Recommended": int(recommended),
            "Delta": int(recommended) - int(current_workers.get(station, 1)),
        })
    df = pd.DataFrame(rows).sort_values(["Delta", "Station"], ascending=[True, True])
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Current", y=df["Station"], x=df["Current"], orientation="h", marker_color=COLORS["muted"], text=df["Current"], textposition="auto"))
    fig.add_trace(go.Bar(name="Recommended", y=df["Station"], x=df["Recommended"], orientation="h", marker_color=COLORS["primary"], text=df["Recommended"], textposition="auto"))
    fig.update_layout(barmode="group", xaxis_title="Workers", yaxis_title="")
    return apply_chart_layout(fig, height=max(420, 28 * len(df) + 140), title="Current vs recommended station workers")


def sensitivity_target_chart(sensitivity_df: pd.DataFrame):
    if sensitivity_df.empty:
        return apply_chart_layout(go.Figure(), height=360, title="Target sensitivity")
    fig = px.line(
        sensitivity_df,
        x="Annual Target",
        y="Operating Cost / Bike",
        markers=True,
        color="Risk Level",
        custom_data=["Feasible", "Shifts", "Added Workers", "Parallel Stations"],
    )
    fig.update_traces(hovertemplate="Annual target: %{x:,.0f}<br>Cost/bike: PKR %{y:,.0f}<br>Feasible: %{customdata[0]}<br>Shifts: %{customdata[1]}<br>Added workers: %{customdata[2]}<br>Parallel: %{customdata[3]}<extra></extra>")
    fig.update_layout(xaxis_title="Annual target", yaxis_title="Operating cost / bike")
    return apply_chart_layout(fig, height=430, title="Target volume sensitivity")


def space_treemap(space_df: pd.DataFrame):
    df = space_df.copy()
    df = df[df["area_sqft"] > 0]
    if df.empty:
        return apply_chart_layout(go.Figure(), height=360, title="Space utilization")
    fig = px.treemap(df, path=["zone"], values="area_sqft", color="area_sqft", color_continuous_scale="Blues", custom_data=["notes"])
    fig.update_traces(textinfo="label+value", hovertemplate="%{label}<br>%{value:,.0f} sq ft<br>%{customdata[0]}<extra></extra>")
    return apply_chart_layout(fig, height=480, title="Space utilization treemap")


def space_bar(space_df: pd.DataFrame):
    df = space_df.copy()
    df = df[df["area_sqft"] > 0].sort_values("area_sqft", ascending=True)
    df["Zone Short"] = df["zone"].apply(lambda x: short_label(x, 38))
    fig = px.bar(df, x="area_sqft", y="Zone Short", orientation="h", text="area_sqft", custom_data=["zone", "pct_building", "notes"])
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="auto", cliponaxis=False, hovertemplate="%{customdata[0]}<br>Area: %{x:,.0f} sq ft<br>Building share: %{customdata[1]:.1%}<br>%{customdata[2]}<extra></extra>")
    fig.update_layout(xaxis_title="sq ft", yaxis_title="")
    return apply_chart_layout(fig, height=max(420, 28 * len(df) + 120), title="Zone footprint")


def assembly_sankey(sub_assemblies: pd.DataFrame):
    """Readable Sankey chart for SA → MA feeder relationships.

    Kept as the original feeder-map style, but forced onto a white canvas
    with plain black text so it remains readable in Streamlit light/dark mode.
    """
    if sub_assemblies is None or sub_assemblies.empty:
        fig = go.Figure()
        fig.update_layout(paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF")
        return apply_chart_layout(
            fig,
            height=420,
            title="Sub-assembly feeder flow into main assembly",
        )

    def hex_to_rgba(hex_color: str, alpha: float = 0.28) -> str:
        hex_color = str(hex_color).replace("#", "")
        if len(hex_color) != 6:
            return f"rgba(37, 99, 235, {alpha})"
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha})"

    labels, index, node_colors = [], {}, []
    sources, targets, values, link_colors = [], [], [], []

    def idx(label: str, color: str):
        if label not in index:
            index[label] = len(labels)
            labels.append(label)
            node_colors.append(color)
        return index[label]

    # Keep the previous map concept: one feeder source → SA nodes → MA nodes.
    # Use light node fills and strong black labels for readability.
    plant_idx = idx("Sub-Assembly Feed", "#DBEAFE")

    df = sub_assemblies.copy()
    df["feeds_into"] = df["feeds_into"].fillna("Unmapped").astype(str)
    df["description"] = df["description"].fillna("").astype(str)
    df["station"] = df["station"].fillna("").astype(str)
    df["workers"] = pd.to_numeric(df["workers"], errors="coerce").fillna(1)
    df = df.sort_values(["feeds_into", "station"])

    for _, row in df.iterrows():
        station = str(row.get("station", ""))
        description = short_label(str(row.get("description", "")), 28)
        ma_station = str(row.get("feeds_into", "Unmapped"))
        ma_color = MA_COLORS.get(ma_station, COLORS["primary"])
        worker_value = max(1.0, float(row.get("workers", 1)))

        # Single-line labels are clearer than grey multi-line labels in the Sankey view.
        sa_label = f"{station} {description}".strip()
        ma_label = ma_station

        sa_idx = idx(sa_label, "#EFF6FF")
        ma_idx = idx(ma_label, "#DBEAFE")

        sources.append(plant_idx)
        targets.append(sa_idx)
        values.append(worker_value)
        link_colors.append("rgba(15, 23, 42, 0.22)")

        sources.append(sa_idx)
        targets.append(ma_idx)
        values.append(worker_value)
        link_colors.append(hex_to_rgba(ma_color, 0.42))

    fig = go.Figure(
        data=[
            go.Sankey(
                arrangement="snap",
                textfont=dict(size=13, color="#000000", family="Arial, sans-serif"),
                node=dict(
                    label=labels,
                    pad=24,
                    thickness=22,
                    color=node_colors,
                    line=dict(color="#334155", width=0.9),
                    hovertemplate="%{label}<extra></extra>",
                ),
                link=dict(
                    source=sources,
                    target=targets,
                    value=values,
                    color=link_colors,
                    hovertemplate="Flow weight: %{value}<extra></extra>",
                ),
            )
        ]
    )
    fig.update_layout(
        font=dict(size=13, color="#000000", family="Arial, sans-serif"),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        margin=dict(l=18, r=18, t=72, b=24),
    )
    fig = apply_chart_layout(fig, height=570, title="Sub-assembly feeder flow into main assembly")
    fig.update_layout(
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(size=13, color="#000000", family="Arial, sans-serif"),
        title=dict(
            text="Sub-assembly feeder flow into main assembly",
            x=0.01,
            xanchor="left",
            font=dict(size=18, color="#000000", family="Arial, sans-serif"),
        ),
    )
    return fig

def plant_layout_figure(sub_assemblies: pd.DataFrame, main_assembly: pd.DataFrame, bottlenecks=None, safety_stations=None):
    bottlenecks = set(bottlenecks or [])
    safety_stations = set(safety_stations or ["SA-10"])
    fig = go.Figure()
    fig.add_shape(type="rect", x0=0, y0=0, x1=BUILDING_LENGTH_FT, y1=BUILDING_WIDTH_FT, line=dict(width=2, color="#334155"), fillcolor="#F8FAFC")
    zones = [
        ("Offices", 0, 56, 24, 80),
        ("Weld", 28, 62, 48, 72),
        ("Incoming", 100, 55, 150, 75),
        ("Frame Tag", 30, 47, 40, 57),
        ("Paint", 0, 0, 25, 25),
        ("Main Line", 55, 37, 95, 42),
        ("Test", 100, 30, 115, 45),
        ("Finished", 100, 0, 150, 25),
        ("Expansion", 118, 28, 148, 50),
    ]
    for name, x0, y0, x1, y1 in zones:
        fill = "#E2E8F0" if name != "Expansion" else "#EEF2FF"
        dash = None if name != "Expansion" else "dash"
        fig.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1, line=dict(width=1, color="#CBD5E1", dash=dash), fillcolor=fill)
        fig.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2, text=name, showarrow=False, font=dict(size=10, color="#0F172A"), hovertext=f"{name} zone")
    ma_y0, ma_y1, ma_x0 = 37, 42, 55
    ma_w = 40 / max(len(main_assembly), 1)
    for i, (_, row) in enumerate(main_assembly.iterrows()):
        station = row["station"]
        x0, x1 = ma_x0 + i * ma_w, ma_x0 + (i + 1) * ma_w
        is_bn = station in bottlenecks
        fig.add_shape(type="rect", x0=x0, y0=ma_y0, x1=x1, y1=ma_y1, line=dict(color=COLORS["danger"] if is_bn else "#334155", width=3 if is_bn else 1), fillcolor=MA_COLORS.get(station, COLORS["primary"]))
        fig.add_annotation(x=(x0+x1)/2, y=(ma_y0+ma_y1)/2, text=station, showarrow=False, font=dict(size=9, color="white"))
    for i, (_, row) in enumerate(sub_assemblies.iterrows()):
        top = i < 6
        x0 = 50 + (i % 6) * 9
        y0 = 50 if top else 24
        x1, y1 = x0 + 8, y0 + 7
        station = row["station"]
        is_safety = station in safety_stations
        fig.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1, line=dict(width=2 if is_safety else 1, color=COLORS["warning"] if is_safety else "#94A3B8"), fillcolor="#FEF3C7" if is_safety else "#F1F5F9")
        fig.add_annotation(x=(x0+x1)/2, y=(y0+y1)/2, text=station, showarrow=False, font=dict(size=9, color="#0F172A"))
    # Main flow arrows
    for x0, y0, x1, y1 in [(25, 12, 55, 39), (95, 39, 112, 38), (115, 38, 125, 15)]:
        fig.add_annotation(x=x1, y=y1, ax=x0, ay=y0, xref="x", yref="y", axref="x", ayref="y", showarrow=True, arrowhead=3, arrowsize=1, arrowwidth=2, arrowcolor=COLORS["primary"])
    fig.update_xaxes(range=[0, BUILDING_LENGTH_FT], visible=False)
    fig.update_yaxes(range=[0, BUILDING_WIDTH_FT], visible=False, scaleanchor="x", scaleratio=1)
    return apply_chart_layout(fig, height=640, title="Plant layout with bottleneck and safety highlights")


def financial_waterfall(capex_df: pd.DataFrame):
    df = capex_df.copy()
    df = df[df["amount_pkr"] > 0].sort_values("amount_pkr", ascending=True)
    if df.empty:
        return apply_chart_layout(go.Figure(), height=360, title="CapEx breakdown")
    df["Category Short"] = df["category"].apply(lambda x: short_label(x, 38))
    fig = px.bar(df, x="amount_pkr", y="Category Short", orientation="h", text="amount_pkr", custom_data=["category", "notes"])
    fig.update_traces(texttemplate="PKR %{text:,.0f}", textposition="auto", cliponaxis=False, hovertemplate="%{customdata[0]}<br>Amount: PKR %{x:,.0f}<br>%{customdata[1]}<extra></extra>")
    fig.update_layout(xaxis_title="PKR", yaxis_title="")
    return apply_chart_layout(fig, height=max(420, 28 * len(df) + 120), title="CapEx breakdown")
