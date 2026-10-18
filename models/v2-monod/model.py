"""v2.0 Monod: growth and substrate uptake limited by metabolite concentrations (MODEL2.md).

With no Monod constant set, every factor is 1 and the run is identical to v1.1 (tested).
"""
from __future__ import annotations

import math

import pandas as pd

from bioprocess.checks import EPS, Issue, has_block, validate
from bioprocess.models import ContinuousPhase, FedBatchPhase
from bioprocess.simulate import SimResult, run_checks, table_row
from bioprocess.suggest import RATE_FACTOR, PhasePlan, min_feed_terms


def _k(params: dict, met: str, key: str):
    v = (params.get(met) or {}).get(key)
    return float(v) if v not in (None, "") and float(v) > 0 else None


def growth_factor(mets, conc, params) -> tuple[float, str | None]:
    """Π C/(Ks+C) over limiting substrates × Π Ki/(Ki+C) over inhibitors; also the most limiting metabolite."""
    f, worst, worst_f = 1.0, None, 1.0
    for m, c in zip(mets, conc):
        if math.isnan(c):
            continue
        ks, ki = _k(params, m.name, "Ks"), _k(params, m.name, "Ki")
        g = 1.0
        if m.kind == "consumed" and ks:
            g = c / (ks + c)
        elif m.kind == "produced" and ki:
            g = ki / (ki + c)
        f *= g
        if g < worst_f:
            worst, worst_f = m.name, g
    return f, worst


