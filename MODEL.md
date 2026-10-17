# MODEL.md: Bioprocess Phase Planner model

The single reference for every model parameter, equation and assumption used by the dashboard.
Change the model here first, then in `src/bioprocess/`, and update the reference tests.

**Model version:** 1.0 (parity with the original spreadsheet planner, with µ as the per-phase input)
**Status:** specification. The code in `src/bioprocess/` must follow this file.

All numeric defaults are **example values** taken from published literature, for development only. Values marked *placeholder* are not literature values; they are stand-ins until a measured value exists.

---

## 1. Parameters

### 1.1 Setup

| Symbol | Parameter | Default | Unit | Notes |
|---|---|---|---|---|
| `V_vessel` | Vessel volume (total) | 2.0 | L | *placeholder* |
| `V0` | Initial working volume | 1.0 | L | Must satisfy `V_min ≤ V0 ≤ V_max < V_vessel` |
| `V_min` | Minimum working volume | 0.5 | L | *placeholder*. The simulation is **blocked** if V drops below it. |
| `V_max` | Maximum working volume | 2.0 (= `V_vessel`) | L | *placeholder*. The simulation is **blocked** if V exceeds it. |
| `X_seed` | Seeding density (t = 0) | 8.0E5 | cells/mL | |
| `k_wb` | Wet biomass at 1E6 cells/mL | 2.0 | g/L | *placeholder*. Wet biomass is assumed to scale linearly with VCC. |
| `steps_per_day` | Time resolution | 24 (hourly) | 1/day | 1 = daily (the spreadsheet's resolution, used by the parity tests) |

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
| Continuous | `T`, `µ`, perfusion (feed) rate `D`, bleed rate `b` | d, 1/day, VVD, VVD |

`µ` is a required input for every phase. The UI pre-fills it with the previous phase's `µ`. `µ = 0` is allowed and holds VCC constant in batch and fed-batch phases.

### 1.4 Feed regimes (fed-batch)

A bolus per phase day `d = 1…30`, as **% of the initial working volume `V0`**, for each of regimes A–D.

| Regime | Default |
|---|---|
| A | 3 % on days 1–2 |
| B | 2 % every day |
| C | 5 % every 2nd day |
| D | custom (empty) |

### 1.5 Hard limits

- 6 phases;
- 120 days in total;
- 30 feed-regime days.

A fed-batch phase longer than 30 days is a validation error.

---

## 2. Equations

Time `t` is in days. The step is `Δt = 1/steps_per_day`. Step `n` covers `(t_{n-1}, t_n]`. A step at a phase boundary belongs to the phase that ends there, the same rule as the spreadsheet's `COUNTIF(end < k) + 1`. `τ = t − t_phase_start` is the time in the phase. `X_s` is the VCC at the start of the phase, which is the VCC at the end of the previous phase, or `X_seed` for phase 1.

### 2.1 Cell density

| Phase | VCC(τ) |
|---|---|
| Batch, fed-batch | `X_s · exp(µ·τ)` |
| Continuous | `X_s · exp((µ − b)·τ)` |

This is exact at any `Δt`. The step-average VCC is `X̄_n = (X_{n-1} + X_n)/2`.

### 2.2 Volumes and flows (per step)

| Quantity | Batch | Fed-batch | Continuous |
|---|---|---|---|
| Bolus `F_n` (L) | 0 | `regime[d]/100 · V0` at the end of phase day `d` (the step where `τ = d`), else 0 | 0 |
| Perfusion feed `I_n` (L) | 0 | 0 | `D · V_{n-1} · Δt` |
| Bleed `J_n` (L) | 0 | 0 | `b · V_{n-1} · Δt` |
| Harvest `H_n` (L, cell-free) | 0 | 0 | `I_n − J_n` |
| Volume `V_n` | `V_{n-1}` | `V_{n-1} + F_n` | `V_{n-1}` (constant) |
| Cells bled | 0 | 0 | `J_n · 1000 · X̄_n` |

Cumulative values:
- fresh medium: `V0 + ΣF + ΣI`;
- bleed: `ΣJ`;
- harvest: `ΣH`;
- cells bled: `Σ(cells bled)`.

### 2.3 Metabolites (per metabolite with `q` given)

The volumetric rate is `r_n = sign · q · 24E-8 · X̄_n` in mM/day. This comes from 1E-11 mmol/cell/h × 24 h/day × cells/mL × 1000 mL/L.

**Mixing.** A bolus added at the end of step *n*−1 is mixed in at step *n*:

`C_mix = (C_{n-1}·(V_{n-1} − F_{n-1}) + C_fb·F_{n-1}) / V_{n-1}`

| Phase | `C_n` |
|---|---|
| Batch, fed-batch | `max(0, C_mix + r_n·Δt)` (explicit Euler; exact as in the sheet at Δt = 1) |
| Continuous (D > 0) | `max(0, C* + (C_mix − C*)·exp(−D·Δt))`, with `C* = C_perf + r_n/D` (exact for constant `r_n` over the step) |

At `t = 0`, `C = C_batch`. If `C_perf` is blank for a modelled metabolite, its value becomes blank from the first continuous step onwards.

### 2.4 Suggestions (continuous phases)

- **Suggested bleed** = `µ`. This holds VCC constant.
- **Suggested min. perfusion rate** = `max(b, max_m [ q_m · max(X_s, X_e) · 24E-8 / |limit_m − C_perf,m| ])`.
  - The max over metabolites only counts a metabolite when `sign·(limit − C_perf) > 0`, i.e. the perfusion medium is on the safe side of the limit.
  - `X_e` = VCC at the end of the phase.
  - It is a steady-state estimate and does not depend on `Δt`.

### 2.5 Outputs

- Wet biomass (g/L) = `X / 1E6 · k_wb`.
- Wet biomass in the reactor (g) = that value × `V`.
- Wet biomass in the bleed (g, cumulative) = cum. cells bled · `k_wb` / 1E9.
- Cells inoculated = `X_seed · V0 · 1000`.
- Cells at end = `X_end · V_end · 1000`.
- **Cells produced** = cells at end + cells bled − cells inoculated.
- **Total wet biomass produced** = cells produced · `k_wb` / 1E9.

---

## 3. Checks

| Check | Level | Rule |
|---|---|---|
| Volume window | **block** | If `V < V_min` or `V > V_max` at any step, the run stops at that step. Results are shown only up to that point, marked invalid, and left out of comparisons. |
| Feed ≠ bleed (continuous) | warning | `D ≠ b`: the warning states the harvest stream `(D − b)·V` per day. `D < b` (negative harvest) is a **block**. |
| Metabolite limit | warning | Consumed: min < limit. Produced: max > limit. The warning reports the first time the limit is crossed. |
| Metabolite depleted | warning | `C` hits 0. The time is reported. Growth is **not** affected (see A1). |
| Inputs | **block** | Missing `µ`, `T`, a regime or `D`/`b`; non-integer `T`; more than 6 phases or 120 days; a fed-batch phase over 30 days; `V0` outside `[V_min, V_max]`. |

---

## 4. Assumptions

- **A1:** Growth is set by the user's `µ` per phase. It does not respond to metabolite levels: no Monod, inhibition or death terms.
- **A2:** `q` rates are constant through the whole process and in all phase types.
- **A3:** Viability is 100 %. VCC equals total cell density, and cell death is not modelled.
- **A4:** Wet biomass scales linearly with VCC (`k_wb`, a placeholder).
- **A5:** In continuous mode, volume is held constant by a cell-free harvest stream `D − b`. Feed and bleed are referred to the current working volume.
- **A6:** Fed-batch boluses are instantaneous at the end of each phase day, as % of `V0` (not of the current volume). Their composition is `C_fb`.
- **A7:** The reactor is ideally mixed. There is no sampling volume, evaporation or base addition.
- **A8:** The batch-phase metabolite step uses the step-average VCC with explicit Euler. Hourly steps therefore give slightly different (more accurate) metabolite profiles than the daily spreadsheet. For the reference plan, peak lactate is 23.82 mM daily and 23.25 mM hourly.

---

## 5. Reference plan (regression tests)

Setup and metabolites are the defaults above. The phases are:
1. Batch, 2 d, µ = ln(2.37E6/8E5)/2 = 0.54302 1/day.
2. Fed-batch, 2 d, µ = ln(7E6/2.37E6)/2 = 0.54151 1/day, Regime A.
3. Continuous, 10 d, µ = 0.54151, b = suggested (0.54151), D = suggested (0.7224 VVD).

| Output | Daily (`steps_per_day = 1`) | Hourly (24) |
|---|---|---|
| Suggested D / b | 0.7224 / 0.5415 VVD | same |
| Total fresh medium | 8.717 L | 8.717 L |
| Max working volume | 1.06 L | 1.06 L |
| Cells bled | 4.018E10 | 4.018E10 |
| Total wet biomass | 93.60 g | 93.6 g |
| Peak lactate | 23.82 mM | 23.25 mM |
| Min glucose | 6.64 mM | 6.64 mM |

The daily column must match the spreadsheet day by day at `rel = 1e-9`.

Invariants at any `Δt`:
- fresh medium = `V_end` + cum. bleed + cum. harvest;
- `b = µ` ⇒ constant VCC.

The hourly column is computed by the model's own scratch port and is pinned once M1 reproduces it.
