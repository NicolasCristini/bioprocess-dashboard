"""MODEL.md §5: the three reference columns."""
import pytest

from bioprocess.defaults import MU_FEDBATCH, example_scenario
from bioprocess.simulate import simulate
from bioprocess.summary import fedbatch_volume_per_day, key_numbers

COLUMNS = {
    # name: (scenario kwargs, simulate kwargs, expected)
    "example": (dict(feed="= bleed"), {},
                dict(D=0.5415, fresh=6.800, harvest=0.0, peak_lac=26.66, end_lac=26.66, min_glc=0.56)),
    "suggested_hourly": (dict(feed="suggested"), {},
                         dict(D=0.7224, fresh=8.717, harvest=1.917, peak_lac=22.88, end_lac=20.00, min_glc=6.64)),
    "sheet_parity": (dict(feed="suggested"), dict(steps_per_day=1, fedbatch_feeding="bolus"),
                     dict(D=0.7224, fresh=8.717, harvest=1.917, peak_lac=23.82, end_lac=20.00, min_glc=6.64)),
}


@pytest.mark.parametrize("col", COLUMNS)
def test_reference_column(col):
    sc_kw, sim_kw, exp = COLUMNS[col]
    r = simulate(example_scenario(mu_digits=None, **sc_kw), **sim_kw)
    assert r.ok
    k = key_numbers(r)
    cont = r.plans[2]
    assert cont.bleed == pytest.approx(MU_FEDBATCH)
    assert cont.suggested_min_feed == pytest.approx(0.7224, abs=5e-5)
    assert cont.feed == pytest.approx(exp["D"], abs=5e-5)
    assert k["fresh_medium_L"] == pytest.approx(exp["fresh"], abs=5e-4)
    assert k["harvest_L"] == pytest.approx(exp["harvest"], abs=5e-4)
    assert k["max_volume_L"] == pytest.approx(1.06, abs=1e-9)
    assert k["cells_bled"] == pytest.approx(4.018e10, rel=5e-4)
    assert k["wb_total_g"] == pytest.approx(93.6, abs=0.05)
    assert r.table.Lactate.max() == pytest.approx(exp["peak_lac"], abs=5e-3)
    assert r.table.Lactate.iloc[-1] == pytest.approx(exp["end_lac"], abs=5e-3)
    assert r.table.Glucose.min() == pytest.approx(exp["min_glc"], abs=5e-3)
    fb = fedbatch_volume_per_day(r)
    assert fb.Day.tolist() == [3, 4] and fb["Volume added (L)"].tolist() == pytest.approx([0.03, 0.03])


def test_example_plan_warns_feed_below_suggestion():
    r = simulate(example_scenario())
    msgs = [i.message for i in r.issues if i.level == "warning"]
    assert any("below the suggested minimum" in m for m in msgs)
    assert any(m.startswith("Lactate exceeds") for m in msgs)
    assert any(m.startswith("Glucose drops below") for m in msgs)


def test_rounded_example_close_to_exact():
    exact = key_numbers(simulate(example_scenario(mu_digits=None)))
    shipped = key_numbers(simulate(example_scenario()))
    for k in exact:
        assert shipped[k] == pytest.approx(exact[k], rel=2e-4)
