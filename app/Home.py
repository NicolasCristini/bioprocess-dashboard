"""Entry point and router. Runs natively (`streamlit run app/Home.py`) and in the browser (stlite)."""
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
for p in (_here, _here.parent / "src"):          # stlite has no installed package: mount paths instead
    if p.is_dir() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

import streamlit as st  # noqa: E402

from bioprocess import MODEL_VERSION  # noqa: E402
from bioprocess.checks import validate  # noqa: E402
from ui import state  # noqa: E402

st.set_page_config(page_title="Bioprocess Phase Planner", page_icon="🧫", layout="wide")
state.init()

pages = {
    "": [st.Page("pages/home.py", title="Start here", icon="🏠", default=True)],
    "Inputs": [
        st.Page("pages/p1_setup.py", title="1 · Setup", icon="⚙️", url_path="setup"),
        st.Page("pages/p2_phases.py", title="2 · Phases", icon="🧩", url_path="phases"),
        st.Page("pages/p3_regimes.py", title="3 · Feed regimes", icon="💧", url_path="regimes"),
    ],
    "Outputs": [
        st.Page("pages/p4_results.py", title="4 · Results", icon="📈", url_path="results"),
        st.Page("pages/p5_compare.py", title="5 · Compare", icon="⚖️", url_path="compare"),
    ],
    "Data": [st.Page("pages/library.py", title="My scenarios", icon="🗂️", url_path="scenarios")],
}
nav = st.navigation(pages)

with st.sidebar:
    sc = state.sc()
    st.markdown(f"**{sc.name}**")
    if state.ss.is_example:
        st.caption("🏷️ Example — placeholder values")
    if state.unsaved():
        st.caption("● unsaved changes — save in *My scenarios*")
    issues = validate(sc)
    res = state.result()
    run_issues = [i for i in res.issues if i.where == "results" or i.level == "warning"]

    def status(where):
        lv = {i.level for i in issues + res.issues if i.where == where}
        return "⛔" if "block" in lv else "⚠" if "warning" in lv else "✓"

    st.markdown(f"{status('setup')} Setup  \n{status('phases')} Phases  \n{status('regimes')} Feed regimes  \n"
                f"{'⛔' if res.blocked else '⚠' if run_issues else '✓'} Results")
    st.divider()
    st.caption(f"🔒 Your inputs never leave this computer.  \nModel {MODEL_VERSION} · see MODEL.md")

nav.run()
state.autosave()
