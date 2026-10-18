"""Session state: the active scenario, widget keys, the cached simulation and the scenario library."""
from __future__ import annotations

import streamlit as st

from bioprocess.defaults import example_scenario
from bioprocess.io.scenario_file import to_json
from bioprocess.io.store import IN_BROWSER, ScenarioStore
from bioprocess.models import Scenario
from bioprocess.simulate import SimResult, simulate

ss = st.session_state


def init() -> None:
    if "scenario" not in ss:
        restored = store().restore()
        if restored:                            # working copy from the previous session (reload-safe)
            ss.scenario, meta = restored
            ss.saved_json = meta.get("saved_json")
            ss.is_example = meta.get("is_example", False)
        else:
            ss.scenario = example_scenario()
            ss.saved_json = to_json(ss.scenario)   # last saved/loaded version, for "unsaved changes"
            ss.is_example = True
        ss.rev = 0


def autosave() -> None:
    """Persist the working copy when it changed (called once per run by the router)."""
    j = to_json(sc())
    if ss.get("_autosaved") != j:
        store().autosave(sc(), {"saved_json": ss.saved_json, "is_example": ss.is_example})
        ss._autosaved = j


def sc() -> Scenario:
    init()
    return ss.scenario


def replace(new: Scenario, *, saved: bool = False, example: bool = False) -> None:
    """Swap the active scenario and reset every input widget."""
    ss.scenario = new
    ss.rev += 1
    ss.saved_json = to_json(new) if saved or example else None
    ss.is_example = example


def bump() -> None:
    """Reset widgets after a structural change (phase added/removed/moved/retyped)."""
    ss.rev += 1


def key(name: str) -> str:
    return f"r{ss.rev}:{name}"


def unsaved() -> bool:
    return ss.saved_json != to_json(sc())


def result() -> SimResult:
    """Simulate the active scenario, re-running only when it changed."""
    j = to_json(sc())
    if ss.get("_res_key") != j:
        ss._res = simulate(sc())
        ss._res_key = j
    return ss._res


def store() -> ScenarioStore:
    if "_store" not in ss:
        ss._store = ScenarioStore()
    return ss._store


STORAGE_NOTE = ("Saved in this browser (IndexedDB). Clearing site data deletes them; download a backup."
                if IN_BROWSER else "Saved in the project's scenarios/private/ folder (not in git).")
