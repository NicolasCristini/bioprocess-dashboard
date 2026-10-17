# MODEL.md: Bioprocess Phase Planner model

The single reference for every model parameter, equation and assumption used by the dashboard.
Change the model here first, then in `src/bioprocess/`, and update the reference tests.

**Model version:** 1.1 (2026-10-17)
- µ is an input per phase.
- Fed-batch feeding is a constant flow.
- In continuous phases, feed = bleed by default.
- The model matches the original spreadsheet only in its internal *sheet-parity mode* (§2.6).

**Status:** specification. The code in `src/bioprocess/` must follow this file.

**All numeric values are placeholders for development.** They are example values taken from published literature, or round stand-ins, and will be replaced by measured values later.

---

## 1. Parameters

### 1.1 Setup

| Symbol | Parameter | Default | Unit | Notes |
|---|---|---|---|---|
| `V_vessel` | Vessel volume (total) | 2.0 | L | |
| `V0` | Initial working volume | 1.0 | L | Must satisfy `V_min ≤ V0 ≤ V_max ≤ V_vessel` |
| `V_min` | Minimum working volume | 0.5 | L | The run is **blocked** if V drops below it |
| `V_max` | Maximum working volume | 2.0 | L | The run is **blocked** if V exceeds it |
| `X_seed` | Seeding density (t = 0) | 8.0E5 | cells/mL | |
| `k_wb` | Wet biomass at 1E6 cells/mL | 2.0 | g/L | Wet biomass is assumed to scale linearly with VCC |
| `steps_per_day` | Time resolution | 24 (hourly) | 1/day | 1 = daily |

### 1.2 Metabolites (one row each; the list can be extended)

| Parameter | Unit | Notes |
|---|---|---|
| `kind` | consumed / produced | sets `sign = −1` (consumed) or `+1` (produced) |
| `q` | 1E-11 mmol/cell/h | specific consumption/production rate; blank = not modelled |
| `limit` | mM | consumed: minimum to keep; produced: maximum tolerated |
| `C_batch` | mM | concentration in the batch (initial) medium |
| `C_fb` | mM | concentration in the fed-batch feed |
| `C_perf` | mM | concentration in the perfusion medium |

Defaults:

| Metabolite | kind | q | limit | C_batch | C_fb | C_perf |
|---|---|---|---|---|---|---|
| Glucose | consumed | 7.9 | 5 | 25 | 250 | 25 |
| Lactate | produced | 8.6 | 20 | 0 | 0 | 0 |
| Glutamine | consumed | — | 0.5 | — | — | — |
| Glutamate | consumed | — | 0.5 | — | — | — |
| Ammonia | produced | — | 5 | — | 0 | 0 |

### 1.3 Phases (1–6 phases; total duration ≤ 120 days)

| Type | Inputs | Unit |
|---|---|---|
| Batch | duration `T` (whole days), specific growth rate `µ` | d, 1/day |
| Fed-batch | `T`, `µ`, feed regime | d, 1/day, — |
| Continuous | `T`, `µ`, bleed rate `b`, perfusion (feed) rate `D` | d, 1/day, VVD, VVD |

- `µ` is required in every phase. The UI pre-fills it with the previous phase's `µ`. `µ = 0` holds VCC constant in batch and fed-batch phases.
- In continuous phases, `b` defaults to the suggested bleed (`= µ`), and **`D` defaults to `b` (linked)**. The user can unlink `D` and enter a larger value; see §3.

### 1.4 Feed regimes (fed-batch)

For each phase day `d = 1…30` and each regime A–D: the **feed volume added on that day, as % of the initial working volume `V0`**. It is delivered as a constant flow over the whole day (§2.2).

| Regime | Default |
|---|---|
| A | 3 %/day on days 1–2 |
| B | 2 %/day every day |
| C | 5 % on every 2nd day |
| D | custom (empty) |

### 1.5 Hard limits

- 6 phases;
- 120 days in total;
- 30 feed-regime days.

A fed-batch phase longer than 30 days is a validation error.

---

## 2. Equations

Time `t` is in days. The step is `Δt = 1/steps_per_day`. Step `n` covers `(t_{n-1}, t_n]`. A step at a phase boundary belongs to the phase that ends there. `τ = t − t_phase_start` is the time in the phase. Phase day `d = ⌈τ⌉`, so day 1 covers τ ∈ (0, 1]. `X_s` is the VCC at the start of the phase: the VCC at the end of the previous phase, or `X_seed` for phase 1.

