"""Smoke-test every Streamlit page headlessly (native mode)."""
import sys
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))
PAGES = sorted((APP / "pages").glob("*.py"))


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.stem)
def test_page_runs_without_exception(page, tmp_path, monkeypatch):
    monkeypatch.setattr("bioprocess.io.store.default_dir", lambda: tmp_path / "lib")
    at = AppTest.from_file(str(page), default_timeout=60)
    at.run()
    assert not at.exception, [e.message for e in at.exception]


def test_router_runs(tmp_path, monkeypatch):
    monkeypatch.setattr("bioprocess.io.store.default_dir", lambda: tmp_path / "lib")
    at = AppTest.from_file(str(APP / "Home.py"), default_timeout=60)
    at.run()
    assert not at.exception, [e.message for e in at.exception]


def test_results_page_shows_reference_numbers(tmp_path, monkeypatch):
    monkeypatch.setattr("bioprocess.io.store.default_dir", lambda: tmp_path / "lib")
    at = AppTest.from_file(str(APP / "pages" / "p4_results.py"), default_timeout=60)
    at.run()
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Total fresh medium"] == "6.800 L"
    assert metrics["Max working volume"] == "1.060 L"
    assert metrics["Total wet biomass"] == "93.6 g"


def test_compare_page_with_saved_scenarios(tmp_path, monkeypatch):
    from bioprocess.defaults import example_scenario
    from bioprocess.io.store import ScenarioStore

    lib = tmp_path / "lib"
    monkeypatch.setattr("bioprocess.io.store.default_dir", lambda: lib)
    st_ = ScenarioStore(lib)
    a = example_scenario("suggested")
    a.name = "Suggested feed"
    st_.save(a)
    b = example_scenario()
    b.name = "Too much feed"
    b.setup = b.setup.model_copy(update={"v_max_L": 1.03})   # blocked run: listed, not overlaid
    st_.save(b)
    at = AppTest.from_file(str(APP / "pages" / "p5_compare.py"), default_timeout=60)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert any("Too much feed" in w.value for w in at.warning)
    df = at.dataframe[0].value
    assert "Current" in df.columns and "Suggested feed" in df.columns
    row = [i for i in df.index if i.startswith("Total fresh medium")][0]
    assert df.loc[row, "Current"] == pytest.approx(6.8, abs=1e-4)          # example rounds µ to 5 digits
    assert df.loc[row, "Suggested feed"] == pytest.approx(8.71744, abs=1e-3)
    assert df.loc[row, "Δ% Suggested feed"] == pytest.approx((8.71744 / 6.8 - 1) * 100, abs=0.05)


def test_library_save_button(tmp_path, monkeypatch):
    lib = tmp_path / "lib"
    monkeypatch.setattr("bioprocess.io.store.default_dir", lambda: lib)
    at = AppTest.from_file(str(APP / "pages" / "library.py"), default_timeout=60)
    at.run()
    save = next(b for b in at.button if b.label == "💾 Save")
    save.click().run()
    assert not at.exception
    assert [p.name for p in lib.glob("*.yaml")] == ["Example-plan-placeholder-values.yaml"]
