# Bioprocess Phase Planner

A planner for cell-culture processes built from phases (batch, fed-batch, continuous bleed & feed).
It predicts cell density, metabolites, working volume, medium use and biomass, **hour by hour**, and
compares scenarios side by side.

**Privacy:** the app runs entirely in your browser from `localhost`. Inputs and saved scenarios stay on your
computer, in the browser's storage. The local server blocks every request to another host (Content-Security-Policy).

**Status:** v1 (milestones M0–M7). **All numbers are placeholders.**

## Run

Requires Python 3.13 (via [uv](https://docs.astral.sh/uv/)), plus npm on the first run to fetch the runtime (~75 MB, then offline).

```bash
./run.sh            # in-browser app on http://localhost:8765
```

Native mode is for development, or as the fallback. Scenarios are then saved in `scenarios/private/` (gitignored):

```bash
uv sync --extra dev
uv run streamlit run app/Home.py          # http://localhost:8501
```

## Use

1. **Setup**: vessel, working-volume window, seeding density, metabolites.
2. **Phases**: up to 6 phases. Each has a duration and µ; fed-batch phases pick a feed regime; continuous phases set
   the bleed (feed = bleed by default, or the suggested feed with a cell-free harvest).
3. **Feed regimes**: daily feed volume (% of V0), fed as a constant flow.
4. **Results**: key numbers, checks, charts, hour-by-hour playback, CSV/Excel export.
5. **Compare**: overlay saved scenarios, with Δ% against a baseline.

*My scenarios* saves, opens, imports (YAML, zip backup, or a spreadsheet-planner `.xlsx`) and exports.
The working scenario is autosaved, so a page reload does not lose edits.

## Develop

```bash
uv run pytest -q                 # model, parity with the spreadsheet, invariants, edge cases, I/O, page smoke tests
uv run python -m bioprocess      # prints the MODEL.md §5 reference table
```

Model specification: [MODEL.md](MODEL.md). Plan: [_plan/PLAN.md](_plan/PLAN.md).
