# VoltRides International Optimization Dashboard

A GitHub-ready Streamlit dashboard for VoltRides production planning, line balancing, OPEX optimization, scenario comparison, and real-time decision recommendations.

## What is included

- Executive decision cockpit with target, feasibility, bottleneck, OPEX/bike, and recommended action cards
- Cleaner professional layout with a consistent design system
- Overflow-safe text handling for KPI cards, recommendation cards, charts, and tables
- Mathematical optimization framework with station worker, shift, overtime, and parallel capacity decisions
- MA + SA integrated line balance view
- OPEX cost-driver view with fixed, variable, hour-driven, CapEx-linked, and quality-driven costs
- Sensitivity and constraint diagnostics
- Plant layout with short labels and hover details
- Data quality and assumptions audit page

## Project structure

```text
app.py
requirements.txt
runtime.txt
README.md
.streamlit/config.toml
data/
  VoltRides_Plant_Master_v1.xlsx
  Opex.xlsx
src/
  charts.py
  config.py
  data_cleaning.py
  data_loader.py
  decision_engine.py
  design_system.py
  formatting.py
  labour_model.py
  opex_model.py
  optimizer.py
  production_model.py
  schema.py
  sensitivity.py
  solver_model.py
  ui_components.py
  validations.py
```

## Local run

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud deployment

Upload the extracted project contents to GitHub. Do not upload the ZIP file directly.

Recommended GitHub root:

```text
app.py
requirements.txt
runtime.txt
data/
src/
```

Streamlit Cloud settings:

```text
Main file path: app.py
Branch: main
```

Avoid spaces in folder names. Use names like `VoltRides_Optimization_Dashboard_V1` if the app is inside a subfolder.
