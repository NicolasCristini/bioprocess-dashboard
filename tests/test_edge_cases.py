import pytest
from pydantic import ValidationError

from bioprocess.defaults import example_scenario
from bioprocess.models import BatchPhase, ContinuousPhase, FedBatchPhase, Metabolite, Setup
from bioprocess.simulate import simulate


def blocks(r):
    return [i.message for i in r.issues if i.level == "block"]


def test_volume_above_vmax_stops_run():
    sc = example_scenario()
    sc.setup = Setup(v_max_L=1.03)        # Regime A reaches 1.06 L
    r = simulate(sc)
    assert r.blocked and not r.ok
    assert r.stopped_at_h is not None and 48 < r.stopped_at_h <= 96
    assert r.table.volume_L.iloc[-1] > 1.03 and r.table.volume_L.iloc[:-1].max() <= 1.03
    assert any("above V_max" in m for m in blocks(r))


def test_v0_outside_window_is_input_error():
    sc = example_scenario()
    sc.setup = Setup(v_min_L=1.5)
    r = simulate(sc)
    assert r.table.empty and any("between" in m for m in blocks(r))


def test_vmax_above_vessel_is_input_error():
    sc = example_scenario()
    sc.setup = Setup(v_max_L=3)
    assert any("larger than the vessel" in m for m in blocks(simulate(sc)))


def test_feed_below_bleed_blocks():
    sc = example_scenario()
    sc.phases[2] = ContinuousPhase(days=10, mu=0.5, bleed_vvd=0.5, feed_vvd=0.3)
    assert any("below bleed" in m for m in blocks(simulate(sc)))


def test_feed_above_bleed_warns_harvest():
    sc = example_scenario()
    sc.phases[2] = ContinuousPhase(days=10, mu=0.5, bleed_vvd=0.5, feed_vvd=0.8)
    r = simulate(sc)
    assert r.ok and any("harvest" in i.message for i in r.issues if i.level == "warning")


def test_hard_caps():
    sc = example_scenario()
    sc.phases = [BatchPhase(days=1, mu=0.1) for _ in range(7)]
    assert any("At most 6 phases" in m for m in blocks(simulate(sc)))
    sc.phases = [BatchPhase(days=121, mu=0.0)]
    assert any("exceeds 120 days" in m for m in blocks(simulate(sc)))
    sc.phases = [FedBatchPhase(days=31, mu=0.1, regime="Regime B")]
    assert any("at most 30 days" in m for m in blocks(simulate(sc)))


def test_unknown_regime_blocks():
    sc = example_scenario()
    sc.phases[1] = FedBatchPhase(days=2, mu=0.5, regime="Nope")
    assert any("does not exist" in m for m in blocks(simulate(sc)))


def test_pydantic_rejects_bad_values():
    with pytest.raises(ValidationError):
        BatchPhase(days=0, mu=0.5)
    with pytest.raises(ValidationError):
        BatchPhase(days=2.5, mu=0.5)
    with pytest.raises(ValidationError):
        Setup(seeding_density=0)


def test_mu_zero_holds_and_negative_mu_info():
    sc = example_scenario()
    sc.phases = [BatchPhase(days=3, mu=0.0), BatchPhase(days=2, mu=-0.1)]
    r = simulate(sc)
    assert r.ok
    assert r.table.vcc.iloc[:73].nunique() == 1
    assert any(i.level == "info" and "declines" in i.message for i in r.issues)


def test_missing_perfusion_concentration_blanks_metabolite():
    sc = example_scenario()
    sc.metabolites[0] = Metabolite(name="Glucose", kind="consumed", q=7.9, limit=5, c_batch=25, c_fedbatch=250)
    r = simulate(sc)
    assert r.ok
    assert r.table[r.table.type == "Continuous"].Glucose.isna().all()
    assert r.table[r.table.type != "Continuous"].Glucose.notna().all()
    assert any(i.level == "info" and "Glucose" in i.message for i in r.issues)


def test_depletion_reported():
    sc = example_scenario()
    sc.phases = [BatchPhase(days=8, mu=0.5)]
    r = simulate(sc)
    assert r.table.Glucose.min() == 0
    assert any("depleted" in i.message for i in r.issues)
