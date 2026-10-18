"""Time-stepping simulation (MODEL.md §2). simulate() never raises on bad input: it returns issues."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

from .checks import EPS, Issue, has_block, validate
from .models import Scenario
from .suggest import RATE_FACTOR, PhasePlan, plan_phases, steady_state

Feeding = Literal["flow", "bolus"]


@dataclass
class SimResult:
    scenario: Scenario
    steps_per_day: int
    table: pd.DataFrame                       # one row per step, row 0 = t 0
    plans: list[PhasePlan]
    issues: list[Issue] = field(default_factory=list)
    stopped_at_h: float | None = None         # set when the volume window blocked the run

    @property
    def ok(self) -> bool:
        """True when the run is complete and valid (no block)."""
        return not has_block(self.issues) and not self.table.empty

    @property
    def blocked(self) -> bool:
        return has_block(self.issues)

    @property
    def metabolite_names(self) -> list[str]:
        return [m.name for m in self.scenario.metabolites]


def simulate(sc: Scenario, steps_per_day: int | None = None, fedbatch_feeding: Feeding = "flow") -> SimResult:
    """Run the scenario. `fedbatch_feeding="bolus"` is the internal sheet-parity mode (MODEL.md §2.6)."""
    n_day = steps_per_day or sc.setup.steps_per_day
    issues = validate(sc)
    if has_block(issues):
        return SimResult(sc, n_day, pd.DataFrame(), [], issues)
    plans = plan_phases(sc)
    s, mets = sc.setup, sc.metabolites
    dt, v0, k_wb = 1.0 / n_day, s.initial_wv_L, s.wet_biomass_g_per_L_at_1e6
    nan = math.nan

    # state
    x, v = s.seeding_density, v0
    conc = [m.c_batch if m.modelled else nan for m in mets]
    pending_bolus = 0.0                       # bolus mode: added at end of previous step, mixed this step
    cum = dict(fresh=v0, fb=0.0, perf=0.0, harvest=0.0, bleed=0.0, cells=0.0)
    rows = [_row(0, 0, plans[0], 0.0, x, x, 0, v, 0, 0, 0, 0, cum, mets, conc, k_wb)]
    stopped = None
    total_steps = plans[-1].end_day * n_day
    pi = 0
    for n in range(1, total_steps + 1):
        t = n * dt
        while t > plans[pi].end_day + EPS:
            pi += 1
        p = plans[pi]
        tau = t - p.start_day
        x_new = p.x_start * math.exp((p.mu - p.bleed) * tau)
        x_avg = (x + x_new) / 2

        fb = 0.0
        if p.type == "Fed-batch":
            regime = sc.regime(p.regime)
            if fedbatch_feeding == "flow":
                fb = regime.pct(math.ceil(tau - EPS)) / 100 * v0 * dt
            elif abs(tau - round(tau)) < EPS:
                fb = regime.pct(round(tau)) / 100 * v0
        perf, bleed = p.feed * v * dt, p.bleed * v * dt
        harvest, cells_bled = perf - bleed, bleed * 1000 * x_avg

        new_conc = []
        for m, c in zip(mets, conc):
            if math.isnan(c) or m.q is None:
                new_conc.append(nan)
                continue
            if fedbatch_feeding == "flow":
                mix = (c * v + (m.c_fedbatch or 0.0) * fb) / (v + fb) if fb else c
            else:
                mix = (c * (v - pending_bolus) + (m.c_fedbatch or 0.0) * pending_bolus) / v if pending_bolus else c
            rate = m.sign * m.q * RATE_FACTOR * x_avg
            if p.type == "Continuous" and p.feed > 0:
                if m.c_perfusion is None:
                    new_conc.append(nan)
                    continue
                c_star = m.c_perfusion + rate / p.feed
                new_conc.append(max(0.0, c_star + (mix - c_star) * math.exp(-p.feed * dt)))
            else:
                new_conc.append(max(0.0, mix + rate * dt))

        v_new = v + fb
        cum["fresh"] += fb + perf
        cum["fb"] += fb
        cum["perf"] += perf
        cum["harvest"] += harvest
        cum["bleed"] += bleed
        cum["cells"] += cells_bled
        x, v, conc = x_new, v_new, new_conc
        pending_bolus = fb if fedbatch_feeding == "bolus" else 0.0
        rows.append(_row(n, t, p, tau, x, x_avg, fb, v, perf, bleed, harvest, cells_bled, cum, mets, conc, k_wb))
        if v > s.v_max_L + EPS or v < s.v_min_L - EPS:
            stopped = t * 24
            side = "above V_max" if v > s.v_max_L else "below V_min"
            issues.append(Issue("block", "results", f"Run stopped at day {int(t)} h {round(t % 1 * 24)}: working "
                                                    f"volume {v:.3f} L is {side}.", p.index, stopped))
            break

    table = pd.DataFrame(rows)
    result = SimResult(sc, n_day, table, plans, issues, stopped)
    result.issues.extend(_run_checks(result))
    return result


def _row(n, t, p: PhasePlan, tau, x, x_avg, fb, v, perf, bleed, harvest, cells_bled, cum, mets, conc, k_wb):
    row = {
        "step": n, "t_h": t * 24, "t_d": t, "day": math.ceil(t - EPS) if n else 0,
        "phase": p.index, "type": p.type, "tau_d": tau,
        "vcc": x, "avg_vcc": x_avg if n else math.nan,
        "fb_feed_L": fb, "volume_L": v, "perf_feed_L": perf, "bleed_L": bleed, "harvest_L": harvest,
        "cells_bled": cells_bled,
        "cum_fresh_L": cum["fresh"], "cum_fb_L": cum["fb"], "cum_perf_L": cum["perf"],
        "cum_harvest_L": cum["harvest"], "cum_bleed_L": cum["bleed"], "cum_cells_bled": cum["cells"],
    }
    for m, c in zip(mets, conc):
        row[m.name] = c
    row["wb_g_per_L"] = x / 1e6 * k_wb
    row["wb_reactor_g"] = row["wb_g_per_L"] * v
    row["cum_wb_bleed_g"] = cum["cells"] * k_wb / 1e9
    return row


def _run_checks(r: SimResult) -> list[Issue]:
    out: list[Issue] = []
    tb, sc = r.table, r.scenario
    for p in r.plans:
        if p.type != "Continuous":
            continue
        v_end = tb.loc[tb.phase == p.index, "volume_L"]
        v_end = float(v_end.iloc[-1]) if len(v_end) else sc.setup.initial_wv_L
        if p.feed > p.bleed + EPS:
            out.append(Issue("warning", "phases", f"Feed {p.feed:.3f} > bleed {p.bleed:.3f} VVD: a cell-free harvest "
                                                  f"of {(p.feed - p.bleed) * v_end:.3f} L/day is drawn.", p.index))
        if p.suggested_min_feed is not None and p.feed < p.suggested_min_feed - 1e-6:
            beyond = []
            for m in sc.metabolites:
                cs = steady_state(m, max(p.x_start, p.x_end), p.feed)
                if cs is not None and m.limit is not None and m.sign * (cs - m.limit) > 0:
                    beyond.append(f"{m.name} → {cs:.1f} mM (limit {m.limit:g})")
            if beyond:
                out.append(Issue("warning", "phases", f"Feed {p.feed:.3f} VVD is below the suggested minimum "
                                                      f"{p.suggested_min_feed:.3f} VVD: " + "; ".join(beyond) + ".",
                                 p.index))
    for m in sc.metabolites:
        if m.name not in tb or tb[m.name].isna().all():
            continue
        col = tb[m.name]
        if m.limit is not None:
            bad = col > m.limit + EPS if m.sign > 0 else col < m.limit - EPS
            if bad.any():
                i = int(bad.idxmax())
                verb = "exceeds its maximum" if m.sign > 0 else "drops below its minimum"
                out.append(Issue("warning", "results", f"{m.name} {verb} of {m.limit:g} mM at day "
                                                       f"{tb.t_d[i]:.2f} (extreme {col.max() if m.sign > 0 else col.min():.2f} mM).",
                                 int(tb.phase[i]), float(tb.t_h[i])))
        if m.sign < 0 and (col <= 0).any():
            i = int((col <= 0).idxmax())
            out.append(Issue("warning", "results", f"{m.name} is depleted at day {tb.t_d[i]:.2f} "
                                                   "(growth is not affected in this model).", int(tb.phase[i]), float(tb.t_h[i])))
    return out
