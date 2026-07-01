from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
MASTER_FILE = DATA_DIR / "VoltRides_Plant_Master_v1.xlsx"
OPEX_FILE = DATA_DIR / "Opex.xlsx"

BASE_ANNUAL_OUTPUT = 5000
WORKING_DAYS_YEAR = 250
WORKING_DAYS_MONTH = 20
SHIFT_MINUTES = 480
BASE_UPTIME = 0.90
BASE_SHIFTS_PER_DAY = 1
MAX_WORKERS_PER_STATION = 4
MAX_SHIFTS_PER_DAY = 4
MAX_OVERTIME_MINUTES_PER_DAY = 120
BASE_SCRAP_RATE = 0.03
SA10_MIN_WORKERS = 2

BUILDING_LENGTH_FT = 150
BUILDING_WIDTH_FT = 80
BUILDING_AREA_SQFT = BUILDING_LENGTH_FT * BUILDING_WIDTH_FT
FUNCTIONAL_AREA_SQFT = 4880

DEFAULT_MA_TIMES = {
    "MA-01": 10.0,
    "MA-02": 10.0,
    "MA-03": 10.0,
    "MA-04": 10.0,
    "MA-05": 10.0,
    "MA-06": 15.0,
}

DEFAULT_SA_TIMES = {
    "SA-01": 24.0,
    "SA-02": 24.0,
    "SA-03": 24.0,
    "SA-04": 24.0,
    "SA-05": 24.0,
    "SA-06": 24.0,
    "SA-07": 24.0,
    "SA-08": 24.0,
    "SA-09": 24.0,
    "SA-10": 24.0,
    "SA-11": 24.0,
}

# Monthly salary assumptions used for incremental staff when the workbook does not specify
# station-level salary costs. Users can change these in the sidebar.
DEFAULT_MONTHLY_SKILL_RATES = {
    "Unskilled": 45000,
    "Semi-skilled": 60000,
    "Skilled": 75000,
    "Senior": 120000,
    "Professional": 180000,
    "Supervisor": 140000,
}

# CapEx / expansion assumptions for the optimization model.
DEFAULT_PARALLEL_STATION_CAPEX = 850000
CAPEX_ANNUALIZATION_YEARS = 5
DEFAULT_PARALLEL_STATION_AREA_SQFT = 85
DEFAULT_EXTRA_SHIFT_FIXED_OPEX = 1_250_000
DEFAULT_OVERTIME_PREMIUM = 1.5

OBJECTIVES = [
    "Minimize OPEX per bike",
    "Minimize total operating cost",
    "Minimize additional workers",
    "Minimize CapEx",
    "Maximize utilization",
    "Balanced decision score",
]

COLORS = {
    "primary": "#2563EB",
    "secondary": "#7C3AED",
    "success": "#16A34A",
    "warning": "#F59E0B",
    "danger": "#DC2626",
    "muted": "#64748B",
    "bg": "#F8FAFC",
    "card": "#FFFFFF",
    "border": "#E2E8F0",
    "text": "#0F172A",
    "soft_blue": "#DBEAFE",
    "soft_green": "#DCFCE7",
    "soft_yellow": "#FEF3C7",
    "soft_red": "#FEE2E2",
}

MA_COLORS = {
    "MA-01": "#2563EB",
    "MA-02": "#0EA5E9",
    "MA-03": "#16A34A",
    "MA-04": "#7C3AED",
    "MA-05": "#F97316",
    "MA-06": "#DC2626",
}