### 2.1 Cell density

| Phase | VCC(τ) |
|---|---|
| Batch, fed-batch | `X_s · exp(µ·τ)` |
| Continuous | `X_s · exp((µ − b)·τ)` |

This is exact at any `Δt`. The step-average VCC is `X̄_n = (X_{n-1} + X_n)/2`.

### 2.2 Volumes and flows (per step)

| Quantity | Batch | Fed-batch | Continuous |
|---|---|---|---|
| Fed-batch feed `F_n` (L) | 0 | `regime[d]/100 · V0 · Δt` (a constant flow over phase day `d`) | 0 |
| Perfusion feed `I_n` (L) | 0 | 0 | `D · V_{n-1} · Δt` |
| Bleed `J_n` (L) | 0 | 0 | `b · V_{n-1} · Δt` |
| Harvest `H_n` (L, cell-free) | 0 | 0 | `I_n − J_n` (= 0 with the default `D = b`) |
| Volume `V_n` | `V_{n-1}` | `V_{n-1} + F_n` | `V_{n-1}` (constant) |
| Cells bled | 0 | 0 | `J_n · 1000 · X̄_n` |

- **Volume added per day** (fed-batch) = `Σ F_n` over that day = `regime[d]/100 · V0`. It is reported in the results.
- Cumulative values:
  - fresh medium: `V0 + ΣF + ΣI`;
  - bleed: `ΣJ`;
  - harvest: `ΣH`;
  - cells bled: `Σ(cells bled)`.

### 2.3 Metabolites (per metabolite with `q` given)

The volumetric rate is `r_n = sign · q · 24E-8 · X̄_n` in mM/day. This comes from 1E-11 mmol/cell/h × 24 h/day × cells/mL × 1000 mL/L.

| Phase | `C_n` |
|---|---|
| Batch | `max(0, C_{n-1} + r_n·Δt)` |
| Fed-batch | `C_mix = (C_{n-1}·V_{n-1} + C_fb·F_n) / (V_{n-1} + F_n)`; `C_n = max(0, C_mix + r_n·Δt)` |
| Continuous (D > 0) | `max(0, C* + (C_{n-1} − C*)·exp(−D·Δt))`, with `C* = C_perf + r_n/D` (exact for constant `r_n` over the step) |

- At `t = 0`, `C = C_batch`.
- If `C_perf` is blank for a modelled metabolite, its value becomes blank from the first continuous step onwards.
- `C*` is the steady state a continuous phase approaches. With the default `D = b = µ`, it is `C_perf + r/µ`.

### 2.4 Suggestions (continuous phases)

- **Suggested bleed** = `µ`. This holds VCC constant.
- **Suggested min. perfusion rate** = `max(b, max_m [ q_m · max(X_s, X_e) · 24E-8 / |limit_m − C_perf,m| ])`.
  - The max over metabolites only counts a metabolite when `sign·(limit − C_perf) > 0`. `X_e` is the VCC at the end of the phase.
  - This is advice, not the default.
  - If it exceeds `b`, the UI says that `D = b` will not keep the metabolites within their limits. It offers to set `D` to the suggestion, which creates a harvest stream `D − b`.

### 2.5 Outputs

- Wet biomass (g/L) = `X / 1E6 · k_wb`.
- Wet biomass in the reactor (g) = that value × `V`.
- Wet biomass in the bleed (g, cumulative) = cum. cells bled · `k_wb` / 1E9.
- Cells inoculated = `X_seed · V0 · 1000`.
- Cells at end = `X_end · V_end · 1000`.
- **Cells produced** = cells at end + cells bled − cells inoculated.
- **Total wet biomass produced** = cells produced · `k_wb` / 1E9.

### 2.6 Sheet-parity mode (internal, for tests only)

`simulate(..., fedbatch_feeding="bolus")` replaces the §2.2–2.3 fed-batch rows with the spreadsheet's rule:
- the day-`d` volume is added as one bolus at the end of phase day `d`;
- it is mixed in at the next step: `C_mix = (C_{n-1}·(V_{n-1} − F_{n-1}) + C_fb·F_{n-1}) / V_{n-1}`.

