import math

import pytest

from bioprocess.defaults import example_scenario
from bioprocess.models import ContinuousPhase
from bioprocess.simulate import simulate

CASES = [(n, f, feed) for n in (1, 24) for f in ("flow", "bolus") for feed in ("= bleed", "suggested")]


@pytest.mark.parametrize("n,feeding,feed", CASES)
def test_volume_balance(n, feeding, feed):
    r = simulate(example_scenario(feed), steps_per_day=n, fedbatch_feeding=feeding)
    last = r.table.iloc[-1]
    assert last.cum_fresh_L == pytest.approx(last.volume_L + last.cum_bleed_L + last.cum_harvest_L, rel=1e-12)


@pytest.mark.parametrize("n", [1, 24])
def test_bleed_equal_mu_holds_vcc(n):
    r = simulate(example_scenario(), steps_per_day=n)
    cont = r.table[r.table.type == "Continuous"]
    assert cont.vcc.to_numpy() == pytest.approx(r.plans[2].x_start, rel=1e-12)


def test_feed_equals_bleed_gives_no_harvest_and_constant_volume():
    r = simulate(example_scenario("= bleed"))
    cont = r.table[r.table.type == "Continuous"]
    assert cont.harvest_L.abs().max() < 1e-15
    assert cont.volume_L.nunique() == 1


def test_long_continuous_phase_reaches_steady_state():
    sc = example_scenario("suggested")
    sc.phases[2] = ContinuousPhase(days=60, mu=sc.phases[2].mu, feed_vvd="suggested")
    r = simulate(sc)
    p = r.plans[2]
    lac = sc.metabolites[1]
    c_star = lac.c_perfusion + lac.q * 24e-8 * p.x_start / p.feed
    assert r.table.Lactate.iloc[-1] == pytest.approx(c_star, rel=1e-9)


def test_vcc_independent_of_step_and_daily_rows_match():
    daily = simulate(example_scenario(), steps_per_day=1).table
    hourly = simulate(example_scenario(), steps_per_day=24).table
    at_days = hourly[hourly.step % 24 == 0].reset_index(drop=True)
    assert at_days.vcc.to_numpy() == pytest.approx(daily.vcc.to_numpy(), rel=1e-12)


@pytest.mark.parametrize("n", [1, 24])
def test_end_of_day_volume_same_in_both_feeding_modes(n):
    flow = simulate(example_scenario(), steps_per_day=n, fedbatch_feeding="flow").table
    bolus = simulate(example_scenario(), steps_per_day=n, fedbatch_feeding="bolus").table
    f = flow[flow.step % n == 0].volume_L.to_numpy()
    b = bolus[bolus.step % n == 0].volume_L.to_numpy()
    assert f == pytest.approx(b, rel=1e-12)


def test_cells_produced_identity():
    from bioprocess.summary import key_numbers
    k = key_numbers(simulate(example_scenario()))
    assert k["cells_produced"] == pytest.approx(k["cells_end"] + k["cells_bled"] - k["cells_inoculated"])
    assert k["wb_total_g"] == pytest.approx(k["cells_produced"] * 2.0 / 1e9)
    assert not math.isnan(k["wb_total_g"])
