# M0 spike: stlite on localhost (2026-10-17)

**Verdict: PASS.** stlite is the primary runtime. Native Streamlit is the tested fallback.

The test page is `web/spike/` (`./run.sh spike/`). It was checked in the Claude desktop app's built-in browser.

| Check | Result |
|---|---|
| Runtime | Pyodide 0.29.3, Python 3.13.2, Streamlit 1.65.0 (stlite 1.11.0) |
| numpy, pandas, pydantic, pyyaml, plotly, openpyxl | All import and work: hourly array, pydantic validation (rejects `days=0`), YAML round-trip, xlsx written to bytes, Plotly chart rendered, download button |
| Compute | 49-row hourly table + checks in 15 ms |
| IndexedDB persistence (`/mnt`) | A counter file survives every reload (1 → 7) |
| Offline / local-only | Pyodide core + 33 prebuilt wheels and 6 PyPI wheels are vendored in `web/vendor/` (74 MB, sha256-checked, not committed). The Pyodide `indexURL` is `http://localhost:8765/vendor/pyodide/`, and micropip installs nothing from PyPI. |
| Enforced local-only | `scripts/serve.py` sends a CSP that allows only this origin. The app runs fully under it, with **zero blocked requests**: nothing tries to leave localhost. Streamlit telemetry is off. |
| Native fallback | `uv run streamlit run app/Home.py` is healthy in ~2 s and renders the scaffold page |

## Findings that change the plan

1. **Python 3.13, not 3.12.** stlite 1.11 ships Streamlit for Pyodide 0.29 / Python 3.13. `pyproject.toml` pins `>=3.13,<3.14`.
2. **PyPI wheels must be pre-installed.** If listed as URL requirements, micropip still resolved Streamlit's `protobuf` dependency from PyPI, because of a race in the resolver. Unpacking them with stlite's `archives` option (`format: "wheel"`) before micropip runs fixes it.
3. **stlite's worker is an inline `data:` script.** The CSP needs `data:` in `script-src`/`worker-src`. That is inline code, not a network source.
4. **Startup is slow: about 40 s per full page load** in the built-in browser.

| Stage | Time |
|---|---|
| Pyodide | 6 s |
| Unpack wheels | 3.6 s |
| Install | 7.5 s |
| Import Streamlit | 6 s |
| Server boot + first script run | 17 s |

Interactions after the boot are normal Streamlit reruns (fast); only a full reload pays this again. Mitigations to try in M2–M6:
- import openpyxl only when exporting;
- keep page modules light;
- measure in desktop Chrome or Safari, likely faster than the embedded pane.

If 40 s is unacceptable, the native fallback starts in ~2 s. Its trade-off: scenarios live in a local folder instead of browser storage.

## Files added in M0

- `pyproject.toml`, `src/bioprocess/__init__.py`, `app/Home.py`, `tests/test_smoke.py`
- `web/vendor.json` (the pinned runtime), `scripts/vendor_runtime.py`, `scripts/serve.py` (CSP server), `run.sh`
- `web/spike/` (spike page + app; kept as a runtime health check)
- `CLAUDE.md`, `README.md`
