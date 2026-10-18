# CLAUDE.md: bioprocess-dashboard

A personal project: a browser-based planner for batch → fed-batch → continuous (bleed & feed)
cell-culture processes. Python model + Streamlit UI that runs **inside the browser** (stlite /
Pyodide), published as a **static site with a shareable link**. There is no server logic: each visitor's
inputs and saved scenarios stay in their own browser.

## Read first
- `MODEL.md`: the model spec (parameters, equations, checks, assumptions, reference numbers). Code follows it.
- `_plan/PLAN.md`: the build plan and milestones. `_plan/M0_SPIKE.md`: runtime findings.

## Non-negotiable rules
- **Inputs are confidential and never leave the visitor's browser.** Use static hosting only: no backend, no
  server-side state, no external API calls, no telemetry, no CDN assets. The page carries a this-origin-only
  CSP (`<meta>`, defined in `scripts/build_site.py`) that binds the Python worker too. Never loosen it to allow
  another host.
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
./run.sh                       # build dist/ and preview it on http://localhost:8765/ (fetches web/vendor/ on first run)
./run.sh --base /bioprocess-dashboard/   # rehearse the GitHub Pages sub-path
python3 scripts/build_site.py --base /<repo>/   # the static site, for any host
uv run streamlit run app/Home.py --server.address 127.0.0.1   # native mode (dev / fallback)
```

## Gotchas
- Python is pinned to 3.13 to match stlite's Pyodide (0.29.x). Every dependency must exist as a
  Pyodide build or a pure-Python wheel. Add new ones to `web/vendor.json` and re-run the vendor script.
- PyPI wheels are pre-installed through stlite `archives` (`format: "wheel"`), not as URL
  requirements: micropip otherwise races to PyPI.
- A full page load boots Pyodide (~5 s with a warm cache). Keep heavy imports (openpyxl) lazy.
- `scripts/build_site.py` copies `app/` and `src/bioprocess/`, writes `manifest.json`, fills the `web/index.html`
  template (base path + CSP) into `index.html` and `404.html`, and copies the runtime. `scripts/serve.py` is a plain
  static preview: it adds no headers or logic.
- Every URL in the page shell must stay relative to `<base href>`: the site runs under a sub-path on GitHub Pages.
- Browser storage is the IndexedDB mount `/bioprocess-planner`. It must be top-level (a nested `/mnt/...` mount fails
  at boot) and unique to the app, because all Pages sites of one account share one origin.
- In stlite, deep links open *Start here* (the URL is reset to the base). Use sidebar navigation.
- `.github/workflows/site.yml` runs the tests on every push. It builds and deploys to Pages only when the repo
  variable `DEPLOY_PAGES` is `true`.
- Tests: `tests/test_against_sheet.py` (day-by-day parity with the original spreadsheet, bolus mode) and
  `tests/test_reference.py` (MODEL.md §5) are the regression tripwires.
