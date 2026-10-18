"""Import a scenario from the spreadsheet planner (.xlsx, e.g. downloaded from Google Sheets).

Reads the input cells of the tabs '1 Setup', '2 Phases' and '3 Feed regimes'. The spreadsheet uses a target
cell density per batch/fed-batch phase; it is converted to µ = ln(target / start) / days. The spreadsheet has
no working-volume window: V_min is set to 0 and V_max to the vessel volume.
"""
from __future__ import annotations

import io
import math

from ..models import BatchPhase, ContinuousPhase, FedBatchPhase, FeedRegime, Metabolite, Scenario, Setup

SETUP, PHASES, REGIMES = "1 Setup", "2 Phases", "3 Feed regimes"
SUGGESTION_REFS = ("=Q", "=R")     # default continuous inputs point at the suggestion columns


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def from_xlsx(data: bytes, name: str = "Imported from spreadsheet") -> tuple[Scenario, list[str]]:
    """Return the scenario and a list of notes about what was converted."""
    import openpyxl  # lazy: slow to import in the browser

    try:
        wb_f = openpyxl.load_workbook(io.BytesIO(data))                    # formulas
        wb_v = openpyxl.load_workbook(io.BytesIO(data), data_only=True)    # cached values
        su, ph, fr = wb_v[SETUP], wb_v[PHASES], wb_v[REGIMES]
        ph_f = wb_f[PHASES]
    except KeyError as e:
        raise ValueError(f"Not a phase-planner workbook (missing tab {e}).") from e
    notes: list[str] = []

    vessel, v0, seed, kwb = (_num(su[f"B{r}"].value) for r in (4, 5, 6, 7))
    if None in (vessel, v0, seed, kwb):
        raise ValueError("Setup values (vessel, working volume, seeding density, wet biomass) are missing.")
    setup = Setup(vessel_volume_L=vessel, initial_wv_L=v0, v_min_L=0.0, v_max_L=vessel, seeding_density=seed,
                  wet_biomass_g_per_L_at_1e6=kwb)
    notes.append(f"Working-volume window set to 0–{vessel:g} L (the spreadsheet has none).")

    mets = []
    for r in range(10, 15):
        nm = su[f"A{r}"].value
        if not nm:
            continue
        kind = su[f"B{r}"].value if su[f"B{r}"].value in ("consumed", "produced") else "consumed"
        q, lim, cb, cf, cp = (_num(su[f"{c}{r}"].value) for c in "CDEFG")
        mets.append(Metabolite(name=str(nm), kind=kind, q=q, limit=lim, c_batch=cb, c_fedbatch=cf, c_perfusion=cp))

    regimes = []
    for c in "BCDE":
        rname = fr[f"{c}4"].value
        if not rname:
            continue
        pct = {d: float(v) for d in range(1, 31) if (v := _num(fr[f"{c}{5 + d}"].value))}
        regimes.append(FeedRegime(name=str(rname), description=str(fr[f"{c}5"].value or ""), pct_per_day=pct))

    n = int(_num(ph["B4"].value) or 0)
    phases, x, mu_prev = [], seed, None
    for i in range(n):
        r = 7 + i
        typ, days = ph[f"C{r}"].value, _num(ph[f"D{r}"].value)
        if typ not in ("Batch", "Fed-batch", "Continuous") or not days:
            raise ValueError(f"Phase {i + 1}: type or duration missing.")
        days = int(days)
        if typ == "Continuous":
            override = _num(ph[f"I{r}"].value)
            mu = override if override is not None else mu_prev
            if mu is None:
                raise ValueError(f"Phase {i + 1}: no growth rate to inherit.")
            def setting(col, val):
                f = ph_f[f"{col}{r}"].value
                if isinstance(f, str) and f.startswith(SUGGESTION_REFS):
                    return "suggested"
                return val
            bleed = setting("H", _num(ph[f"H{r}"].value))
            feed = setting("G", _num(ph[f"G{r}"].value))
            if bleed is None or feed is None:
                raise ValueError(f"Phase {i + 1}: feed or bleed rate missing.")
            phases.append(ContinuousPhase(days=days, mu=mu, bleed_vvd=bleed, feed_vvd=feed))
            x = x * math.exp((mu - (mu if bleed == "suggested" else bleed)) * days)
        else:
            target = _num(ph[f"E{r}"].value)
            mu = math.log(target / x) / days if target else 0.0
            notes.append(f"Phase {i + 1}: target {target:.3g} cells/mL → µ = {mu:.5f} 1/day." if target
                         else f"Phase {i + 1}: no target → µ = 0 (VCC held).")
            if typ == "Batch":
                phases.append(BatchPhase(days=days, mu=mu))
            else:
                phases.append(FedBatchPhase(days=days, mu=mu, regime=str(ph[f"F{r}"].value or "Regime A")))
            x = target or x
        mu_prev = mu
    notes.append("Fed-batch feed is now a constant flow over each day (the spreadsheet adds a bolus at day end): "
                 "metabolite curves in fed-batch phases differ slightly; volumes and totals are the same.")
    return Scenario(name=name, setup=setup, metabolites=mets, regimes=regimes, phases=phases), notes
