from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from src.charts import (
    assembly_sankey,
    financial_waterfall,
    opex_breakdown_chart,
    opex_driver_chart,
    plant_layout_figure,
    scenario_capacity_chart,
    scenario_cost_chart,
    sensitivity_target_chart,
    space_bar,
    space_treemap,
    station_time_chart,
    worker_recommendation_chart,
)
from src.config import (
    BASE_ANNUAL_OUTPUT,
    BASE_SCRAP_RATE,
    BASE_UPTIME,
    DEFAULT_MONTHLY_SKILL_RATES,
    FUNCTIONAL_AREA_SQFT,
    MAX_OVERTIME_MINUTES_PER_DAY,
    MAX_SHIFTS_PER_DAY,
    MAX_WORKERS_PER_STATION,
    MA_COLORS,
    OBJECTIVES,
    SHIFT_MINUTES,
    WORKING_DAYS_YEAR,
)
from src.data_cleaning import clean_all_data
from src.data_loader import load_workbook_sheets
from src.decision_engine import constraint_diagnostics, decision_status, generate_recommendations
from src.design_system import apply_theme
from src.formatting import num, pct, pkr, pkr_short
from src.labour_model import labour_summary
from src.opex_model import opex_driver_summary, prepare_opex
from src.optimizer import run_optimization
from src.production_model import (
    calculate_capacity,
    calculate_line_balance,
    calculate_required_takt,
    normalize_target,
    station_balance_dataframe,
    worker_loads,
)
from src.schema import schema_report
from src.sensitivity import driver_sensitivity, target_sensitivity
from src.ui_components import (
    compact_money_table,
    dashboard_input_summary,
    dataframe_with_status,
    kpi_row,
    page_hero,
    panel,
    recommendation_cards,
    section_note,
    section_title,
    status_banner,
)
from src.validations import run_data_checks


st.set_page_config(
    page_title="VoltRides Assemblyliner Dashboard",
    page_icon="⚡",
    layout="wide",
)
apply_theme()


@st.cache_data(show_spinner=True)
def load_data() -> dict:
    raw = load_workbook_sheets()
    data = clean_all_data(raw)
    data["opex"] = prepare_opex(data["opex"])
    return data



