import pytest

from bioprocess.defaults import example_scenario
from bioprocess.io.export import results_xlsx, table_csv
from bioprocess.io.scenario_file import from_text, to_json, to_yaml
from bioprocess.io.store import ScenarioStore, slug
from bioprocess.simulate import simulate
from bioprocess.summary import daily_table


def test_yaml_and_json_round_trip():
    sc = example_scenario()
    assert from_text(to_yaml(sc)) == sc
    assert from_text(to_json(sc)) == sc


def test_bad_files_raise_readable_errors():
    with pytest.raises(ValueError):
        from_text("just a string")
    with pytest.raises(ValueError):
        from_text("schema_version: 99\n")
    with pytest.raises(ValueError, match="invalid values"):
        from_text(to_yaml(example_scenario()).replace("days: 2", "days: -2", 1))


def test_store_save_list_load_delete_zip(tmp_path):
    st = ScenarioStore(tmp_path / "lib")
    sc = example_scenario()
    st.save(sc)
    sc2 = sc.model_copy(update={"name": "Variant / B"})
    st.save(sc2)
    names = {d["name"] for d in st.list()}
    assert names == {sc.name, "Variant / B"}
    f = next(d["file"] for d in st.list() if d["name"] == "Variant / B")
    assert st.load(f) == sc2
    data = st.export_all()
    other = ScenarioStore(tmp_path / "other")
    assert other.import_zip(data) == 2
    st.delete(f)
    assert len(st.list()) == 1
    assert st.clear() == 1 and st.list() == []
    assert slug("../../etc/passwd") == "etc-passwd"


def test_exports():
    r = simulate(example_scenario())
    assert table_csv(r).startswith(b"step,t_h")
    d = daily_table(r)
    assert len(d) == 15 and d.day.tolist() == list(range(15))
    assert d.fb_feed_L.sum() == pytest.approx(0.06)
    assert results_xlsx(r)[:2] == b"PK"


def test_autosave_round_trip(tmp_path):
    st = ScenarioStore(tmp_path)
    assert st.restore() is None
    sc = example_scenario("suggested")
    st.autosave(sc, {"is_example": False, "saved_json": None})
    got, meta = st.restore()
    assert got == sc and meta["is_example"] is False
    assert st.list() == []          # the working copy is not a saved scenario
    (tmp_path / st.AUTOSAVE).write_text("{broken")
    assert st.restore() is None
