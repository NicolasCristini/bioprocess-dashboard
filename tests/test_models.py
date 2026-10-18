"""Model versions: discovery, the v1 wrapper, v2 Monod reduction to v1, v2 reference values (MODEL2.md §6)."""
import math

import pytest

from bioprocess import registry
from bioprocess.defaults import example_scenario
from bioprocess.io.scenario_file import from_text, to_yaml
from bioprocess.simulate import simulate as core
from bioprocess.summary import key_numbers

CARDS = registry.discover()


def test_discovery_and_cards():
    assert list(CARDS)[:2] == ["v1-baseline", "v2-monod"]
    v1, v2 = CARDS["v1-baseline"], CARDS["v2-monod"]
    assert v1.status == "validated" and v2.status == "development"
    assert v1.spec_file.name == "MODEL.md" and "Bioprocess Phase Planner model" in v1.spec_text()
    assert "Monod" in v2.spec_text() and not v2.spec_text().startswith("---")
    assert registry.get("does-not-exist").id == "v1-baseline"


def test_v1_wrapper_is_the_core():
    sc = example_scenario()
    a, b = CARDS["v1-baseline"].simulate(sc), core(sc)
    assert a.model_id == "v1-baseline"
    assert a.table.equals(b.table)


@pytest.mark.parametrize("feed", ["= bleed", "suggested"])
@pytest.mark.parametrize("n", [1, 24])
def test_v2_without_constants_equals_v1(feed, n):
    sc = example_scenario(feed)
    v1 = core(sc, steps_per_day=n)
    v2 = CARDS["v2-monod"]._module().simulate(sc, params={}, steps_per_day=n)
    for c in v1.table.columns:
        if v1.table[c].dtype == object:
            assert (v1.table[c] == v2.table[c]).all()
        else:
            assert v2.table[c].to_numpy() == pytest.approx(v1.table[c].to_numpy(), rel=1e-12, abs=1e-12, nan_ok=True), c
    assert (v2.table.mu_eff == v2.table.mu_eff).all()


REF = {  # MODEL2.md §6
    "= bleed": dict(fresh=6.644, final_vcc=5.223e6, wet=76.53, glc_min=5.111, lac_max=24.93, lac_end=21.50, mu_min=0.4933),
    "suggested": dict(fresh=8.347, final_vcc=5.882e6, wet=81.32, glc_min=8.505, lac_max=22.15, lac_end=18.02, mu_min=0.5114),
}


@pytest.mark.parametrize("feed", REF)
def test_v2_reference_values(feed):
    r = CARDS["v2-monod"].simulate(example_scenario(feed))
    k, e = key_numbers(r), REF[feed]
    assert r.model_id == "v2-monod"
    assert k["fresh_medium_L"] == pytest.approx(e["fresh"], abs=5e-4)
    assert k["final_vcc"] == pytest.approx(e["final_vcc"], rel=5e-4)
    assert k["wb_total_g"] == pytest.approx(e["wet"], abs=5e-3)
    assert r.table.Glucose.min() == pytest.approx(e["glc_min"], abs=5e-3)
    assert r.table.Lactate.max() == pytest.approx(e["lac_max"], abs=5e-3)
    assert r.table.Lactate.iloc[-1] == pytest.approx(e["lac_end"], abs=5e-3)
    assert r.table.mu_eff.min() == pytest.approx(e["mu_min"], abs=5e-5)
    assert any("drifts" in i.message for i in r.issues)


def test_v2_volume_balance_and_glucose_positive():
    r = CARDS["v2-monod"].simulate(example_scenario())
    last = r.table.iloc[-1]
    assert last.cum_fresh_L == pytest.approx(last.volume_L + last.cum_bleed_L + last.cum_harvest_L, rel=1e-12)
    assert r.table.Glucose.min() > 0


def test_inhibition_slows_growth():
    sc = example_scenario()
    base = CARDS["v2-monod"].simulate(sc)
    sc.model_params = {"v2-monod": {"Lactate": {"Ki": 20}}}
    inhibited = CARDS["v2-monod"].simulate(sc)
    assert key_numbers(inhibited)["final_vcc"] < key_numbers(base)["final_vcc"]
    assert any("Lactate" in i.message for i in inhibited.issues if i.level == "info")


def test_scenario_params_override_defaults_and_round_trip():
    sc = example_scenario()
    sc.model_params = {"v2-monod": {"Glucose": {"Ks": None}}}
    assert CARDS["v2-monod"].params_for(sc)["Glucose"]["Ks"] is None
    back = from_text(to_yaml(sc))
    assert back.model_params == sc.model_params
    # Ks blank and glutamine not modelled -> v2 equals v1 for the example
    assert key_numbers(CARDS["v2-monod"].simulate(sc))["final_vcc"] == pytest.approx(7e6, rel=1e-4)
    assert not math.isnan(key_numbers(CARDS["v2-monod"].simulate(sc))["wb_total_g"])


def test_every_model_card_spec_resolves_in_a_built_site(tmp_path):
    """Run the registry against a built site's layout, as the browser does (catches specs the build forgets)."""
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    if not (root / "web" / "vendor" / "pyodide" / "pyodide.mjs").exists():
        pytest.skip("runtime not vendored")
    sys.path.insert(0, str(root / "scripts"))
    from build_site import build
    out = build("/", tmp_path / "dist")
    cards = registry.discover(out / "models")
    assert set(cards) == set(CARDS)
    for c in cards.values():
        assert not c.spec_text().startswith("*Specification file not found"), c.id
