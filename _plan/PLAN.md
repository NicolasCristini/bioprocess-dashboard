# Bioprocess Dashboard: build plan v2

**Status:** v2, revised after Nicolas's answers (2026-10-17). It awaits approval of v2 and answers to §10. No app code yet.
**What it is:** a personal project. It is a browser-based planner for batch → fed-batch → continuous (bleed & feed) cell-culture processes, and it replaces an earlier spreadsheet planner. The spreadsheet stays in use separately while the app is under development.
**Model spec:** [`../MODEL.md`](../MODEL.md) holds every parameter, equation, check and assumption. This plan does not repeat the formulas.

---

## 0. Decisions from Nicolas's answers (v1 → v2)

| # | Answer | What changes in the plan |
|---|---|---|
| 1, 2, 11 | Inputs stay in the user's browser, and the data is confidential. Anyone with the link uses the app with their own inputs. For now the example data comes from published papers. Later, real data means local use only, with no external server. | **Streamlit runs in the browser (stlite / Pyodide):** the Python runs client-side and no inputs reach any server. Scenarios persist in the browser (IndexedDB). The same code also runs fully offline on localhost. See §1–§2. |
| 3 | Hourly resolution, so the simulation can be watched evolving hour by hour | The simulation steps hourly (`steps_per_day = 24`). The Results page gets an **hour slider + play button**. Daily (`= 1`) stays available for parity tests. |
| 4 | Keep the limits | Hard caps: 6 phases, 120 days, 30 feed-regime days |
| 5, 12 | **Remove the target cell density. µ is an input for every phase.** | Batch and fed-batch: `X = X_s·e^(µτ)`. Continuous: `X = X_s·e^((µ−b)τ)`. End VCC becomes an output. The blank-target edge case is gone. |
| 6 | Feed ≠ bleed → warning. Volume > V_max or < V_min → block. Add V_min and V_max as inputs. | `V_min` and `V_max` are new Setup inputs. Volume outside the window stops the run at that step. Feed ≠ bleed is a warning (feed < bleed blocks). One point to confirm, in §10 Q1. |
| 7 | Keep parity with the sheet for v1. All model parameters and assumptions go in MODEL.md. | `MODEL.md` written. Parity is tested at daily resolution. |
| 8 | The sheet stays usable separately | No sync. Importing a downloaded sheet `.xlsx` stays optional. |
| 9 | Build the Compare page | Core milestone (M4) |
| 10 | Project files stay in this folder, with a private GitHub repo | `git init` here, plus a private repo `bioprocess-dashboard` |
| 13 | A personal project, with no reference to the project it came from | All earlier references removed from the project files: paths, sheet IDs, names. The repo contains none. |

**Parity holds with µ as the input.** I re-ran the scratch port. With the exact µ values (0.54302 / 0.54151 1/day) the reference plan gives the same numbers as the sheet:
- 8.717 L medium;
- 1.06 L max volume;
- 4.018E10 cells bled;
- 93.6 g wet biomass;
- 23.82 mM peak lactate.

At **hourly** resolution, everything is unchanged except peak lactate, which drops to 23.25 mM: the finer Euler step smooths the overshoot at the end of the fed-batch phase. MODEL.md §5 records both columns.

---

## 1. Stack: Streamlit **in the browser** (stlite) + Plotly

The privacy requirement changes the v1 recommendation. On a host, a normal Streamlit app keeps each user's inputs in *server* memory. That breaks the requirement that inputs stay in the browser.

| Option | Where inputs live | Shareable link | Fully local later | Code language | Verdict |
|---|---|---|---|---|---|
| Streamlit on a server (v1 plan) | Server memory | Yes | Yes (localhost) | Python | ✗ when hosted |
| React/TS client app (like the Cell-Culture-Analyzer example) | Browser (`localStorage`) | Yes (static files) | Yes | TypeScript: the model would be rewritten in TS | Possible, but loses Python and the pytest suite |
| **stlite**: Streamlit compiled to WebAssembly (Pyodide) | **Browser only**; nothing is sent anywhere | Yes, as static files | Yes: open it from localhost, or run `streamlit run` | **Python, the same code** | **✓ Recommended** |

**Why stlite:**
- It fits the example app's pattern (client-side parsing, browser storage, a saved-items database with load, delete, compare and export) while keeping one Python model that can be tested with pytest.
- The same `app/` folder runs two ways:
  - **in the browser** via a small `web/index.html` that mounts the app with stlite;
  - **natively** with `uv run streamlit run app/Home.py` on localhost, for the later confidential phase and for development.

**Costs and risks, checked in the M0 spike before anything else is built:**
- **First load.** The page downloads the Pyodide runtime and packages, roughly 10–30 MB. The browser caches it, so later visits are fast.
- **Packages.** Every dependency must be pure Python or ship as a Pyodide build. That holds for numpy, pandas, plotly, pydantic, pyyaml and openpyxl, and M0 confirms each one.
- **Browser storage.** It is per-origin: changing the URL or clearing site data loses saved scenarios. Hence the always-available YAML download/upload, and an "Export all" backup.

