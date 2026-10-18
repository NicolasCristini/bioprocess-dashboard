"""Entry point and router. Runs natively (`streamlit run app/Home.py`) and in the browser (stlite)."""
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
for p in (_here, _here.parent / "src"):          # stlite has no installed package: mount paths instead
    if p.is_dir() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

import streamlit as st  # noqa: E402

from bioprocess import registry  # noqa: E402
from bioprocess.checks import validate  # noqa: E402
from ui import state, theme  # noqa: E402

st.set_page_config(page_title="Bioprocess Phase Planner", page_icon=":material/science:", layout="wide")
theme.inject()
state.init()

pages = {
    "": [st.Page("pages/home.py", title="Overview", icon=":material/space_dashboard:", default=True)],
    "Inputs": [
        st.Page("pages/p1_setup.py", title="Setup", icon=":material/tune:", url_path="setup"),
        st.Page("pages/p2_phases.py", title="Phases", icon=":material/timeline:", url_path="phases"),
        st.Page("pages/p3_regimes.py", title="Feed regimes", icon=":material/water_drop:", url_path="regimes"),
    ],
    "Outputs": [
        st.Page("pages/p4_results.py", title="Results", icon=":material/monitoring:", url_path="results"),
        st.Page("pages/p5_compare.py", title="Compare", icon=":material/compare_arrows:", url_path="compare"),
    ],
    "Model": [st.Page("pages/model.py", title="Model", icon=":material/function:", url_path="model")],
    "Data": [st.Page("pages/library.py", title="My scenarios", icon=":material/folder_open:", url_path="scenarios")],
}
nav = st.navigation(pages)

with st.sidebar:
    sc = state.sc()
    issues = validate(sc)
    res = state.result()

    def status(where):
        lv = {i.level for i in issues + res.issues if i.where == where}
        return ("Fix", "danger") if "block" in lv else ("Check", "warning") if "warning" in lv else ("OK", "accent")

    run = ("Stopped", "danger") if res.blocked else ("Check", "warning") if any(
        i.level == "warning" for i in res.issues) else ("OK", "accent")
    st.html(f'<div class="bp-panel-title">{theme.esc(sc.name)}</div>')
    flags = []
    if state.ss.is_example:
        flags.append(("Placeholder values", "", ""))
    if state.unsaved():
        flags.append(("Unsaved", "", "warning"))
    if flags:
        theme.chips(flags)
    rows = [("Setup", *status("setup")), ("Phases", *status("phases")), ("Feed regimes", *status("regimes")),
            ("Results", *run)]
    st.html('<div class="bp-issues">' + "".join(
        f'<div class="bp-issue" style="grid-template-columns:1fr auto;padding:6px 10px"><div>{n}</div>'
        f'<span class="bp-chip {tone}" style="padding:1px 8px">{lbl}</span></div>' for n, lbl, tone in rows) + "</div>")
    # ---- model selector (bottom of the panel): run the same scenario with any model version in models/
    st.divider()
    cards = registry.discover()
    ids = list(cards)
    current = state.model().id
    chosen = st.selectbox("Model", ids, index=ids.index(current), format_func=lambda i: cards[i].label,
                          key="model_select", help="Runs the current scenario with this model version. "
                                                   "Details and model parameters: Model page.")
    if chosen != current:
        state.ss.model_id = chosen
        st.rerun()
    card = cards[chosen]
    theme.chips([(card.status.capitalize(), "", "accent" if card.status == "validated" else "warning")])
    st.caption(f"Runs in your browser. Inputs never leave it.")

nav.run()
state.autosave()
