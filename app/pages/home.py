import streamlit as st

from bioprocess.defaults import example_scenario
from bioprocess.io.scenario_file import from_text
from ui import state

st.title("Bioprocess Phase Planner")
st.markdown("Predicts **cell density, metabolites, working volume, medium use and biomass**, hour by hour, "
            "for a process built from up to six phases: **batch**, **fed-batch** and **continuous** "
            "(bleed & feed). Compare scenarios side by side.")

c1, c2, c3 = st.columns(3)
if c1.button("Start from the example plan", icon="🧪", width="stretch"):
    state.replace(example_scenario(), example=True)
    st.switch_page("pages/p1_setup.py")
if c2.button("Open my scenarios", icon="🗂️", width="stretch"):
    st.switch_page("pages/library.py")
up = c3.file_uploader("Open a scenario file (.yaml / .json)", type=["yaml", "yml", "json"],
                      label_visibility="collapsed")
if up is not None and st.session_state.get("_home_up") != up.file_id:
    st.session_state._home_up = up.file_id
    try:
        state.replace(from_text(up.getvalue().decode("utf-8")), saved=True)
        st.success(f"Loaded “{state.sc().name}”.")
    except ValueError as e:
        st.error(str(e))

st.subheader("How to use it — 5 steps")
st.markdown("""
1. **Setup**: vessel, working-volume window (V_min / V_max), seeding density and the metabolite table.
2. **Phases**: add up to 6 phases. Each needs a duration and a specific growth rate **µ**.
   Fed-batch phases pick a feed regime; continuous phases set the bleed (and feed, = bleed by default).
3. **Feed regimes**: the daily feed volume (% of the initial working volume) for fed-batch phases,
   fed as a constant flow over the day.
4. **Results**: key numbers, checks, charts and an hour-by-hour playback.
5. **Compare**: overlay saved scenarios and see the differences.

Status marks in the sidebar: ✓ fine · ⚠ check this · ⛔ must be fixed before results are shown.
""")

with st.expander("Model assumptions (MODEL.md §4)"):
    st.markdown("""
- Growth follows the **µ you enter per phase**; it does not respond to metabolite levels.
- Specific rates **q** are constant; viability is 100 %; cell death is not modelled.
- Wet biomass scales linearly with cell density (placeholder factor).
- Continuous phases run with **feed = bleed** by default: constant volume, no harvest. A feed above the bleed
  draws a cell-free harvest (feed − bleed) that keeps the volume constant.
- Fed-batch feed is a constant flow over each phase day, as % of the **initial** working volume.
- Ideal mixing; no sampling, evaporation or base addition.
- **All example numbers are placeholders**, not measured values.
""")
