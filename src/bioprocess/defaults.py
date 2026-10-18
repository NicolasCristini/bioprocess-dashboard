"""Default (placeholder) inputs: MODEL.md §1 defaults and the §5 reference plan."""
from __future__ import annotations

import math

from .models import (BatchPhase, ContinuousPhase, FedBatchPhase, FeedRegime, Metabolite, Scenario,
                     Setup)

MU_BATCH = math.log(2.37e6 / 8e5) / 2      # 0.54302 1/day
MU_FEDBATCH = math.log(7e6 / 2.37e6) / 2   # 0.54151 1/day


def default_metabolites() -> list[Metabolite]:
    return [
        Metabolite(name="Glucose", kind="consumed", q=7.9, limit=5, c_batch=25, c_fedbatch=250, c_perfusion=25),
        Metabolite(name="Lactate", kind="produced", q=8.6, limit=20, c_batch=0, c_fedbatch=0, c_perfusion=0),
        Metabolite(name="Glutamine", kind="consumed", limit=0.5),
        Metabolite(name="Glutamate", kind="consumed", limit=0.5),
        Metabolite(name="Ammonia", kind="produced", limit=5, c_fedbatch=0, c_perfusion=0),
    ]


def default_regimes() -> list[FeedRegime]:
    return [
        FeedRegime(name="Regime A", description="3 %/day on days 1–2", pct_per_day={1: 3, 2: 3}),
        FeedRegime(name="Regime B", description="2 %/day every day", pct_per_day={d: 2 for d in range(1, 31)}),
        FeedRegime(name="Regime C", description="5 % on every 2nd day",
                   pct_per_day={d: 5 for d in range(2, 31, 2)}),
        FeedRegime(name="Regime D", description="custom"),
    ]


def example_scenario(feed: str | float = "= bleed", mu_digits: int | None = 5) -> Scenario:
    """The example plan (MODEL.md §5). Placeholder values for development."""
    rnd = (lambda v: round(v, mu_digits)) if mu_digits is not None else (lambda v: v)
    return Scenario(
        name="Example plan (placeholder values)",
        notes="Batch 2 d → fed-batch 2 d (Regime A) → continuous 10 d. All values are placeholders.",
        setup=Setup(),
        metabolites=default_metabolites(),
        regimes=default_regimes(),
        phases=[
            BatchPhase(days=2, mu=rnd(MU_BATCH)),
            FedBatchPhase(days=2, mu=rnd(MU_FEDBATCH), regime="Regime A"),
            ContinuousPhase(days=10, mu=rnd(MU_FEDBATCH), bleed_vvd="suggested", feed_vvd=feed),
        ],
    )


def blank_phase(kind: str, mu: float = 0.5, regime: str = "Regime A"):
    if kind == "Batch":
        return BatchPhase(days=2, mu=mu)
    if kind == "Fed-batch":
        return FedBatchPhase(days=2, mu=mu, regime=regime)
    return ContinuousPhase(days=7, mu=mu)
