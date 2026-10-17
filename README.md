# Bioprocess Phase Planner

A planner for cell-culture processes built from phases (batch, fed-batch, continuous bleed & feed).
It predicts cell density, metabolites, volumes, medium use and biomass, hour by hour, and compares scenarios.

**Privacy:** the app runs entirely in your browser from `localhost`. Inputs and saved scenarios stay
on your computer (browser storage). The local server blocks any request to another host.

**Status:** under development (milestone M0 done: scaffold + runtime). All numbers are placeholders.

## Run
Requires Python 3.13 (via [uv](https://docs.astral.sh/uv/)) and npm (first run only, to fetch the runtime).

```bash
./run.sh          # opens http://localhost:8765
```

## Develop
```bash
uv sync --extra dev
uv run pytest -q
uv run streamlit run app/Home.py --server.address 127.0.0.1
```

Model specification: [MODEL.md](MODEL.md). Plan: [_plan/PLAN.md](_plan/PLAN.md).
