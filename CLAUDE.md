# CLAUDE.md: bioprocess-dashboard

A personal project: a browser-based planner for batch → fed-batch → continuous (bleed & feed)
cell-culture processes. Python model + Streamlit UI that runs **inside the browser** (stlite /
Pyodide), served from localhost only.

## Read first
- `MODEL.md`: the model spec (parameters, equations, checks, assumptions, reference numbers). Code follows it.
- `_plan/PLAN.md`: the build plan and milestones. `_plan/M0_SPIKE.md`: runtime findings.

## Non-negotiable rules
- **Inputs are confidential and never leave the machine.** No hosting, no external API calls, no
  telemetry, no CDN assets. `scripts/serve.py` enforces this with a this-origin-only CSP. Never loosen
  it to allow another host.
- **No references to the origin of this project** in any file or commit. Present it as a personal project.
- Never commit scenario data from `scenarios/private/` (gitignored). `scenarios/examples/` holds
  placeholder values only.
- `src/bioprocess/` never imports Streamlit. The UI (`app/`) never does model arithmetic.
- A model change goes into `MODEL.md` first, then code, then the reference tests.

## Layout
- `src/bioprocess/`: pure model package.
  - `models` (pydantic inputs), `suggest` (phase plan + suggestions), `simulate` (time stepping), `checks`, `summary`, `compare`;
  - `io/` (YAML, scenario store + autosave, CSV/Excel export, spreadsheet `.xlsx` import);
  - `defaults` (placeholder example).
- `app/`: Streamlit. `Home.py` is the router and sidebar. Pages live in `app/pages/`, and `app/ui/` holds state, charts and widgets.
  Widget keys carry a revision counter (`state.key()`); call `state.replace()` or `state.bump()` after structural changes.
- `web/`: the in-browser shell. `web/vendor.json` pins stlite, Pyodide and the wheels.
  `web/vendor/` is fetched by `scripts/vendor_runtime.py` and not committed. `web/spike/` is the runtime health check.
- `tests/`: pytest.

## How to run
```bash
uv sync --extra dev            # Python 3.13 venv
uv run pytest -q
./run.sh                       # in-browser app on http://localhost:8765 (fetches web/vendor/ on first run)
./run.sh spike/                # runtime health check page
uv run streamlit run app/Home.py --server.address 127.0.0.1   # native mode (dev / fallback)
```

## Gotchas
- Python is pinned to 3.13 to match stlite's Pyodide (0.29.x). Every dependency must exist as a
  Pyodide build or a pure-Python wheel. Add new ones to `web/vendor.json` and re-run the vendor script.
- PyPI wheels are pre-installed through stlite `archives` (`format: "wheel"`), not as URL
  requirements: micropip otherwise races to PyPI.
- A full page load boots Pyodide (~5 s with a warm cache). Keep heavy imports (openpyxl) lazy.
- `scripts/serve.py` serves only `web/`, plus read-only `.py` files from `app/` and `src/bioprocess/` and `/manifest.json`.
  A new Python source file is picked up automatically; any other new asset belongs in `web/`.
- In stlite, deep links open *Start here* (the URL is reset to `/`). Use sidebar navigation.
- Tests: `tests/test_against_sheet.py` (day-by-day parity with the original spreadsheet, bolus mode) and
  `tests/test_reference.py` (MODEL.md §5) are the regression tripwires.
