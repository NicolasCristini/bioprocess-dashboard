from pathlib import Path

import pytest

from bioprocess.io.sheet_import import from_xlsx
from bioprocess.simulate import simulate
from bioprocess.summary import key_numbers

FIX = Path(__file__).parent / "fixtures"


def test_import_reference_planner_reproduces_sheet():
    sc, notes = from_xlsx((FIX / "planner_ref.xlsx").read_bytes())
    assert [p.type for p in sc.phases] == ["Batch", "Fed-batch", "Continuous"]
    assert sc.phases[0].mu == pytest.approx(0.54302, abs=1e-5)
    assert sc.phases[2].bleed_vvd == "suggested" and sc.phases[2].feed_vvd == "suggested"
    assert any("µ =" in n for n in notes)
    r = simulate(sc, steps_per_day=1, fedbatch_feeding="bolus")
    k = key_numbers(r)
    assert k["fresh_medium_L"] == pytest.approx(8.71744, rel=1e-9)
    assert r.table.Lactate.max() == pytest.approx(23.8184232643909, rel=1e-9)


def test_import_explicit_rates_and_mu_override():
    sc, _ = from_xlsx((FIX / "planner_regB.xlsx").read_bytes())
    cont = sc.phases[2]
    assert (cont.mu, cont.bleed_vvd, cont.feed_vvd) == (0.45, 0.4, 0.9)
    assert sc.phases[1].regime == "Regime B" and sc.phases[1].days == 5
    k = key_numbers(simulate(sc, steps_per_day=1, fedbatch_feeding="bolus"))
    assert k["fresh_medium_L"] == pytest.approx(11.0, rel=1e-9)


def test_not_a_planner():
    import io

    import openpyxl
    buf = io.BytesIO()
    openpyxl.Workbook().save(buf)
    with pytest.raises(ValueError, match="Not a phase-planner"):
        from_xlsx(buf.getvalue())