def render_sidebar(data: dict) -> dict:
    st.sidebar.title("⚙️ Control Panel")
    st.sidebar.caption("Set the target, operating limits, and cost assumptions. The decision cockpit updates automatically.")

    with st.sidebar.expander("1. Production target", expanded=True):
        target_units = st.number_input("Target production", min_value=1.0, value=400.0, step=10.0)
        target_period = st.selectbox("Target period", ["Per Month", "Per Year", "Per Day", "Per Shift"], index=0)
        objective = st.selectbox("Optimization objective", OBJECTIVES, index=0)

    with st.sidebar.expander("2. Operating constraints", expanded=True):
        uptime = st.slider("Expected uptime", 0.50, 1.00, BASE_UPTIME, 0.01)
        max_shifts = st.slider("Maximum shifts/day", 1, MAX_SHIFTS_PER_DAY, 2)
        max_overtime = st.slider("Maximum overtime minutes/day", 0, MAX_OVERTIME_MINUTES_PER_DAY, 60, 30)
        max_workers = st.slider("Maximum workers/station", 1, 6, MAX_WORKERS_PER_STATION)
        allow_parallel = st.toggle("Allow parallel bottleneck stations / CapEx", value=True)
        expansion_area = st.number_input("Available expansion area (sq ft)", min_value=0.0, value=800.0, step=50.0)

    with st.sidebar.expander("3. Cost drivers", expanded=False):
        st.caption("Enter percentages directly. The model converts them into decimal rates for the optimizer.")
        scrap_rate_pct = st.number_input(
            "Scrap / rework rate (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(BASE_SCRAP_RATE * 100),
            step=0.5,
            help="Quality loss / rework allowance as a percentage of production cost driver. Example: enter 3 for 3%.",
        )
        energy_escalation_pct_input = st.number_input(
            "Energy tariff escalation (%)",
            min_value=-100.0,
            max_value=100.0,
            value=0.0,
            step=1.0,
            help="Expected electricity/gas tariff change. Example: enter 10 for +10% or -5 for a 5% reduction.",
        )
        miscellaneous_cost_pct_input = st.number_input(
            "Miscellaneous cost allowance (%)",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=0.5,
            help="Additional contingency / unknown OPEX allowance applied to optimized annual OPEX subtotal.",
        )
        scrap_rate = scrap_rate_pct / 100
        energy_escalation = energy_escalation_pct_input / 100
        miscellaneous_cost_pct = miscellaneous_cost_pct_input / 100

    monthly_rates = DEFAULT_MONTHLY_SKILL_RATES.copy()
    with st.sidebar.expander("4. Monthly skill rates", expanded=False):
        for skill, rate in DEFAULT_MONTHLY_SKILL_RATES.items():
            monthly_rates[skill] = st.number_input(
                f"{skill} monthly PKR",
                min_value=0.0,
                value=float(rate),
                step=5000.0,
                key=f"rate_{skill}",
            )

    station_times = data["station_times"].copy()
    station_workers = data["station_workers"].copy()
    station_min_workers = data["station_min_workers"].copy()

    with st.sidebar.expander("5. Station process times", expanded=False):
        st.caption("Use short station labels here; full station details remain available in tables and hover tooltips.")
        station_df = data["stations"].sort_values(["type", "station"])
        for _, row in station_df.iterrows():
            station = row["station"]
            st.markdown(f"<div class='vr-station-sidebar-title'>{escape(str(station))} — {escape(str(row.get('name', '')))}</div>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("<div class='vr-sidebar-field-label'>Process time / takt time (min)</div>", unsafe_allow_html=True)
                station_times[station] = st.number_input(
                    f"{station} process time minutes",
                    min_value=1.0,
                    max_value=480.0,
                    value=float(station_times.get(station, row.get("base_time_min", 10.0))),
                    step=1.0,
                    key=f"time_{station}",
                    label_visibility="collapsed",
                )
            minimum = int(station_min_workers.get(station, 1))
            current = max(int(station_workers.get(station, minimum)), minimum)
            with c2:
                st.markdown("<div class='vr-sidebar-field-label'>No. of worker</div>", unsafe_allow_html=True)
                station_workers[station] = st.slider(
                    f"{station} number of workers",
                    minimum,
                    max(max_workers, minimum),
                    current,
                    key=f"worker_{station}",
                    label_visibility="collapsed",
                )

    return {
        "target_units": target_units,
        "target_period": target_period,
        "objective": objective,
        "uptime": uptime,
        "max_shifts": max_shifts,
        "max_overtime": max_overtime,
        "max_workers": max_workers,
        "allow_parallel": allow_parallel,
        "expansion_area": expansion_area,
        "scrap_rate": scrap_rate,
        "energy_escalation": energy_escalation,
        "miscellaneous_cost_pct": miscellaneous_cost_pct,
        "monthly_rates": monthly_rates,
        "station_times": station_times,
        "station_workers": station_workers,
        "station_min_workers": station_min_workers,
    }

def model_run(data: dict, controls: dict):
    base_labour_annual = labour_summary(data["labour_cost"], BASE_ANNUAL_OUTPUT)["annual_cost"]
    target = normalize_target(controls["target_units"], controls["target_period"])
    current_required_takt = calculate_required_takt(target["daily_target"], SHIFT_MINUTES, 1, controls["uptime"], 0)
    current_balance = calculate_line_balance(controls["station_times"], controls["station_workers"])
    current_capacity = calculate_capacity(current_balance["cycle_time"], SHIFT_MINUTES, 1, WORKING_DAYS_YEAR, controls["uptime"], 0)
    best, scenarios, scenario_df, solver_metadata = run_optimization(
        target=target,
        station_times=controls["station_times"],
        current_workers=controls["station_workers"],
        station_min_workers=controls["station_min_workers"],
        station_skill=data["station_skill"],
        station_type=data["station_type"],
        opex_df=data["opex"],
        objective=controls["objective"],
        uptime=controls["uptime"],
        max_workers_per_station=controls["max_workers"],
        max_shifts_per_day=controls["max_shifts"],
        max_overtime_minutes_per_day=controls["max_overtime"],
        scrap_rate=controls["scrap_rate"],
        allow_parallel_stations=controls["allow_parallel"],
        available_expansion_area_sqft=controls["expansion_area"],
        monthly_rates=controls["monthly_rates"],
        energy_escalation_pct=controls["energy_escalation"],
        miscellaneous_cost_pct=controls["miscellaneous_cost_pct"],
        base_labour_annual=base_labour_annual,
    )
    recommended_takt = calculate_required_takt(
        target["daily_target"],
        SHIFT_MINUTES,
        int(best.get("Required Shifts", 1)) if best else 1,
        controls["uptime"],
        int(best.get("Overtime Min/Day", 0)) if best else 0,
    )
    return {
        "target": target,
        "current_required_takt": current_required_takt,
        "recommended_takt": recommended_takt,
        "current_balance": current_balance,
        "current_capacity": current_capacity,
        "best": best,
        "scenarios": scenarios,
        "scenario_df": scenario_df,
        "solver_metadata": solver_metadata,
    }



def render_decision_cockpit(data: dict, controls: dict, result: dict):
    target = result["target"]
    best = result["best"]
    scenario_df = result["scenario_df"]
    current = result["scenarios"][0] if result["scenarios"] else None
    status = decision_status(best, current, target)

    page_hero(
        "VoltRides Production Optimization Dashboard",
        "Executive decision cockpit for target output, operating constraints, OPEX impact, bottlenecks, and recommended actions.",
        "Assemblyliner Graphical User Interface",
    )
    status_banner(status["level"], status["headline"], status["message"])

    section_title("Selected scenario inputs", icon="①")
    dashboard_input_summary(target, controls)

    section_title("Executive decision summary", icon="②")
    kpi_row([
        ("Annualized Target", f"{target['annual_target']:,.0f} bikes", "Converted from user input", "neutral"),
        ("Daily Target", f"{target['daily_target']:,.1f} bikes/day", "Required production pace", "neutral"),
        ("Current Cycle Time", f"{result['current_balance']['cycle_time']:.1f} min", "Before recommendation", "warning" if result['current_balance']['cycle_time'] > result['current_required_takt'] else "good"),
        ("Current Capacity", f"{result['current_capacity']['annual_capacity']:,.0f}/yr", "Current modeled output", "good" if result['current_capacity']['annual_capacity'] >= target['annual_target'] else "bad"),
    ])

    if best:
        kpi_row([
            ("Recommended Scenario", best["Scenario"], "Best feasible operating mode", "good"),
            ("Recommended Capacity", f"{best['Annual Capacity']:,.0f}/yr", f"Gap {best['Capacity Gap']:,.0f}", "good" if best['Capacity Gap'] >= 0 else "bad"),
            ("Operating Cost / Bike", pkr(best["Operating Cost per Bike"]), "Labour + OPEX + annualized CapEx", "neutral"),
            ("OPEX / Bike", pkr(best["OPEX per Bike"]), "Running expense per unit", "neutral"),
        ])
        kpi_row([
            ("Required Shifts", f"{best['Required Shifts']:.0f}", "Recommended shift count", "warning" if best['Required Shifts'] > 1 else "good"),
            ("Overtime", f"{best['Overtime Min/Day']:.0f} min/day", "Daily overtime lever", "warning" if best['Overtime Min/Day'] > 0 else "good"),
            ("Added Workers", f"{best['Added Workers']:.0f}", "Additional station labour", "warning" if best['Added Workers'] > 0 else "good"),
            ("Bottleneck", best["Bottleneck"], "Primary constraint to monitor", "warning"),
        ])

    recs = generate_recommendations(best, scenario_df, target, result["current_balance"], result["current_required_takt"], controls["station_min_workers"])

    left, right = st.columns([0.42, 0.58])
    with left:
        section_title("Top management recommendations", icon="③", level=3)
        recommendation_cards(recs, limit=5)
    with right:
        section_title("Best scenarios at a glance", icon="④", level=3)
        st.plotly_chart(scenario_cost_chart(scenario_df), width="stretch")

    with st.expander("View capacity comparison and full decision context", expanded=False):
        st.plotly_chart(scenario_capacity_chart(scenario_df, target["annual_target"]), width="stretch")
        display_cols = ["Rank", "Recommended", "Scenario", "Feasible", "Risk Level", "Annual Capacity", "Capacity Gap", "Required Shifts", "Added Workers", "Bottleneck", "Operating Cost per Bike"]
        dataframe_with_status(scenario_df[[c for c in display_cols if c in scenario_df.columns]], height=360)


def render_optimization_model(data: dict, controls: dict, result: dict):
    st.header("Optimization Model")
    section_note(
        "This page separates inputs, solver logic, decision variables, and detailed scenario ranking so the optimization process is transparent and easy to audit."
    )

    left, right = st.columns([0.30, 0.70])
    with left:
        with st.container(border=True):
            section_title("Scenario inputs", icon="①", level=3)
            target = result["target"]
            st.write(f"**Target:** {target['monthly_target']:,.0f} bikes/month")
            st.write(f"**Annualized:** {target['annual_target']:,.0f} bikes/year")
            st.write(f"**Objective:** {controls['objective']}")
            st.write(f"**Uptime:** {controls['uptime']:.0%}")
            st.write(f"**Max shifts:** {controls['max_shifts']}")
            st.write(f"**Max workers/station:** {controls['max_workers']}")

        with st.container(border=True):
            section_title("Solver status", icon="②", level=3)
            meta = result["solver_metadata"]
            st.write(f"**Solver used:** {meta.get('method', 'Optimization engine')}")
            st.write(f"**Objectives solved:** {len(meta.get('solved_objectives', []))}")
            st.caption("If a mathematical solver is unavailable, the app falls back to conservative scenario search.")

    with right:
        with st.container(border=True):
            section_title("Mathematical model summary", icon="ƒ", level=3)
            st.markdown(
                """
                **Decision variables**  
                `x[i,k,p] = 1` if station `i` uses worker level `k` and parallel-station flag `p`.  
                `y[s] = 1` if the model chooses `s` shifts/day.  
                `z[o] = 1` if the model chooses overtime option `o` minutes/day.

                **Capacity constraint**  
                `daily_target × effective_time[i] ≤ shift_minutes × shifts × uptime + overtime` for every MA and SA station.

                **Objective**  
                Minimize selected business objective: OPEX per bike, operating cost, added workers, CapEx, utilization, or a balanced score.
                """
            )

    if result["best"]:
        section_title("Recommended station-level decision variables", icon="③")
        worker_df = pd.DataFrame([
            {
                "Station": s,
                "Type": data["station_type"].get(s, ""),
                "Current Workers": controls["station_workers"].get(s, 1),
                "Recommended Workers": result["best"]["Workers"].get(s, controls["station_workers"].get(s, 1)),
                "Parallel Added": result["best"]["Parallel"].get(s, 0),
                "Effective Time": result["best"]["Effective Times"].get(s, 0),
            }
            for s in controls["station_times"]
        ])
        chart_col, table_col = st.columns([0.55, 0.45])
        with chart_col:
            st.plotly_chart(worker_recommendation_chart(result["best"], controls["station_workers"], data["station_type"]), width="stretch")
        with table_col:
            dataframe_with_status(worker_df, height=460)

    section_title("Scenario comparison", icon="④")
    display_cols = [
        "Rank", "Recommended", "Scenario", "Feasible", "Risk Level", "Annual Capacity", "Capacity Gap",
        "Required Shifts", "Overtime Min/Day", "Added Workers", "Parallel Stations Added", "Bottleneck",
        "Annual Operating Cost", "Operating Cost per Bike", "Utilization %", "Solver Status",
    ]
    scenario_view = result["scenario_df"][[c for c in display_cols if c in result["scenario_df"].columns]].copy()
    dataframe_with_status(scenario_view, height=420)

    with st.expander("Solver diagnostics and full objective audit", expanded=False):
        dataframe_with_status(pd.DataFrame(result["solver_metadata"].get("solved_objectives", [])), height=280)


def render_line_balance(data: dict, controls: dict, result: dict):
    st.header("Production & Line Balance")
    section_note("Line balance combines main assembly and sub-assembly stations against the recommended takt. Long labels are kept in tables and hover tooltips to preserve chart readability.")
    best = result["best"]
    station_parallel = best.get("Parallel", {}) if best else {s: 0 for s in controls["station_times"]}
    station_workers = best.get("Workers", controls["station_workers"]) if best else controls["station_workers"]
    recommended_takt = result["recommended_takt"]
    balance_df = station_balance_dataframe(controls["station_times"], station_workers, data["station_type"], recommended_takt, station_parallel)

    kpi_row([
        ("Recommended Takt", f"{recommended_takt:.1f} min/bike", "Target operating pace", "neutral"),
        ("Integrated Cycle Time", f"{balance_df['Effective Time'].max():.1f} min", None if balance_df.empty else f"{balance_df.loc[balance_df['Effective Time'].idxmax(), 'Station']} bottleneck", "warning" if not balance_df.empty and balance_df['Effective Time'].max() > recommended_takt else "good"),
        ("Stations Above Takt", f"{(balance_df['Status'] == 'Above takt').sum():.0f}", "Should be zero", "bad" if (balance_df['Status'] == 'Above takt').sum() else "good"),
        ("Line Efficiency", f"{result['current_balance']['line_efficiency_pct']:.1f}%", "Current balance reference", "neutral"),
    ])

    section_title("Integrated station balance", icon="①")
    st.plotly_chart(station_time_chart(balance_df, recommended_takt, "Integrated MA + SA effective time vs recommended takt"), width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            section_title("Main assembly balance", icon="MA", level=3)
            ma_balance_df = balance_df[balance_df["Type"] == "MA"]
            st.plotly_chart(station_time_chart(ma_balance_df, recommended_takt, "Main assembly balance"), width="stretch")
    with c2:
        with st.container(border=True):
            section_title("Sub-assembly readiness", icon="SA", level=3)
            sa_balance_df = balance_df[balance_df["Type"] == "SA"]
            st.plotly_chart(station_time_chart(sa_balance_df, recommended_takt, "Sub-assembly readiness"), width="stretch")

    with st.expander("Detailed line balance table", expanded=True):
        dataframe_with_status(balance_df, height=440)

    with st.expander("Original main-line worker-tag load from workbook", expanded=False):
        loads = worker_loads(data["main_assembly"], controls["station_times"])
        if loads:
            dataframe_with_status(pd.DataFrame([{"Worker Tag": k, "Load Minutes": v} for k, v in loads.items()]), height=260)
        else:
            st.info("No worker-tag mapping found.")


def render_opex_costs(data: dict, controls: dict, result: dict):
    st.header("OPEX & Cost Drivers")
    best = result["best"]
    if not best:
        st.warning("No feasible scenario found, so OPEX optimization details are unavailable.")
        return
    opex_breakdown = best["OPEX Breakdown"]

    section_note("OPEX is grouped by cost driver so the dashboard can distinguish fixed costs, unit-variable costs, hour-driven costs, CapEx-linked costs, and quality/rework costs.")
    kpi_row([
        ("Annual OPEX", pkr_short(best["Annual OPEX"]), "Optimized annual running cost", "neutral"),
        ("Base Annual Labour", pkr_short(best.get("Base Annual Labour", 0)), "Workbook labour reference", "neutral"),
        ("Annualized CapEx", pkr_short(best["Annualized CapEx"]), "Expansion/parallel capacity impact", "warning" if best["Annualized CapEx"] else "good"),
        ("Operating Cost / Bike", pkr(best["Operating Cost per Bike"]), "Total operating view", "neutral"),
    ])

    c1, c2 = st.columns([1.35, 1])
    with c1:
        with st.container(border=True):
            section_title("Top OPEX lines", icon="①", level=3)
            st.plotly_chart(opex_breakdown_chart(opex_breakdown), width="stretch")
    with c2:
        with st.container(border=True):
            section_title("Cost-driver mix", icon="②", level=3)
            st.plotly_chart(opex_driver_chart(opex_breakdown), width="stretch")

    section_title("Cost-driver optimization levers", icon="③")
    cols = ["Cost Line", "Cost Type", "Cost Driver", "Optimization Lever", "Base Annual Cost", "Optimized Annual Cost", "Change"]
    view = opex_breakdown[[c for c in cols if c in opex_breakdown.columns]].copy()
    dataframe_with_status(view, height=440)

    with st.expander("Financial workbook summary", expanded=False):
        c3, c4 = st.columns(2)
        with c3:
            st.plotly_chart(financial_waterfall(data["capex_summary"]), width="stretch")
        with c4:
            labour = labour_summary(data["labour_cost"], result["target"]["annual_target"])
            kpi_row([
                ("Workbook Labour Headcount", f"{labour['headcount']:,}", None, "neutral"),
                ("Workbook Annual Labour", pkr_short(labour["annual_cost"]), None, "neutral"),
                ("Workbook Labour / Bike", pkr(labour["cost_per_bike"]), None, "neutral"),
            ])


def render_sensitivity_risk(data: dict, controls: dict, result: dict):
    st.header("Sensitivity & Risk")
    section_note("Sensitivity identifies trigger points where output, uptime, scrap, or cost pressure would change the recommended operating decision.")

    with st.spinner("Running target-volume sensitivity..."):
        sens_df = target_sensitivity(
            base_target_units=controls["target_units"],
            target_period=controls["target_period"],
            station_times=controls["station_times"],
            current_workers=controls["station_workers"],
            station_min_workers=controls["station_min_workers"],
            station_skill=data["station_skill"],
            station_type=data["station_type"],
            opex_df=data["opex"],
            objective=controls["objective"],
            uptime=controls["uptime"],
            max_workers_per_station=controls["max_workers"],
            max_shifts_per_day=controls["max_shifts"],
            max_overtime_minutes_per_day=controls["max_overtime"],
            scrap_rate=controls["scrap_rate"],
            allow_parallel_stations=controls["allow_parallel"],
            available_expansion_area_sqft=controls["expansion_area"],
            monthly_rates=controls["monthly_rates"],
            energy_escalation_pct=controls["energy_escalation"],
            miscellaneous_cost_pct=controls["miscellaneous_cost_pct"],
            base_labour_annual=labour_summary(data["labour_cost"], BASE_ANNUAL_OUTPUT)["annual_cost"],
        )
    section_title("Target volume sensitivity", icon="①")
    st.plotly_chart(sensitivity_target_chart(sens_df), width="stretch")

    with st.expander("Sensitivity data table", expanded=False):
        dataframe_with_status(sens_df, height=300)

    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            section_title("Constraint diagnostics", icon="②", level=3)
            best = result["best"]
            recommended_takt = result["recommended_takt"]
            parallel = best.get("Parallel", {}) if best else {s: 0 for s in controls["station_times"]}
            workers = best.get("Workers", controls["station_workers"]) if best else controls["station_workers"]
            balance_df = station_balance_dataframe(controls["station_times"], workers, data["station_type"], recommended_takt, parallel)
            diag = constraint_diagnostics(best, balance_df, recommended_takt, controls["max_workers"], controls["max_shifts"], controls["allow_parallel"])
            dataframe_with_status(diag, height=320)
    with c2:
        with st.container(border=True):
            section_title("Key driver watchlist", icon="③", level=3)
            dataframe_with_status(driver_sensitivity(result["best"], controls["scrap_rate"], controls["uptime"]), height=320)


def render_layout_space(data: dict, result: dict):
    st.header("Plant Layout & Space")
    section_note("Plant blocks use short labels to avoid text overflow. Full details are available in hover text, tables, and data quality views.")
    best = result["best"]
    bottlenecks = best["Bottleneck"].split(", ") if best else result["current_balance"].get("bottlenecks", [])
    c1, c2 = st.columns([1.45, 1.0])
    with c1:
        with st.container(border=True):
            section_title("Plant block layout", icon="①", level=3)
            st.plotly_chart(plant_layout_figure(data["sub_assemblies"], data["main_assembly"], bottlenecks=bottlenecks, safety_stations=["SA-10"]), width="stretch")
    with c2:
        with st.container(border=True):
            section_title("Space utilization", icon="②", level=3)
            st.plotly_chart(space_treemap(data["space"]), width="stretch")

    section_title("Zone footprint", icon="③")
    st.plotly_chart(space_bar(data["space"]), width="stretch")

    total_area = float(data["space"].get("area_sqft", pd.Series(dtype=float)).sum()) if not data["space"].empty else 0
    kpi_row([
        ("Loaded Zone Area", f"{total_area:,.0f} sq ft", "From space schedule", "neutral"),
        ("Functional Area Target", f"{FUNCTIONAL_AREA_SQFT:,.0f} sq ft", "Planning reference", "neutral"),
        ("Expansion Used", f"{best.get('Expansion Area SqFt', 0):,.0f} sq ft" if best else "0 sq ft", "Optimization expansion impact", "warning" if best and best.get('Expansion Area SqFt', 0) else "good"),
        ("Safety Highlight", "SA-10 Battery", "Minimum 2 workers", "warning"),
    ])


def render_feeder_flow_cards(sub_assemblies: pd.DataFrame) -> None:
    """Render a high-contrast MA-wise feeder card view for SA → MA relationships."""
    if sub_assemblies is None or sub_assemblies.empty:
        st.info("No sub-assembly feeder data is available.")
        return

    df = sub_assemblies.copy()
    df["feeds_into"] = df["feeds_into"].fillna("Unmapped").astype(str)
    df["description"] = df["description"].fillna("").astype(str)
    df["station"] = df["station"].fillna("").astype(str)
    df["workers"] = pd.to_numeric(df["workers"], errors="coerce").fillna(1).astype(int)
    df = df.sort_values(["feeds_into", "station"])

    cards = []
    for ma_station, group in df.groupby("feeds_into", sort=True):
        ma_color = MA_COLORS.get(str(ma_station), "#2563EB")
        items = []
        for _, row in group.iterrows():
            station = escape(str(row.get("station", "")))
            desc = escape(str(row.get("description", "")))
            workers = int(row.get("workers", 1))
            safety_critical = bool(row.get("safety_critical", False)) or str(row.get("station", "")).upper() == "SA-10"
            safety_badge = '<span class="vr-feeder-safety">Safety critical</span>' if safety_critical else ""
            items.append(
                f"""
                <div class="vr-feeder-item">
                    <div class="vr-feeder-station">{station}</div>
                    <div class="vr-feeder-desc">{desc}</div>
                    <div class="vr-feeder-meta">
                        <span>{workers} worker(s)</span>
                        {safety_badge}
                    </div>
                </div>
                """
            )

        cards.append(
            f"""
            <div class="vr-feeder-card" style="border-top-color:{ma_color};">
                <div class="vr-feeder-ma" style="color:{ma_color};">{escape(str(ma_station))}</div>
                <div class="vr-feeder-flow-label">Sub-assemblies feeding this main station</div>
                <div class="vr-feeder-list">{''.join(items)}</div>
            </div>
            """
        )

    html = f'<div class="vr-feeder-grid">{"".join(cards)}</div>'
    if hasattr(st, "html"):
        st.html(html)
    else:
        st.markdown(html, unsafe_allow_html=True)


def render_flow_data_quality(data: dict, controls: dict, result: dict):
    st.header("Assembly Flow, Data Quality & Assumptions")
    section_note("This page is the audit layer: it keeps detailed workbook data, feeder mapping, schema checks, and assumptions separate from the executive decision pages.")

    section_title("Assembly feeder map", icon="①")
    
    flow_left, flow_right = st.columns([1.35, 1.0])
    with flow_left:
        with st.container(border=True):
            section_title("Sub-assembly feeder flow framework", icon="A", level=3)
            st.plotly_chart(assembly_sankey(data["sub_assemblies"]), width="stretch")
    with flow_right:
        with st.container(border=True):
            section_title("Feeder relationship cards", icon="B", level=3)
            render_feeder_flow_cards(data["sub_assemblies"])

    with st.expander("Workbook station tables", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Sub-assemblies")
            dataframe_with_status(data["sub_assemblies"], height=360)
        with c2:
            st.subheader("Main assembly")
            dataframe_with_status(data["main_assembly"], height=360)

    section_title("Automated data checks", icon="②")
    checks = run_data_checks({**data, "station_workers": controls["station_workers"], "station_min_workers": controls["station_min_workers"]}, result["target"]["annual_target"])
    dataframe_with_status(checks, height=360)

    with st.expander("Schema report and assumptions", expanded=False):
        st.subheader("Schema report")
        dataframe_with_status(schema_report(data), height=260)
        st.subheader("Assumptions and notes")
        dataframe_with_status(data["assumptions"], height=360)

def main():
    data = load_data()
    controls = render_sidebar(data)
    result = model_run(data, controls)

    tabs = st.tabs([
        "🏛️ Executive Cockpit",
        "⚙️ Optimization Model",
        "🟢 Line Balance",
        "🧾 OPEX & Cost Drivers",
        "⚠️ Sensitivity & Risk",
        "🏭 Plant Layout",
        "✅ Data Quality",
    ])
    with tabs[0]:
        render_decision_cockpit(data, controls, result)
    with tabs[1]:
        render_optimization_model(data, controls, result)
    with tabs[2]:
        render_line_balance(data, controls, result)
    with tabs[3]:
        render_opex_costs(data, controls, result)
    with tabs[4]:
        render_sensitivity_risk(data, controls, result)
    with tabs[5]:
        render_layout_space(data, result)
    with tabs[6]:
        render_flow_data_quality(data, controls, result)


if __name__ == "__main__":
    main()
