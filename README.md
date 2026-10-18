# Bioprocess Phase Planner

**Open the app:** https://nicolascristini.github.io/bioprocess-dashboard/

A planner for cell-culture processes built from phases (batch, fed-batch, continuous bleed & feed).
It predicts cell density, metabolites, working volume, medium use and biomass, **hour by hour**, and
compares scenarios side by side.

**Privacy:** the app is a static web page and the Python runs inside your browser tab. There is no server
behind it: inputs and saved scenarios stay in your browser's storage. Share the link freely, because every visitor
works with their own data. The page's Content-Security-Policy makes the browser refuse any request to another host.

**Status:** v1 (milestones M0–M7). **All numbers are placeholders.**

## Run

Open the shared link, or preview locally. Local preview needs Python 3.13 (via [uv](https://docs.astral.sh/uv/)),
plus npm on the first run to fetch the runtime (~75 MB):

```bash
./run.sh            # builds dist/ and opens http://localhost:8765/
```

## Publish (shareable link)

`python3 scripts/build_site.py --base /<path>/` writes a self-contained static site to `dist/`, for any static
host. On GitHub Pages, `.github/workflows/site.yml` does it on every push once the repository variable
`DEPLOY_PAGES` is `true` and Pages is set to "GitHub Actions". The link then looks like
`https://<user>.github.io/bioprocess-dashboard/`.

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