With `steps_per_day = 1` and explicit `D`, this reproduces the original spreadsheet day by day. It is not shown in the UI.

---

## 3. Checks

| Check | Level | Rule |
|---|---|---|
| Volume window | **block** | If `V < V_min` or `V > V_max` at any step, the run stops at that step. Results are shown only up to that point, marked invalid, and left out of comparisons. With `D = b`, only fed-batch feeding can trigger it. |
| Feed ≠ bleed (continuous) | warning | `D > b`: the warning states the harvest stream `(D − b)·V` per day. |
| Feed < bleed | **block** | Negative harvest |
| Feed below the suggested min. | warning | "With D = …, <metabolite> settles at … mM, beyond its limit; the suggested min. feed is … VVD." |
| Metabolite limit | warning | Consumed: min < limit. Produced: max > limit. The warning reports the first time the limit is crossed. |
| Metabolite depleted | warning | `C` hits 0. The time is reported. Growth is **not** affected (see A1). |
| Inputs | **block** | Missing `µ`, `T`, a regime or `b`; non-integer `T`; more than 6 phases or 120 days; a fed-batch phase over 30 days; `V0` outside `[V_min, V_max]`. |

---

## 4. Assumptions

- **A1:** Growth is set by the user's `µ` per phase. It does not respond to metabolite levels: no Monod, inhibition or death terms.
- **A2:** `q` rates are constant through the whole process and in all phase types.
- **A3:** Viability is 100 %. VCC equals total cell density, and cell death is not modelled.
- **A4:** Wet biomass scales linearly with VCC (`k_wb`).
- **A5:** Continuous phases run by default with feed = bleed (`D = b`). Volume is constant and there is no cell-free harvest. If `D > b`, a cell-free harvest `D − b` keeps the volume constant. Volume is never integrated as `dV/dt` in continuous mode.
- **A6:** Fed-batch feed is a constant flow over each phase day. The day's volume is a % of `V0` (not of the current volume), and its composition is `C_fb`.
- **A7:** The reactor is ideally mixed. There is no sampling volume, evaporation or base addition.
- **A8:** Batch and fed-batch metabolites use the step-average VCC with explicit Euler. Hourly steps are more accurate than daily ones.

---

## 5. Reference plans (regression tests)

Setup and metabolites are the defaults above. The phases are:
1. Batch, 2 d, µ = ln(2.37E6/8E5)/2 = 0.54302 1/day.
2. Fed-batch, 2 d, µ = ln(7E6/2.37E6)/2 = 0.54151 1/day, Regime A.
3. Continuous, 10 d, µ = 0.54151, b = suggested = 0.54151 VVD.

| Output | **Example plan** (app default: hourly, flow feeding, `D = b`) | Hourly, flow feeding, `D` = suggested 0.7224 | **Sheet parity** (daily, bolus mode, `D` = 0.7224) |
|---|---|---|---|
| D used | 0.5415 VVD | 0.7224 VVD | 0.7224 VVD |
| Fed-batch volume added per day | 0.030 L (days 3, 4) | same | same |
| Total fresh medium | 6.800 L | 8.717 L | 8.717 L |
| Harvest | 0 L | 1.917 L | 1.917 L |
| Max working volume | 1.06 L | 1.06 L | 1.06 L |
| Cells bled | 4.018E10 | 4.018E10 | 4.018E10 |
| Total wet biomass | 93.6 g | 93.6 g | 93.6 g |
| Peak / final lactate | 26.66 / 26.66 mM ⚠ | 22.88 / 20.00 mM ⚠ | 23.82 / 20.00 mM ⚠ |
| Min glucose | 0.56 mM ⚠ | 6.64 mM | 6.64 mM |

- The values come from the scratch port of these equations, and M1 pins them.
- The **sheet-parity** column must match the original spreadsheet day by day at `rel = 1e-9`.
- The example plan triggers the "feed below the suggested min." warning by design: at 7E6 cells/mL, `D = b` is too little medium for the lactate and glucose limits.

Invariants at any `Δt`, in both feeding modes:
- fresh medium = `V_end` + cum. bleed + cum. harvest;
- `b = µ` ⇒ constant VCC;
- `D = b` ⇒ harvest = 0.