**Other choices (unchanged):**
- Plotly for charts;
- pydantic v2 for input models and validation;
- pandas for the time table;
- uv for the environment;
- Python 3.12, matching the Pyodide version stlite ships.

**Unlike the example app:** there are **no external API calls** (the example sends data to Gemini), no CDN-loaded analytics, and Streamlit usage stats are off (`browser.gatherUsageStats = false`).

---

## 2. Data, privacy and storage

- **Inputs** live in the Streamlit session, which with stlite is inside the browser tab.
- **Saved scenarios** are YAML files in a persistent IndexedDB mount (`/mnt/scenarios`, through stlite's `idbfsMountpoints`). They survive reloads and browser restarts on the same device and URL.
- **Portability:** every scenario can be downloaded and uploaded as YAML. *Export all* and *Import* move a set between devices or users.
- **"Clear my data"** in the sidebar wipes the IndexedDB mount.
- **Example data** in `scenarios/examples/` ships with the app. It is literature-based and labelled "example". Confidential scenarios are never committed: `scenarios/private/` is gitignored.
- **Later, confidential use:** run on localhost only, either natively or by serving the static build from `localhost`. Nothing changes in the code.

---

## 3. Architecture

```
bioprocess-dashboard/
├── CLAUDE.md                  # project map (M0)
├── MODEL.md                   # model spec: parameters, equations, checks, assumptions
├── README.md                  # what it is, run locally, privacy note
├── pyproject.toml             # uv; python 3.12
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
├── web/index.html             # stlite loader: mounts app/, src/, IndexedDB at /mnt
├── scenarios/examples/        # reference.yaml + other literature examples
└── tests/                     # see §6
```

The boundary rule from v1 still applies: `bioprocess` never imports Streamlit, and the UI never does arithmetic.

### 3.1 Data model (changes from v1)

```python
class Setup:      vessel_volume_L, initial_wv_L, v_min_L, v_max_L, seeding_density,
                  wet_biomass_g_per_L_at_1e6, steps_per_day=24
class Phase (discriminated union on `type`):
    BatchPhase:       days:int, mu:float
    FedBatchPhase:    days:int, mu:float, regime:str
    ContinuousPhase:  days:int, mu:float, feed_vvd: float|"suggested", bleed_vvd: float|"suggested"
```

- `target_vcc` and `mu_override` are gone. `µ` is required in every phase.
- Validators enforce the hard caps (6 / 120 / 30) and `V_min ≤ V0 ≤ V_max`.
- The equations are in MODEL.md §2.

### 3.2 Hourly simulation

- `simulate()` runs 120 d × 24 = up to 2,880 steps × 5 metabolites, in a few ms in native Python and well under a second in Pyodide.
- The result is a time table with `t_h`, `day`, phase and every MODEL.md quantity.
- Daily tables are derived by taking the rows at whole days, which avoids a second run.
- The parity tests call `steps_per_day = 1`.

---

## 4. UI flow

The sidebar shows:
- the active scenario;
- the ✓/⚠/⛔ status per step;
- **My scenarios** (the browser library), with open, save, duplicate, delete, download, upload and export all;
- Clear my data;
- a one-line privacy note: "Your inputs never leave this browser."

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
  - **Fed-batch:** duration, µ, regime;
  - **Continuous:** duration, µ, feed, bleed.
- µ is pre-filled from the previous phase, and the card shows the resulting end VCC and doubling time live.
- Continuous cards show the suggested bleed and suggested min. feed with a "use suggestion" toggle, plus the feed ≠ bleed warning stating the harvest per day.
- A timeline strip runs underneath.

**3 · Feed regimes.** A 30-day × A–D table, a bar preview and descriptions.

**4 · Results.**
- Key-number tiles and the issues panel. A ⛔ block shows a red banner: "run stopped at day X h Y: volume above V_max".
- **Hourly playback:** a time slider (hour resolution) and ▶/⏸, so all charts draw up to the chosen hour. A "state at t" card shows VCC, V, each metabolite, cumulative medium and biomass.
- Charts with phase bands, all on a time axis in hours or days:
  - VCC (log toggle);
  - metabolites with limit lines;
  - volume with the V_min/V_max band and the vessel line;
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

1. **Reference test.** `scenarios/examples/reference.yaml` must reproduce both columns of MODEL.md §5, daily and hourly.
2. **Sheet parity.**
   - Day-by-day agreement with the spreadsheet's Calculation tab at `steps_per_day = 1`, to `rel = 1e-9`.
   - The fixture is a CSV exported from the sheet, with targets converted to µ.
   - It is repeated for 2–3 more phase sequences: regime B, continuous → continuous, and µ = 0.
3. **Invariants**, at Δt = 1 and 1/24:
   - fresh medium = V_end + bleed + harvest;
   - b = µ ⇒ constant VCC;
   - a long continuous phase → `C*`;
   - cells produced identity;
   - VCC independent of Δt;
   - daily rows of the hourly run have VCC and volume identical to the daily run.
4. **Checks and edge cases:**

| Case | Behaviour |
|---|---|
| V > V_max (e.g. a large fed-batch regime) or V < V_min | ⛔ The run stops at that step. Partial results are shown, and the run is left out of Compare. |
| `V0` outside [V_min, V_max] | ⛔ input error |
| Feed ≠ bleed | ⚠ warning stating the harvest stream |
| Feed < bleed | ⛔ negative harvest |
| Fed-batch phase > 30 days, > 6 phases, > 120 days | ⛔ input error (hard caps) |
| Missing µ / duration / regime / D / b | ⛔ input error on that phase card |
| µ = 0, µ < 0 | Allowed: hold or decline. A negative µ shows an info note. |
| Perfusion concentration blank for a modelled metabolite | Metabolite blank from the continuous phase on, with a note naming the input |
| Metabolite reaches 0 | ⚠ "depleted at t", with the clip at 0 |

5. **Browser smoke test (M7):** load `web/index.html` in the built-in browser, run the reference scenario, save it, reload, and confirm it is still in My scenarios.

---

## 7. Deployment

- **Now:**
  - static files: `web/` plus the Python sources;
  - develop with `uv run streamlit run app/Home.py` on localhost;
  - test the in-browser build with `python -m http.server` on localhost.
- **Sharing a link, while the data is example data:** any static host works, because it only serves code; inputs never reach it.
  - **GitHub Pages from a private repo needs a paid GitHub plan.**
  - **Cloudflare Pages** or **Netlify** deploy from a private repo on their free tiers.
  - Another option is a separate public "build-only" repo.
  - No authentication is needed: no data is stored server-side.
- **Later, confidential:** local only, either natively or by serving the static build from localhost, with no external host. Option: package the app as a desktop app with `@stlite/desktop` (Electron) so colleagues can run it offline without Python.

---

## 8. Milestones

| # | Milestone | Content | Effort | Gate |
|---|---|---|---|---|
| M0 | Scaffold + stlite spike | git + private repo, uv project, CLAUDE.md, README. **Spike:** stlite page loading pydantic, pandas, plotly and openpyxl, writing a file to IndexedDB that survives a reload. | 0.5 d | Spike passes, or a fallback is chosen (§10 Q5) |
| M1 | Model + tests | models, simulate (Δt), suggest, checks, summary; reference, parity, invariant and edge tests | 1.5 d | All green; the CLI prints MODEL.md §5 |
| M2 | Input pages | Home, Setup (with V_min/V_max), Phase builder (µ per phase), Feed regimes | 1 d | The reference plan can be built from scratch in the UI |
| M3 | Results + hourly playback | Tiles, issues and blocks, charts with phase bands, slider and play, tables, CSV | 1–1.5 d | Matches the sheet at daily resolution; playback is smooth in the browser |
| M4 | Scenario library + Compare | IndexedDB store, YAML files, export all, Compare page | 1 d | Several scenarios survive a reload; overlay works |
| M5 | Data I/O | Excel export; optional sheet `.xlsx` import | 0.5 d | Imported sheet = identical results |
| M6 | First-user polish | Help, tooltips with units, assumptions panel, design pass | 0.5–1 d | Usable without a walkthrough |
| M7 | Static build + share | Build, browser smoke test, deploy to the chosen static host | 0.5 d | The link works and data stays local (network tab shows no input traffic) |

**Total: about 6.5–8 working days.**

---

## 9. Answers and comments from Nicolas (2026-10-17, condensed)

Folded into §0. Point 13 was applied by rewording the plan, so this file no longer holds any earlier project references.

---

## 10. Remaining open questions

1. **Feed ≠ bleed: does volume change?** The sheet (and v1 parity) keeps the volume constant through a cell-free harvest `D − b`. Feed ≠ bleed then only means there is a harvest stream, and V_min/V_max can only be hit by fed-batch boluses.
   - Or should the model have **no separate harvest**, so that `dV/dt = (D − b)·V` and feed ≠ bleed makes the volume rise or fall until the V_min/V_max block? That second reading breaks parity, so it would be a v1.1 option.
   - **Plan default: keep the harvest (parity).**
2. **V_min / V_max defaults.** Placeholders are 0.5 L and 2.0 L (= the vessel). Do you have real values?
3. **Static host for the shareable link.** Cloudflare Pages or Netlify (free, private repo), GitHub Pro for Pages, or no hosted link yet (localhost only)?
4. **Hourly bolus timing.** One bolus at the end of each fed-batch day, as the sheet does (plan default)? Or spread evenly over the day?
5. **If the stlite spike fails** (a package doesn't load in Pyodide): fall back to native Streamlit on localhost only? That still meets "data stays local", but with no shareable link.
