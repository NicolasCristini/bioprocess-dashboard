"""Phase pre-pass and continuous-phase suggestions (MODEL.md §2.1, §2.4)."""
from __future__ import annotations

import math
from dataclasses import dataclass

from .models import ContinuousPhase, FedBatchPhase, Metabolite, Scenario

RATE_FACTOR = 24e-8  # q [1E-11 mmol/cell/h] x VCC [cells/mL] -> mM/day


@dataclass(frozen=True)
class PhasePlan:
    """Resolved per-phase quantities, before stepping through time."""
    index: int            # 1-based
    type: str
    start_day: int
    end_day: int
    mu: float
    x_start: float
    x_end: float
    bleed: float          # VVD (0 outside continuous)
    feed: float           # VVD (0 outside continuous)
    suggested_bleed: float | None
    suggested_min_feed: float | None
    regime: str | None

    @property
    def days(self) -> int:
        return self.end_day - self.start_day


def min_feed_terms(metabolites: list[Metabolite], x_start: float, x_end: float) -> dict[str, float]:
    """Per-metabolite perfusion rate (VVD) that keeps the steady state at its limit."""
    out = {}
    x = max(x_start, x_end)
    for m in metabolites:
        if m.q is None or m.c_perfusion is None or m.limit is None:
            continue
        gap = m.limit - m.c_perfusion
        if m.sign * gap > 0:
            out[m.name] = m.q * x * RATE_FACTOR / abs(gap)
    return out


def plan_phases(sc: Scenario) -> list[PhasePlan]:
    plans: list[PhasePlan] = []
    x, day = sc.setup.seeding_density, 0
    for i, p in enumerate(sc.phases, 1):
        sug_b = sug_f = None
        bleed = feed = 0.0
        if isinstance(p, ContinuousPhase):
            sug_b = p.mu
            bleed = sug_b if p.bleed_vvd == "suggested" else float(p.bleed_vvd)
            x_end = x * math.exp((p.mu - bleed) * p.days)
            sug_f = max([bleed, *min_feed_terms(sc.metabolites, x, x_end).values()])
            feed = bleed if p.feed_vvd == "= bleed" else sug_f if p.feed_vvd == "suggested" else float(p.feed_vvd)
        else:
            x_end = x * math.exp(p.mu * p.days)
        plans.append(PhasePlan(i, p.type, day, day + p.days, p.mu, x, x_end, bleed, feed, sug_b, sug_f,
                               p.regime if isinstance(p, FedBatchPhase) else None))
        x, day = x_end, day + p.days
    return plans


def steady_state(m: Metabolite, x: float, feed: float) -> float | None:
    """C* = C_perf + r/D for a continuous phase at VCC x (MODEL.md §2.3)."""
    if m.q is None or m.c_perfusion is None or feed <= 0:
        return None
    return max(0.0, m.c_perfusion + m.sign * m.q * RATE_FACTOR * x / feed)
