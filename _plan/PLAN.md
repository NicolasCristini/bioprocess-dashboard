# Bioprocess Dashboard: build plan v3

**Status:** v3, approved. **M0–M7 done (2026-10-18).** See [`M0_SPIKE.md`](M0_SPIKE.md) for runtime findings, and §11 for the delivery notes.
**What it is:** a personal project. It is a browser-based planner for batch → fed-batch → continuous (bleed & feed) cell-culture processes, and it replaces an earlier spreadsheet planner. The spreadsheet stays in use separately while the app is under development.
**Model spec:** [`../MODEL.md`](../MODEL.md) (v1.1) holds every parameter, equation, check and assumption. This plan does not repeat the formulas.

---

## 0. Decisions from Nicolas's answers (v1 → v3)

| # | Answer | What changes in the plan |
|---|---|---|
| 1, 2, 11 | Inputs stay in the user's browser, and the data is confidential. For now the example data comes from published papers. Later, real data means local use only, with no external server. | **Streamlit runs in the browser (stlite / Pyodide), served from localhost:** the Python runs client-side and scenarios persist in the browser (IndexedDB). See §1–§2. |
| 3 | Hourly resolution, so the simulation can be watched evolving hour by hour | The simulation steps hourly (`steps_per_day = 24`). The Results page gets an **hour slider + play button**. Daily (`= 1`) stays available for parity tests. |
| 4 | Keep the limits | Hard caps: 6 phases, 120 days, 30 feed-regime days |
| 5, 12 | **Remove the target cell density. µ is an input for every phase.** | Batch and fed-batch: `X = X_s·e^(µτ)`. Continuous: `X = X_s·e^((µ−b)τ)`. End VCC becomes an output. The blank-target edge case is gone. |
| 6 | Feed ≠ bleed → warning. Volume > V_max or < V_min → block. Add V_min and V_max as inputs. | `V_min` and `V_max` are new Setup inputs. Volume outside the window stops the run at that step. Feed ≠ bleed is a warning (feed < bleed blocks). |
| 7 | Keep parity with the sheet for v1. All model parameters and assumptions go in MODEL.md. | `MODEL.md` written. Since §10.4, the user-facing model differs from the sheet in fed-batch phases, so parity is kept through an internal **sheet-parity mode** (daily, bolus) that is tested day by day (§6). |
| 8 | The sheet stays usable separately | No sync. Importing a downloaded sheet `.xlsx` stays optional. |
| 9 | Build the Compare page | Core milestone (M4) |
| 10 | Project files stay in this folder, with a private GitHub repo | `git init` here, plus a private repo `bioprocess-dashboard` |
| 13 | A personal project, with no reference to the project it came from | All earlier references removed from the project files: paths, sheet IDs, names. The repo contains none. |
| §10.1 | Continuous phases default to feed = bleed, with no dV/dt | `D` is linked to `b` by default, so there is no harvest and the volume is constant. The user can unlink `D` to go above `b`; a harvest `D − b` then keeps the volume constant. Volume is never integrated in continuous mode. |
| §10.2 | All values are placeholders | MODEL.md says so up front. The UI shows a "placeholder values" note on the example scenario. |
| §10.3 | Localhost only, no shareable link | No hosting. The app is served from localhost: the stlite build via `run.sh` (http://localhost:8765), or native Streamlit. §7 and M7 are cut down accordingly. |
| §10.4 | Fed-batch uses a feeding rate (a constant flow over the day), not a bolus | The regime's daily % of V0 is delivered as a flow, step by step. Results show the **volume added per day**. The sheet's bolus rule survives only as an internal test mode (§6). |
| §10.5 | If stlite fails, fall back to native Streamlit on localhost | Gate at M0 |

**Effect on the numbers** (scratch port of MODEL.md v1.1, reference plan; full table in MODEL.md §5):

| | Example plan (app default: hourly, flow feeding, feed = bleed) | Same, with feed = suggested 0.722 VVD | Sheet-parity mode (daily, bolus, 0.722 VVD) |
|---|---|---|---|
| Total fresh medium | 6.80 L | 8.717 L | 8.717 L (= sheet) |
| Harvest | 0 L | 1.92 L | 1.92 L |
| Max volume / cells bled / wet biomass | 1.06 L / 4.018E10 / 93.6 g | same | same |
| Peak / final lactate | **26.66 / 26.66 mM ⚠** | 22.88 / 20.00 mM | 23.82 / 20.00 mM (= sheet) |
| Min glucose | **0.56 mM ⚠** | 6.64 mM | 6.64 mM |

- With the new default feed = bleed (0.54 VVD), the continuous phase **does not supply enough medium** for 7E6 cells/mL. Lactate settles above its 20 mM limit and glucose falls below its 5 mM limit.
- The app flags this through the "feed below the suggested min." warning and offers the 0.722 VVD suggestion, which creates a 1.9 L harvest stream.
- This is correct behaviour for the placeholder values, not a bug.
- The fed-batch feed adds 0.030 L per day on days 3 and 4 in every column.

---

## 1. Stack: Streamlit **in the browser** (stlite) + Plotly, on localhost

The app runs **on localhost only** (§10.3). stlite stays the primary choice because it is the one option where inputs and saved scenarios live in the browser's own storage (§9 answer 2). Native Streamlit on localhost is the fallback (§10.5): data stays on the machine, but it lives in the local Python process and a local folder instead of the browser.

| Option | Where inputs and saved scenarios live | Code language | Verdict |
|---|---|---|---|
| Native Streamlit on localhost | Local Python process + a local folder | Python | Fallback (§10.5) |
| React/TS client app (like the Cell-Culture-Analyzer example) | Browser (`localStorage`) | TypeScript: the model would be rewritten in TS | Loses Python and the pytest suite |
| **stlite**: Streamlit compiled to WebAssembly (Pyodide), served from localhost | **Browser only** (IndexedDB) | **Python, the same code** | **✓ Recommended** |

**Why stlite:**
- It fits the example app's pattern (client-side parsing, browser storage, a saved-items database with load, delete, compare and export) while keeping one Python model that can be tested with pytest.
- The same `app/` folder runs two ways:
  - **in the browser** via a small `web/index.html` that mounts the app with stlite;
  - **natively** with `uv run streamlit run app/Home.py` on localhost, for the later confidential phase and for development.

**Costs and risks, checked in the M0 spike before anything else is built:**
- **First load.** The page loads the Pyodide runtime and packages, roughly 10–30 MB, served from the local folder so it works offline. The browser caches it, so later visits are fast.
- **Packages.** Every dependency must be pure Python or ship as a Pyodide build. That holds for numpy, pandas, plotly, pydantic, pyyaml and openpyxl, and M0 confirms each one.
- **Browser storage.** It is per-origin: changing the URL or clearing site data loses saved scenarios. A fixed port (`http://localhost:8765`) keeps the origin stable. YAML download/upload and an "Export all" backup are always available.

**Other choices (unchanged):**
- Plotly for charts;
- pydantic v2 for input models and validation;
- pandas for the time table;
- uv for the environment;
- Python 3.13, matching the Pyodide version stlite ships (0.29.x; confirmed in M0).

**Unlike the example app:** there are **no external API calls** (the example sends data to Gemini), no CDN-loaded analytics, and Streamlit usage stats are off (`browser.gatherUsageStats = false`).

---

## 2. Data, privacy and storage

- **Inputs** live in the Streamlit session, which with stlite is inside the browser tab.
- **Saved scenarios** are YAML files in a persistent IndexedDB mount (`/mnt/scenarios`, through stlite's `idbfsMountpoints`). They survive reloads and browser restarts on the same device and URL.
- **Portability:** every scenario can be downloaded and uploaded as YAML. *Export all* and *Import* move a set between devices or users.
- **"Clear my data"** in the sidebar wipes the IndexedDB mount.
- **Example data** in `scenarios/examples/` ships with the app. It is literature-based and labelled "example". Confidential scenarios are never committed: `scenarios/private/` is gitignored.
- **Local only, now and later:** the app is always served from localhost, so nothing changes when real data arrives.

---

## 3. Architecture

```
bioprocess-dashboard/
├── CLAUDE.md                  # project map (M0)
├── MODEL.md                   # model spec: parameters, equations, checks, assumptions
├── README.md                  # what it is, run locally, privacy note
├── pyproject.toml             # uv; python 3.13
├── _plan/PLAN.md              # this file
├── src/bioprocess/            # pure model, no UI imports
│   ├── models.py              # Setup, Metabolite, FeedRegime, Phase (Batch|FedBatch|Continuous), Scenario
│   ├── simulate.py            # simulate(scenario, steps_per_day=24) -> SimResult (time table + phase table)
│   ├── suggest.py             # suggested bleed (= µ), suggested min. perfusion rate
│   ├── checks.py              # block/warning/info issues (MODEL.md §3)
│   ├── summary.py             # key numbers, per-phase summary
│   ├── compare.py             # align N SimResults on time; key-number table + deltas
│   └── io/
│       ├── scenario_file.py   # YAML/JSON save/load, schema_version
│       ├── store.py           # scenario library on a directory (IndexedDB mount in the browser, local folder natively)
│       ├── export.py          # CSV, Excel (values)
│       └── sheet_import.py    # optional: downloaded spreadsheet .xlsx → Scenario (target VCC converted to µ)
├── app/                       # Streamlit (runs in stlite and natively)
│   ├── Home.py
│   ├── pages/1_Setup.py  2_Phases.py  3_Feed_regimes.py  4_Results.py  5_Compare.py
│   └── ui/                    # charts.py (Plotly), state.py, widgets.py
├── web/index.html             # stlite loader: mounts app/, src/, IndexedDB at /mnt (Pyodide assets vendored for offline use)
├── run.sh                     # serves web/ on http://localhost:8765 and opens the browser
├── scenarios/examples/        # example.yaml (app default) + sheet_parity.yaml + other placeholder examples
└── tests/                     # see §6
```

The boundary rule from v1 still applies: `bioprocess` never imports Streamlit, and the UI never does arithmetic.

### 3.1 Data model (changes from v1)

```python
class Setup:      vessel_volume_L, initial_wv_L, v_min_L, v_max_L, seeding_density,
                  wet_biomass_g_per_L_at_1e6, steps_per_day=24
class Phase (discriminated union on `type`):
    BatchPhase:       days:int, mu:float
    FedBatchPhase:    days:int, mu:float, regime:str          # regime = daily volume (% of V0), fed as a flow
    ContinuousPhase:  days:int, mu:float, bleed_vvd: float|"suggested", feed_vvd: float|"= bleed"
```

- `target_vcc` and `mu_override` are gone. `µ` is required in every phase.
- `feed_vvd` defaults to `"= bleed"` (linked). A number unlinks it.
- `simulate(scenario, steps_per_day=24, fedbatch_feeding="flow")`. `"bolus"` is the internal sheet-parity mode (MODEL.md §2.6), used only by tests.
- Validators enforce the hard caps (6 / 120 / 30) and `V_min ≤ V0 ≤ V_max`.
- The equations are in MODEL.md §2.

### 3.2 Hourly simulation

- `simulate()` runs 120 d × 24 = up to 2,880 steps × 5 metabolites, in a few ms in native Python and well under a second in Pyodide.
- The result is a time table with `t_h`, `day`, phase and every MODEL.md quantity.
- Daily tables are derived by taking the rows at whole days, which avoids a second run.
- The parity tests call `steps_per_day = 1, fedbatch_feeding="bolus"`.

---

## 4. UI flow

The sidebar shows:
- the active scenario;
- the ✓/⚠/⛔ status per step;
- **My scenarios** (the browser library), with open, save, duplicate, delete, download, upload and export all;
- Clear my data;
- a one-line privacy note: "Your inputs never leave this browser."
- a "placeholder values" badge while the example scenario is active.

**Home.** What the tool predicts, a 5-step guide, an Assumptions panel (from MODEL.md §4), and three buttons: *Start from example*, *Open my scenarios*, *Upload a scenario file*.

**1 · Setup.**
- The vessel and working-volume form, which now includes **V_min and V_max**.
- A sketch of the volume window shows V_min ≤ V0 ≤ V_max < vessel.
- Seeding density and the wet-biomass factor (marked placeholder).
- The metabolite table.

**2 · Phases.**
- One card per phase, up to 6, with ↑ ↓ ✕ and **+ Add phase**.
- Fields per type:
  - **Batch:** duration, µ;
  - **Fed-batch:** duration, µ, regime. The card shows the **volume added per day** (L) and the total for the phase.
  - **Continuous:** duration, µ, bleed, and feed with a **"feed = bleed" lock**, on by default.
- µ is pre-filled from the previous phase, and the card shows the resulting end VCC and doubling time live.
- Continuous cards show the suggested bleed and the suggested min. feed.
  - If the min. feed is above the bleed, the card warns that metabolites will leave their limits, with a "use suggested feed" button. That button unlocks feed = bleed and states the harvest per day.
- A timeline strip runs underneath.

**3 · Feed regimes.** A 30-day × A–D table (daily volume as % of V0, fed as a constant flow), a bar preview in L/day for the current V0, and descriptions.

**4 · Results.**
- Key-number tiles and the issues panel. A ⛔ block shows a red banner: "run stopped at day X h Y: volume above V_max".
- **Hourly playback:** a time slider (hour resolution) and ▶/⏸, so all charts draw up to the chosen hour. A "state at t" card shows VCC, V, each metabolite, cumulative medium and biomass.
- Charts with phase bands, all on a time axis in hours or days:
  - VCC (log toggle);
  - metabolites with limit lines;
  - volume with the V_min/V_max band and the vessel line;
  - fed-batch volume added per day (bars);
  - cumulative medium, harvest and bleed;
  - cumulative wet biomass in the bleed.
- Tabs: per-phase summary, metabolite check, time table (hourly/daily toggle).
- Downloads: CSV and Excel.

**5 · Compare.**
- Pick 2–6 scenarios from My scenarios.
- A side-by-side key-numbers table, with deltas against a chosen baseline.
- All charts overlaid, one colour per scenario, with the shared hour slider.
- Blocked runs are listed but not overlaid.

**Design pass (M6):** the `graphic` agent. Phase colours: orange = fed-batch, blue = continuous.

---

## 5. Data I/O

| Direction | Format | Milestone |
|---|---|---|
| Scenario save/load (browser library + file) | YAML / JSON | M4 core |
| Export results | CSV (hourly or daily), Excel (inputs, time table, per-phase, key numbers) | M3 / M5 |
| Import from the spreadsheet planner | `.xlsx` downloaded from it. Target VCC is converted to `µ = ln(target/start)/days`. | M5, optional |

All file handling happens in the browser: uploads are read in place, downloads are generated in place.

---

## 6. Validation and tests (`uv run pytest`)

1. **Reference test.** The reference plan must reproduce all three columns of MODEL.md §5: the example plan, the plan with the suggested feed, and sheet parity.
2. **Sheet parity** (internal mode `fedbatch_feeding="bolus"`, `steps_per_day = 1`, explicit feed).
   - Day-by-day agreement with the spreadsheet's Calculation tab, to `rel = 1e-9`.
   - The fixture is a CSV exported from the sheet, with targets converted to µ.
   - It is repeated for 2–3 more phase sequences: regime B, continuous → continuous, and µ = 0.
3. **Invariants**, at Δt = 1 and 1/24:
   - fresh medium = V_end + bleed + harvest;
   - b = µ ⇒ constant VCC;
   - a long continuous phase → `C*`;
   - cells produced identity;
   - VCC independent of Δt;
   - daily rows of the hourly run have VCC identical to the daily run;
   - volume at the end of each day is identical in both feeding modes;
   - D = b ⇒ harvest = 0.
4. **Checks and edge cases:**

| Case | Behaviour |
|---|---|
| V > V_max (e.g. a large fed-batch regime) or V < V_min | ⛔ The run stops at that step. Partial results are shown, and the run is left out of Compare. |
| `V0` outside [V_min, V_max] | ⛔ input error |
| Feed > bleed (unlocked) | ⚠ warning stating the harvest stream |
| Feed below the suggested min. (incl. the default feed = bleed) | ⚠ warning naming the metabolite and its steady state |
| Feed < bleed | ⛔ negative harvest |
| Fed-batch phase > 30 days, > 6 phases, > 120 days | ⛔ input error (hard caps) |
| Missing µ / duration / regime / D / b | ⛔ input error on that phase card |
| µ = 0, µ < 0 | Allowed: hold or decline. A negative µ shows an info note. |
| Perfusion concentration blank for a modelled metabolite | Metabolite blank from the continuous phase on, with a note naming the input |
| Metabolite reaches 0 | ⚠ "depleted at t", with the clip at 0 |

5. **Browser smoke test (M7):**
   - open `http://localhost:8765` in the built-in browser;
   - run the example, save it, reload, and confirm it is still in My scenarios;
   - confirm the network tab shows no requests leaving localhost.

---

## 7. Deployment: localhost only

- **No hosting and no shareable link** (§10.3).
- **Run:** `./run.sh` serves `web/` on `http://localhost:8765` and opens the browser. The Pyodide runtime and wheels are vendored into `web/`, so it runs offline.
- **Develop:** `uv run streamlit run app/Home.py`. This is also the fallback mode if stlite fails (§10.5). In that mode, scenarios are saved in the gitignored `scenarios/private/`.
- No authentication is needed: nothing listens beyond localhost (bound to `127.0.0.1`).
- **Possible later:** package it as a desktop app with `@stlite/desktop`, so a colleague can run it offline without Python. Only if asked.

---

## 8. Milestones

| # | Milestone | Content | Effort | Gate |
|---|---|---|---|---|
| M0 | Scaffold + stlite spike | uv project, CLAUDE.md, README (the repo exists already). **Spike:** a localhost stlite page that loads pydantic, pandas, plotly and openpyxl offline and writes a file to IndexedDB that survives a reload. | 0.5 d | Spike passes → stlite; fails → native Streamlit (§10.5) |
| M1 | Model + tests | models, simulate (Δt, flow/bolus feeding), suggest, checks, summary; reference, parity, invariant and edge tests | 1.5 d | All green; the CLI prints the three columns of MODEL.md §5 |
| M2 | Input pages | Home, Setup (with V_min/V_max), Phase builder (µ per phase), Feed regimes | 1 d | The reference plan can be built from scratch in the UI |
| M3 | Results + hourly playback | Tiles, issues and blocks, charts with phase bands, volume-per-day bars, slider and play, tables, CSV | 1–1.5 d | Matches MODEL.md §5; playback is smooth in the browser |
| M4 | Scenario library + Compare | IndexedDB store, YAML files, export all, Compare page | 1 d | Several scenarios survive a reload; overlay works |
| M5 | Data I/O | Excel export; optional sheet `.xlsx` import | 0.5 d | Imported sheet = identical results |
| M6 | First-user polish | Help, tooltips with units, assumptions panel, design pass | 0.5–1 d | Usable without a walkthrough |
| M7 | Local launch | `run.sh`, vendored offline assets, browser smoke test | 0.25 d | Runs offline from localhost; no requests leave the machine |

**Total: about 6–7.5 working days.**

---

## 9. Answers and comments from Nicolas (2026-10-17, condensed)

Folded into §0. Point 13 was applied by rewording the plan, so this file no longer holds any earlier project references.

---

## 10. Open questions (v2), all answered

1. **Feed ≠ bleed: does volume change?** The sheet (and v1 parity) keeps the volume constant through a cell-free harvest `D − b`. Feed ≠ bleed then only means there is a harvest stream, and V_min/V_max can only be hit by fed-batch boluses.
   - Or should the model have **no separate harvest**, so that `dV/dt = (D − b)·V` and feed ≠ bleed makes the volume rise or fall until the V_min/V_max block? That second reading breaks parity, so it would be a v1.1 option.
   - **Plan default: keep the harvest (parity).**
2. **V_min / V_max defaults.** Placeholders are 0.5 L and 2.0 L (= the vessel). Do you have real values?
3. **Static host for the shareable link.** Cloudflare Pages or Netlify (free, private repo), GitHub Pro for Pages, or no hosted link yet (localhost only)?
4. **Hourly bolus timing.** One bolus at the end of each fed-batch day, as the sheet does (plan default)? Or spread evenly over the day?
5. **If the stlite spike fails** (a package doesn't load in Pyodide): fall back to native Streamlit on localhost only? That still meets "data stays local", but with no shareable link.

### Answers

1. For current simplifation let's now consider continuous phase with feed = bleed as default. So we avoid dV/dt calculation complexity. 
2. All data are placeholders for now. 
3. local host only, no shareable link.
4. For current simplifation let's consider feeding rate instead of feeding bolus. (constant feeding as small flow over the all day). Calculate and show from there the volume added every day.  
5. If stlite fails, fallback to native Streamlit on localhost only.


---

## 11. Delivery notes (2026-10-18)

| Milestone | Delivered |
|---|---|
| M0 | Offline stlite runtime, CSP server, spike. |
| M1 | `bioprocess` package. Day-by-day parity with 4 spreadsheet scenarios at rel 1e-9 (sheet-parity mode). MODEL.md §5 reproduced. CLI `python -m bioprocess`. |
| M2 | Start here, Setup (V_min/V_max, metabolite editor), Phase builder (µ per phase, feed = bleed lock, suggested feed button, timeline), Feed regimes. |
| M3 | Results: key numbers, checks, 6 charts with phase bands and an hour marker, the state at a chosen hour, Plotly playback (client-side frames), per-phase / metabolite / time tables, CSV + Excel. |
| M4 | Scenario library (browser IndexedDB, or a local folder natively), save / save as / open / delete / zip backup, reload-safe autosave, Compare (Δ% vs baseline, overlays, blocked runs left out). |
| M5 | Excel export; spreadsheet-planner `.xlsx` import (target → µ conversion, suggestion links kept). |
| M6 | Light design pass (theme colour, layout fixes, tooltips, assumptions panel). The `graphic` agent was not used. |
| M7 | `run.sh`; in-browser checks: boot, results, save + reload persistence, download under CSP. |

**Tests:** 56, covering the model, parity, invariants, edge cases, I/O, import and headless page tests.

**Known limitations:**
- In the browser build, deep links open *Start here*.
- Playback speed has only been checked in the embedded pane, which throttles when hidden.
- The console shows a harmless "Download Button fetch error" (see M0_SPIKE.md).
