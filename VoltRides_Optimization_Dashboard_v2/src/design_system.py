from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src.config import COLORS


_STATUS_BG = {
    "success": ("#ECFDF5", "#BBF7D0"),
    "warning": ("#FFFBEB", "#FDE68A"),
    "danger": ("#FEF2F2", "#FECACA"),
    "info": ("#EFF6FF", "#BFDBFE"),
    "neutral": ("#F8FAFC", "#E2E8F0"),
}


def apply_theme() -> None:
    """Apply a consistent executive-grade visual system to the Streamlit app."""
    st.markdown(
        f"""
        <style>
        :root {{
            --vr-primary: {COLORS['primary']};
            --vr-success: {COLORS['success']};
            --vr-warning: {COLORS['warning']};
            --vr-danger: {COLORS['danger']};
            --vr-muted: {COLORS['muted']};
            --vr-card: {COLORS['card']};
            --vr-border: {COLORS['border']};
            --vr-text: {COLORS['text']};
            --vr-bg: #F8FAFC;
            --vr-soft-blue: #EFF6FF;
        }}

        .stApp {{
            background: linear-gradient(180deg, #F8FAFC 0%, #FFFFFF 28%, #FFFFFF 100%);
        }}

        .block-container {{
            padding-top: 1.05rem;
            padding-bottom: 2.8rem;
            max-width: 1500px;
        }}

        h1, h2, h3, h4 {{
            color: var(--vr-text);
            letter-spacing: -0.02em;
        }}

        h1 {{
            font-size: 2.05rem !important;
            line-height: 1.15 !important;
            margin-bottom: 0.25rem !important;
        }}

        h2 {{
            font-size: 1.45rem !important;
            margin-top: 1.1rem !important;
        }}

        h3 {{
            font-size: 1.12rem !important;
        }}

        p, li, div, span {{
            overflow-wrap: break-word;
            word-break: normal;
        }}

        section[data-testid="stSidebar"] {{
            background: #F8FAFC;
            border-right: 1px solid #E2E8F0;
        }}

        section[data-testid="stSidebar"] [data-testid="stExpander"] {{
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            background: white;
            overflow: hidden;
        }}

        /* ------------------------------------------------------------------
           Color-coded top navigation tabs
           The default Streamlit tab underline can look like an anonymous bar.
           These rules turn each tab into a named, colored navigation pill.
        ------------------------------------------------------------------ */
        div[data-testid="stTabs"] {{
            margin-top: 0.5rem;
        }}

        div[data-testid="stTabs"] div[role="tablist"] {{
            display: flex;
            gap: 10px;
            border-bottom: 1px solid #E2E8F0;
            padding: 0.55rem 0 0.85rem 0;
            overflow-x: auto;
            scrollbar-width: thin;
        }}

        div[data-testid="stTabs"] button[role="tab"] {{
            min-height: 46px;
            border: 1px solid #E2E8F0 !important;
            border-top-width: 5px !important;
            border-radius: 14px !important;
            background: #FFFFFF !important;
            box-shadow: 0 5px 15px rgba(15, 23, 42, 0.045);
            padding: 0.62rem 0.95rem !important;
            transition: all 0.18s ease-in-out;
            white-space: nowrap;
            flex: 0 0 auto;
        }}

        div[data-testid="stTabs"] button[role="tab"] p {{
            color: #334155 !important;
            font-weight: 800 !important;
            font-size: 0.9rem !important;
            line-height: 1.15 !important;
            margin: 0 !important;
            white-space: nowrap !important;
        }}

        div[data-testid="stTabs"] button[role="tab"]:hover {{
            transform: translateY(-1px);
            box-shadow: 0 9px 22px rgba(15, 23, 42, 0.10);
        }}

        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
            color: white !important;
            box-shadow: 0 10px 26px rgba(15, 23, 42, 0.16);
        }}

        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] p {{
            color: white !important;
        }}

        div[data-testid="stTabs"] button[role="tab"]:nth-of-type(1) {{ border-top-color: #2563EB !important; }}
        div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2) {{ border-top-color: #7C3AED !important; }}
        div[data-testid="stTabs"] button[role="tab"]:nth-of-type(3) {{ border-top-color: #16A34A !important; }}
        div[data-testid="stTabs"] button[role="tab"]:nth-of-type(4) {{ border-top-color: #EA580C !important; }}
        div[data-testid="stTabs"] button[role="tab"]:nth-of-type(5) {{ border-top-color: #DC2626 !important; }}
        div[data-testid="stTabs"] button[role="tab"]:nth-of-type(6) {{ border-top-color: #0891B2 !important; }}
        div[data-testid="stTabs"] button[role="tab"]:nth-of-type(7) {{ border-top-color: #64748B !important; }}

        div[data-testid="stTabs"] button[role="tab"]:nth-of-type(1)[aria-selected="true"] {{ background: #2563EB !important; border-color: #2563EB !important; }}
        div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2)[aria-selected="true"] {{ background: #7C3AED !important; border-color: #7C3AED !important; }}
        div[data-testid="stTabs"] button[role="tab"]:nth-of-type(3)[aria-selected="true"] {{ background: #16A34A !important; border-color: #16A34A !important; }}
        div[data-testid="stTabs"] button[role="tab"]:nth-of-type(4)[aria-selected="true"] {{ background: #EA580C !important; border-color: #EA580C !important; }}
        div[data-testid="stTabs"] button[role="tab"]:nth-of-type(5)[aria-selected="true"] {{ background: #DC2626 !important; border-color: #DC2626 !important; }}
        div[data-testid="stTabs"] button[role="tab"]:nth-of-type(6)[aria-selected="true"] {{ background: #0891B2 !important; border-color: #0891B2 !important; }}
        div[data-testid="stTabs"] button[role="tab"]:nth-of-type(7)[aria-selected="true"] {{ background: #64748B !important; border-color: #64748B !important; }}

        .vr-tab-guide {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 0.45rem 0 0.15rem 0;
            padding: 0.75rem;
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 16px;
        }}

        .vr-tab-chip {{
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 7px 11px;
            border-radius: 999px;
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            color: #334155;
            font-size: 0.78rem;
            font-weight: 800;
            white-space: nowrap;
            box-shadow: 0 3px 10px rgba(15, 23, 42, 0.04);
        }}

        .vr-tab-dot {{
            width: 10px;
            height: 10px;
            display: inline-block;
            border-radius: 999px;
            flex: 0 0 auto;
        }}

        div[data-testid="stMetric"] {{
            background: white;
            border: 1px solid var(--vr-border);
            border-radius: 16px;
            padding: 14px 16px;
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
            min-height: 120px;
            overflow-wrap: anywhere;
        }}

        div[data-testid="stMetricLabel"] p {{
            color: #64748B;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            font-size: 0.78rem;
            white-space: normal;
        }}

        div[data-testid="stMetricValue"] {{
            color: #0F172A;
            white-space: normal;
            overflow-wrap: anywhere;
            line-height: 1.1;
        }}

        .vr-page-hero {{
            background: linear-gradient(135deg, #0F172A 0%, #1E40AF 55%, #2563EB 100%);
            border-radius: 22px;
            padding: 24px 28px;
            color: white;
            box-shadow: 0 18px 48px rgba(15, 23, 42, 0.22);
            margin-bottom: 18px;
            overflow: hidden;
        }}

        .vr-page-hero h1 {{
            color: white !important;
            margin: 0 0 8px 0 !important;
        }}

        .vr-page-hero p {{
            color: rgba(255,255,255,0.86);
            margin: 0;
            max-width: 980px;
            line-height: 1.5;
        }}

        .vr-kicker {{
            display: inline-block;
            font-size: 0.74rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: rgba(255,255,255,0.76);
            margin-bottom: 8px;
        }}

        .vr-section-title {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 18px 0 10px 0;
        }}

        .vr-section-title .vr-section-icon {{
            width: 34px;
            height: 34px;
            border-radius: 10px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: #EFF6FF;
            color: var(--vr-primary);
            font-weight: 800;
        }}

        .vr-section-title h2, .vr-section-title h3 {{
            margin: 0 !important;
        }}

        .vr-card {{
            background: white;
            border: 1px solid var(--vr-border);
            border-radius: 18px;
            padding: 18px 20px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
            margin-bottom: 12px;
            overflow-wrap: anywhere;
        }}

        .vr-panel {{
            background: white;
            border: 1px solid var(--vr-border);
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 8px 28px rgba(15, 23, 42, 0.05);
            margin-bottom: 16px;
            overflow-wrap: anywhere;
        }}

        .vr-status {{
            border-radius: 20px;
            padding: 20px 22px;
            border: 1px solid var(--vr-border);
            margin: 8px 0 18px 0;
            overflow-wrap: anywhere;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
        }}

        .vr-status-success {{background: #ECFDF5; border-color: #BBF7D0;}}
        .vr-status-warning {{background: #FFFBEB; border-color: #FDE68A;}}
        .vr-status-danger {{background: #FEF2F2; border-color: #FECACA;}}
        .vr-status-info {{background: #EFF6FF; border-color: #BFDBFE;}}

        .vr-pill {{
            display:inline-block;
            padding: 5px 11px;
            border-radius: 999px;
            background:#EEF2FF;
            color:#3730A3;
            font-size: 0.76rem;
            font-weight: 800;
            margin-bottom: 8px;
            overflow-wrap: anywhere;
        }}

        .vr-decision-grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 14px;
            margin-bottom: 16px;
        }}

        .vr-metric-card {{
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 18px;
            padding: 16px 18px;
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
            min-height: 128px;
            overflow-wrap: anywhere;
            position: relative;
        }}

        .vr-metric-card::before {{
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 4px;
            border-radius: 18px 18px 0 0;
            background: var(--vr-primary);
        }}

        .vr-metric-card.good::before {{ background: var(--vr-success); }}
        .vr-metric-card.warning::before {{ background: var(--vr-warning); }}
        .vr-metric-card.bad::before {{ background: var(--vr-danger); }}
        .vr-metric-card.neutral::before {{ background: #94A3B8; }}

        .vr-metric-title {{
            font-size: 0.75rem;
            font-weight: 800;
            color: #64748B;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            margin-bottom: 10px;
        }}

        .vr-metric-value {{
            font-size: clamp(1.25rem, 2vw, 1.85rem);
            font-weight: 850;
            color: #0F172A;
            line-height: 1.13;
            margin-bottom: 8px;
        }}

        .vr-metric-subtitle {{
            font-size: 0.82rem;
            color: #64748B;
            line-height: 1.38;
        }}

        .vr-section-note {{
            background: #FFFFFF;
            border: 1px solid #CBD5E1;
            border-left: 6px solid var(--vr-primary);
            padding: 0.95rem 1rem;
            border-radius: 0.85rem;
            margin-bottom: 1rem;
            color: #0F172A;
            line-height: 1.52;
            font-weight: 650;
            overflow-wrap: anywhere;
            box-shadow: none;
        }}

        .vr-rec-card {{
            background: #FFFFFF;
            border-radius: 16px;
            padding: 16px 18px;
            margin-bottom: 12px;
            border: 1px solid #E5E7EB;
            box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
            overflow-wrap: anywhere;
        }}

        .vr-rec-critical, .vr-rec-high {{ border-left: 6px solid var(--vr-danger); }}
        .vr-rec-medium {{ border-left: 6px solid var(--vr-warning); }}
        .vr-rec-low {{ border-left: 6px solid var(--vr-primary); }}

        .vr-rec-priority {{
            font-size: 0.74rem;
            font-weight: 800;
            color: #64748B;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 7px;
        }}

        .vr-rec-text {{
            font-size: 0.96rem;
            color: #0F172A;
            line-height: 1.45;
            font-weight: 700;
            margin-bottom: 6px;
        }}

        .vr-rec-why {{
            font-size: 0.86rem;
            color: #64748B;
            line-height: 1.45;
        }}

        /* ------------------------------------------------------------------
           Sidebar station process-time controls
        ------------------------------------------------------------------ */
        .vr-station-sidebar-title {{
            background: #FFFFFF;
            border: 1px solid #CBD5E1;
            border-left: 5px solid var(--vr-primary);
            border-radius: 12px;
            color: #0F172A;
            font-size: 0.88rem;
            font-weight: 900;
            line-height: 1.3;
            margin: 12px 0 8px 0;
            padding: 10px 11px;
            overflow-wrap: anywhere;
        }}

        .vr-sidebar-field-label {{
            color: #1E293B;
            font-size: 0.72rem;
            font-weight: 900;
            letter-spacing: 0.035em;
            line-height: 1.22;
            margin: 0 0 5px 0;
            min-height: 28px;
            text-transform: uppercase;
        }}

        /* ------------------------------------------------------------------
           High-contrast assembly feeder cards
           Used in Data Quality → Assembly feeder map.
        ------------------------------------------------------------------ */
        .vr-feeder-grid {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 14px;
            margin-top: 0.6rem;
        }}

        .vr-feeder-card {{
            background: #FFFFFF;
            border: 1px solid #CBD5E1;
            border-top: 6px solid var(--vr-primary);
            border-radius: 18px;
            padding: 16px 16px 14px 16px;
            box-shadow: none;
            color: #0F172A;
            overflow-wrap: anywhere;
        }}

        .vr-feeder-ma {{
            font-size: 1.05rem;
            font-weight: 900;
            line-height: 1.2;
            margin-bottom: 4px;
        }}

        .vr-feeder-flow-label {{
            font-size: 0.76rem;
            font-weight: 900;
            color: #334155;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 12px;
        }}

        .vr-feeder-list {{
            display: flex;
            flex-direction: column;
            gap: 9px;
        }}

        .vr-feeder-item {{
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 14px;
            padding: 11px 12px;
        }}

        .vr-feeder-station {{
            font-size: 0.92rem;
            font-weight: 900;
            color: #111827;
            line-height: 1.2;
        }}

        .vr-feeder-desc {{
            font-size: 0.86rem;
            font-weight: 750;
            color: #334155;
            margin-top: 3px;
            line-height: 1.35;
        }}

        .vr-feeder-meta {{
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 7px;
            margin-top: 8px;
            font-size: 0.74rem;
            font-weight: 850;
            color: #475569;
        }}

        .vr-feeder-safety {{
            background: #FEF3C7;
            color: #92400E;
            border: 1px solid #F59E0B;
            border-radius: 999px;
            padding: 3px 8px;
            font-size: 0.70rem;
            font-weight: 900;
        }}

        @media (max-width: 1100px) {{
            .vr-feeder-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .small-muted {{ color: #64748B; font-size: 0.88rem; line-height: 1.45; }}

        .stDataFrame {{ border-radius: 14px; }}

        div[data-testid="stDataFrame"] {{
            border: 1px solid #E5E7EB;
            border-radius: 14px;
            overflow: hidden;
        }}


        /* ------------------------------------------------------------------
           Force the Assembly Feeder Sankey chart to stay readable in both
           Streamlit light and dark modes. This removes grey/shadow text and
           keeps labels plain black on a white chart canvas.
        ------------------------------------------------------------------ */
        .js-plotly-plot .sankey text,
        .js-plotly-plot .sankey .node-label,
        .js-plotly-plot .sankey .annotation-text,
        .js-plotly-plot .sankey .main-svg text {{
            fill: #000000 !important;
            color: #000000 !important;
            text-shadow: none !important;
            filter: none !important;
            stroke: none !important;
            paint-order: normal !important;
            font-weight: 700 !important;
        }}

        .js-plotly-plot .sankey .bg,
        .js-plotly-plot .sankey .main-svg,
        .js-plotly-plot .sankey svg {{
            background: #FFFFFF !important;
        }}

        .js-plotly-plot .plotly .modebar {{
            right: 8px !important;
        }}

        @media (max-width: 1100px) {{
            .vr-decision-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
        }}

        @media (max-width: 720px) {{
            .vr-decision-grid {{ grid-template-columns: 1fr; }}
            .vr-page-hero {{ padding: 20px; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def apply_chart_layout(fig: go.Figure, height: int = 430, title: str | None = None) -> go.Figure:
    """Apply a clean, overflow-safe Plotly layout."""
    fig.update_layout(
        height=height,
        title=dict(text=title or fig.layout.title.text, x=0.01, xanchor="left", font=dict(size=18)),
        font=dict(family="Inter, Arial, sans-serif", size=12, color=COLORS["text"]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=24, r=60, t=70, b=48),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="white", font_size=12, font_color="#0F172A"),
        uniformtext_minsize=9,
        uniformtext_mode="hide",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#E2E8F0", zeroline=False, automargin=True)
    fig.update_yaxes(showgrid=False, zeroline=False, automargin=True, tickfont=dict(size=11))
    return fig