def simulate(sc, params=None, steps_per_day: int | None = None, fedbatch_feeding: str = "flow") -> SimResult:
    params = params or {}
    n_day = steps_per_day or sc.setup.steps_per_day
    issues = validate(sc)
    if has_block(issues):
        return SimResult(sc, n_day, pd.DataFrame(), [], issues)
    s, mets = sc.setup, sc.metabolites
    dt, v0, k_wb = 1.0 / n_day, s.initial_wv_L, s.wet_biomass_g_per_L_at_1e6
    nan = math.nan

    x, v = s.seeding_density, v0
    conc = [m.c_batch if m.modelled else nan for m in mets]
    pending_bolus = 0.0
    cum = dict(fresh=v0, fb=0.0, perf=0.0, harvest=0.0, bleed=0.0, cells=0.0)
    plans: list[PhasePlan] = []
    rows, mu_rows = [], []
    stopped, min_f, min_f_at, min_f_met = None, 1.0, None, None
    day = 0
    first = True
    for i, ph in enumerate(sc.phases, 1):
        f0, _ = growth_factor(mets, conc, params)
        mu_entry = ph.mu * f0
        bleed = feed = 0.0
        sug_b = sug_f = None
        if isinstance(ph, ContinuousPhase):
            sug_b = mu_entry                                   # holds VCC at the entry conditions
            bleed = sug_b if ph.bleed_vvd == "suggested" else float(ph.bleed_vvd)
            x_e = x * math.exp((mu_entry - bleed) * ph.days)
            sug_f = max([bleed, *min_feed_terms(mets, x, x_e).values()])
            feed = bleed if ph.feed_vvd == "= bleed" else sug_f if ph.feed_vvd == "suggested" else float(ph.feed_vvd)
        plan = PhasePlan(i, ph.type, day, day + ph.days, ph.mu, x, x, bleed, feed, sug_b, sug_f,
                         ph.regime if isinstance(ph, FedBatchPhase) else None)
        if first:
            rows.append(table_row(0, 0, plan, 0.0, x, x, 0, v, 0, 0, 0, 0, cum, mets, conc, k_wb))
            mu_rows.append(mu_entry)
            first = False
        regime = sc.regime(plan.regime) if plan.regime else None
        for k in range(1, ph.days * n_day + 1):
            t = day + k * dt
            tau = k * dt
            f, worst = growth_factor(mets, conc, params)            # frozen over the step (explicit)
            mu_eff = ph.mu * f
            if f < min_f - 1e-12:
                min_f, min_f_at, min_f_met = f, t, worst
            x_new = x * math.exp((mu_eff - bleed) * dt)
            x_avg = (x + x_new) / 2
            fb = 0.0
            if plan.type == "Fed-batch":
                if fedbatch_feeding == "flow":
                    fb = regime.pct(math.ceil(tau - EPS)) / 100 * v0 * dt
                elif abs(tau - round(tau)) < EPS:
                    fb = regime.pct(round(tau)) / 100 * v0
            perf, bl = feed * v * dt, bleed * v * dt
            harvest, cells_bled = perf - bl, bl * 1000 * x_avg
            new_conc = []
            for m, c in zip(mets, conc):
                if math.isnan(c) or m.q is None:
                    new_conc.append(nan)
                    continue
                if fedbatch_feeding == "flow":
                    mix = (c * v + (m.c_fedbatch or 0.0) * fb) / (v + fb) if fb else c
                else:
                    mix = (c * (v - pending_bolus) + (m.c_fedbatch or 0.0) * pending_bolus) / v if pending_bolus else c
                ks = _k(params, m.name, "Ks") if m.kind == "consumed" else None
                uptake = c / (ks + c) if ks else 1.0                 # Monod-limited uptake of a substrate
                rate = m.sign * m.q * RATE_FACTOR * x_avg * uptake
                if plan.type == "Continuous" and feed > 0:
                    if m.c_perfusion is None:
                        new_conc.append(nan)
                        continue
                    c_star = m.c_perfusion + rate / feed
                    new_conc.append(max(0.0, c_star + (mix - c_star) * math.exp(-feed * dt)))
                else:
                    new_conc.append(max(0.0, mix + rate * dt))
            v_new = v + fb
            cum["fresh"] += fb + perf
            cum["fb"] += fb
            cum["perf"] += perf
            cum["harvest"] += harvest
            cum["bleed"] += bl
            cum["cells"] += cells_bled
            x, v, conc = x_new, v_new, new_conc
            pending_bolus = fb if fedbatch_feeding == "bolus" else 0.0
            rows.append(table_row(len(rows), t, plan, tau, x, x_avg, fb, v, perf, bl, harvest, cells_bled, cum,
                                  mets, conc, k_wb))
            mu_rows.append(mu_eff)
            if v > s.v_max_L + EPS or v < s.v_min_L - EPS:
                stopped = t * 24
                side = "above V_max" if v > s.v_max_L else "below V_min"
                issues.append(Issue("block", "results", f"Run stopped at day {int(t)} h {round(t % 1 * 24)}: working "
                                                        f"volume {v:.3f} L is {side}.", i, stopped))
                break
        plans.append(PhasePlan(i, ph.type, day, day + ph.days, ph.mu, plan.x_start, x, bleed, feed, sug_b, sug_f,
                               plan.regime))
        day += ph.days
        if stopped:
            break

    table = pd.DataFrame(rows)
    table.insert(table.columns.get_loc("vcc") + 1, "mu_eff", mu_rows)
    res = SimResult(sc, n_day, table, plans, issues, stopped)
    res.issues.extend(run_checks(res))
    if min_f < 0.9 and min_f_at is not None:
        res.issues.append(Issue("info", "results", f"Growth limited to {min_f * 100:.0f} % of µmax at day "
                                                   f"{min_f_at:.2f} (most limiting: {min_f_met}).", None, min_f_at * 24))
    for p in plans:
        if p.type == "Continuous" and p.x_start > 0 and abs(p.x_end / p.x_start - 1) > 0.10:
            res.issues.append(Issue("warning", "results", f"VCC drifts {(p.x_end / p.x_start - 1) * 100:+.0f} % over "
                                                          "this continuous phase: metabolite limitation changes the "
                                                          "growth rate, so bleed = µ at entry no longer holds VCC.",
                                    p.index))
    return res
