---
id: v2-monod
name: Monod limitation
version: "2.0"
status: development
order: 20
summary: >
  The µ entered per phase becomes µmax. Growth is scaled by Monod factors of the limiting substrates (and optional
  inhibition by products), and substrate uptake slows as a substrate runs out. With no constants set it is
  identical to v1.1.
parameters:
  per_metabolite:
    - key: Ks
      label: "Ks, Monod half-saturation"
      unit: mM
      applies_to: consumed
      help: "Concentration at which growth and uptake run at half speed. Blank = this substrate does not limit."
      default: {Glucose: 0.5, Glutamine: 0.2}
    - key: Ki
      label: "Ki, inhibition constant"
      unit: mM
      applies_to: produced
      help: "Concentration at which growth is halved by this product. Blank = no inhibition."
      default: {}
---
# MODEL2.md: Monod limitation (model v2.0)

**Status:** development model. It extends v1.1 (root `MODEL.md`), and everything not listed here is unchanged:
- setup, phases, feeding;
- volumes and flows;
- outputs and checks.

All numeric values are **placeholders**.

## 1. What changes from v1.1

| | v1.1 | v2.0 |
|---|---|---|
| Phase input `µ` | the growth rate | **µmax**, the maximum growth rate in that phase |
| Growth | `µ` (constant per phase) | `µ_eff(t) = µmax · F(C(t))`, which falls as substrates run out or products accumulate |
| VCC | analytic, known in advance | stepped: `X_n = X_{n-1} · exp((µ_eff,n − b) · Δt)` |
| Substrate uptake | `q · X̄` until the clip at 0 | `q · X̄ · C/(Ks + C)`: slows smoothly as the substrate runs out |
| Suggested bleed | `µ` | `µ_eff` at the phase entry |

## 2. Equations

### 2.1 Growth factor

For every **consumed** metabolite *s* with a `Ks`, and every **produced** metabolite *i* with a `Ki`:

$$
F(C) \;=\; \prod_{s} \frac{C_s}{K_{s} + C_s} \;\times\; \prod_{i} \frac{K_{I,i}}{K_{I,i} + C_i}
$$

$$
\mu_\mathrm{eff}(t) \;=\; \mu_\mathrm{max,phase} \cdot F\big(C(t)\big)
$$

- Metabolites without a constant contribute a factor of 1.
- A metabolite that is not modelled (no `q` or no batch concentration) is ignored.

### 2.2 Cell density (per step)

$$
X_n \;=\; X_{n-1}\,\exp\!\big((\mu_\mathrm{eff,n} - b)\,\Delta t\big), \qquad \mu_\mathrm{eff,n} = \mu_\mathrm{max}\,F(C_{n-1})
$$

- `b` = 0 outside continuous phases.
- `F` is evaluated at the start of the step and held over it (explicit). The error is first order in Δt and small at
  the default hourly step.

### 2.3 Metabolites

The volumetric rate uses the step-average VCC, as in v1.1. Consumed substrates with a `Ks` get the Monod uptake term:

$$
r_n \;=\; \mathrm{sign}\cdot q \cdot 24\times10^{-8} \cdot \bar X_n \cdot \frac{C_{n-1}}{K_s + C_{n-1}}
\quad (\text{consumed, } K_s \text{ set}), \qquad
r_n \;=\; \mathrm{sign}\cdot q \cdot 24\times10^{-8} \cdot \bar X_n \quad (\text{otherwise})
$$

- **Batch and fed-batch:** `C_n = max(0, C_mix + r_n Δt)`.
- **Continuous:** `C_n = max(0, C* + (C_mix − C*) e^(−D Δt))` with `C* = C_perf + r_n / D`.

Products are formed at a constant specific rate, as in v1.1. Uptake limitation keeps a substrate from dropping
abruptly to zero.

### 2.4 Continuous phases

- **Suggested bleed** = `µ_eff` at phase entry, which holds VCC only while the concentrations stay as they were at
  entry. If they drift, VCC drifts too, and a warning reports a change of more than 10 % over the phase.
- **Suggested minimum feed:** the same formula as v1.1, using the maximum uptake `q`. That is conservative.
- **Feed = bleed** (the default) uses the resolved bleed.

## 3. Parameters

| Parameter | Applies to | Unit | Default (placeholder) | Typical range in the CHO literature |
|---|---|---|---|---|
| `Ks` | consumed (substrates) | mM | glucose 0.5, glutamine 0.2 | glucose 0.1-1.0; glutamine 0.05-0.5 |
| `Ki` | produced (inhibitors) | mM | off | lactate 40-80; ammonia 5-15 |

- Set them on the **Model** page while this model is selected.
- They are stored in the scenario under `model_params["v2-monod"]`, so the same scenario still runs under v1.1.

## 4. Extra outputs and checks

- **`mu_eff` column:** the effective growth rate at every step.
- **Info:** "Growth limited to X % of µmax", reported when `F` falls below 0.9, with the time and the most limiting
  metabolite.
- **Warning:** VCC drift of more than 10 % over a continuous phase (see 2.4).

## 5. Assumptions (in addition to v1.1)

- **M1:** Monod factors multiply (non-interacting substrates).
- **M2:** Inhibition is non-competitive, `Ki/(Ki + C)`.
- **M3:** Product formation does not depend on growth; there is no Luedeking-Piret term yet.
- **M4:** There is no death or lysis term. Limitation slows growth but never makes it negative, unless µmax < 0.
- **M5:** `F` is held constant within a step (explicit scheme).

## 6. Reduction and reference

- **Reduction:** with every `Ks` and `Ki` blank, `F = 1` and uptake is unlimited. v2.0 then equals v1.1 at every step
  (`tests/test_models.py`).
- **Reference:** the example plan with the default constants (glucose `Ks` 0.5 mM), hourly. Values are filled from the
  implementation and pinned by tests: see the table below.

Example plan, hourly, default constants (glucose `Ks` 0.5 mM; glutamine is not modelled in the example):

| Output | v1.1, feed = bleed | **v2.0, feed = bleed** | v1.1, suggested feed | **v2.0, suggested feed** |
|---|---|---|---|---|
| Total fresh medium | 6.800 L | **6.644 L** | 8.717 L | **8.347 L** |
| Final VCC | 7.00E6 | **5.22E6** | 7.00E6 | **5.88E6** |
| Total wet biomass | 93.60 g | **76.53 g** | 93.60 g | **81.32 g** |
| Min glucose | 0.56 mM | **5.11 mM** | 6.64 mM | **8.51 mM** |
| Peak / final lactate | 26.66 / 26.66 mM | **24.93 / 21.50 mM** | 22.88 / 20.00 mM | **22.15 / 18.02 mM** |
| Lowest µ_eff | 0.5415 | **0.4933** | 0.5415 | **0.5114** |
| VCC drift, continuous phase | 0 % | **-22 %** | 0 % | **-12 %** |

The difference is the model at work, not a bug. With feed = bleed, glucose runs low. Growth and uptake slow before
glucose is exhausted, so glucose bottoms out at 5.1 mM instead of 0.6 mM, and VCC declines because the bleed was
set for the entry growth rate.

## 7. Open points for later versions

- Death rate `kd(t)` and viability.
- Growth-associated product formation (Luedeking-Piret).
- Solving the bleed for a true steady state (`b = µmax F(C*(b))`) instead of using the entry conditions.
- An implicit or substep integration scheme for stiff limitation.
