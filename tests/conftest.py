import json
from pathlib import Path

import pytest

from bioprocess.defaults import default_metabolites
from bioprocess.models import BatchPhase, ContinuousPhase, FedBatchPhase, FeedRegime, Scenario, Setup

FIX = Path(__file__).parent / "fixtures"


def scenario_from_sheet(name: str) -> tuple[Scenario, list[dict]]:
    """Rebuild a scenario from a spreadsheet fixture (targets already converted to µ)."""
    d = json.loads((FIX / f"sheet_{name}.json").read_text())
    phases = []
    for p in d["phases"]:
        if p["type"] == "Batch":
            phases.append(BatchPhase(days=p["days"], mu=p["mu"]))
        elif p["type"] == "Fed-batch":
            phases.append(FedBatchPhase(days=p["days"], mu=p["mu"], regime=p["regime"]))
        else:
            phases.append(ContinuousPhase(days=p["days"], mu=p["mu"], bleed_vvd=p["bleed_vvd"], feed_vvd=p["feed_vvd"]))
    regimes = [FeedRegime(name=k, pct_per_day={int(dd): v for dd, v in days.items()}) for k, days in d["regimes"].items()]
    # the spreadsheet has no volume window: open it wide so parity runs never block
    sc = Scenario(name=f"sheet {name}", setup=Setup(v_min_L=0, v_max_L=2.0), metabolites=default_metabolites(),
                  regimes=regimes, phases=phases)
    return sc, d["rows"]


@pytest.fixture
def sheet():
    return scenario_from_sheet
