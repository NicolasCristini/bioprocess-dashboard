"""Checks (MODEL.md §3): input validation before a run, and warnings found during/after it."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .models import MAX_DAYS, MAX_PHASES, REGIME_DAYS, ContinuousPhase, FedBatchPhase, Scenario

Level = Literal["block", "warning", "info"]
EPS = 1e-9


@dataclass(frozen=True)
class Issue:
    level: Level
    where: Literal["setup", "phases", "regimes", "results"]
    message: str
    phase: int | None = None       # 1-based phase number
    t_h: float | None = None       # time in hours, for run-time findings

    @property
    def icon(self) -> str:
        return {"block": "⛔", "warning": "⚠", "info": "ℹ"}[self.level]


def validate(sc: Scenario) -> list[Issue]:
    """Input problems. Any 'block' issue means the scenario cannot be simulated."""
    out: list[Issue] = []
    s = sc.setup
    if not s.v_min_L <= s.initial_wv_L <= s.v_max_L:
        out.append(Issue("block", "setup", f"Initial working volume {s.initial_wv_L:g} L must lie between "
                                           f"V_min {s.v_min_L:g} L and V_max {s.v_max_L:g} L."))
    if s.v_max_L > s.vessel_volume_L + EPS:
        out.append(Issue("block", "setup", f"V_max {s.v_max_L:g} L is larger than the vessel ({s.vessel_volume_L:g} L)."))
    names = [m.name for m in sc.metabolites]
    if len(set(names)) != len(names):
        out.append(Issue("block", "setup", "Metabolite names must be unique."))

    if not sc.phases:
        out.append(Issue("block", "phases", "Add at least one phase."))
    if len(sc.phases) > MAX_PHASES:
        out.append(Issue("block", "phases", f"At most {MAX_PHASES} phases (got {len(sc.phases)})."))
    if sc.total_days > MAX_DAYS:
        out.append(Issue("block", "phases", f"Total duration {sc.total_days} days exceeds {MAX_DAYS} days."))
    for i, p in enumerate(sc.phases, 1):
        if p.mu < 0:
            out.append(Issue("info", "phases", f"µ = {p.mu:g} 1/day: cell density declines in this phase.", i))
        if isinstance(p, FedBatchPhase):
            if p.days > REGIME_DAYS:
                out.append(Issue("block", "phases", f"A fed-batch phase can last at most {REGIME_DAYS} days.", i))
            if sc.regime(p.regime) is None:
                out.append(Issue("block", "phases", f"Feed regime '{p.regime}' does not exist.", i))
        if isinstance(p, ContinuousPhase):
            bleed = p.mu if p.bleed_vvd == "suggested" else float(p.bleed_vvd)
            if bleed < 0:
                out.append(Issue("block", "phases", "Bleed rate cannot be negative.", i))
            if isinstance(p.feed_vvd, (int, float)):
                if p.feed_vvd <= 0:
                    out.append(Issue("block", "phases", "Feed rate must be above 0.", i))
                elif p.feed_vvd < bleed - EPS:
                    out.append(Issue("block", "phases", f"Feed {p.feed_vvd:g} VVD is below bleed {bleed:g} VVD: "
                                                        "the harvest would be negative.", i))
            elif bleed <= 0 and p.feed_vvd == "= bleed":
                out.append(Issue("block", "phases", "Feed = bleed needs a bleed rate above 0.", i))
            for m in sc.metabolites:
                if m.modelled and m.c_perfusion is None:
                    out.append(Issue("info", "phases", f"{m.name}: no perfusion-medium concentration, so it is "
                                                       "not calculated from this phase on.", i))
    for r in sc.regimes:
        bad = [d for d in r.pct_per_day if not 1 <= d <= REGIME_DAYS]
        if bad:
            out.append(Issue("block", "regimes", f"Regime '{r.name}': days must be 1–{REGIME_DAYS} (got {bad})."))
        if any(v < 0 for v in r.pct_per_day.values()):
            out.append(Issue("block", "regimes", f"Regime '{r.name}': feed % cannot be negative."))
    return out


def has_block(issues: list[Issue]) -> bool:
    return any(i.level == "block" for i in issues)
