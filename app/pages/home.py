import streamlit as st

from bioprocess.defaults import example_scenario
from bioprocess.io.scenario_file import from_text
from bioprocess.summary import key_numbers
from ui import state, theme
from ui.widgets import PHASE_COLOR, sci

theme.top("Bioprocess Phase Planner",
          "Predict cell density, metabolites, working volume, medium use and biomass, hour by hour, "
          "for a process built from batch, fed-batch and continuous phases.")

left, right = st.columns([3, 2], gap="large", vertical_alignment="center")
with left, st.container(horizontal=True, gap="small"):
    if st.button("Start from example", icon=":material/play_arrow:", type="primary"):
        state.replace(example_scenario(), example=True)
        st.switch_page("pages/p1_setup.py")
    if st.button("Open my scenarios", icon=":material/folder_open:"):
        st.switch_page("pages/library.py")
up = right.file_uploader("Open a scenario file (.yaml / .json)", type=["yaml", "yml", "json"],
                         label_visibility="collapsed")
if up is not None and st.session_state.get("_home_up") != up.file_id:
    st.session_state._home_up = up.file_id
    try:
        state.replace(from_text(up.getvalue().decode("utf-8")), saved=True)
        st.success(f"Loaded “{state.sc().name}”.")
    except ValueError as e:
        st.error(str(e))

steps = [
    ("Setup", "Vessel, working-volume window, seeding density and the metabolite table."),
    ("Phases", "Up to six phases, each with a duration and a specific growth rate µ."),
    ("Feed regimes", "Daily fed-batch feed as % of the initial volume, fed as a constant flow."),
    ("Results", "Key numbers, checks, charts and an hour-by-hour playback."),
    ("Compare", "Overlay saved scenarios and read the differences against a baseline."),
]
st.html('<div class="bp-steps">' + "".join(
    f'<div class="bp-step"><div class="n">{i}</div><div class="t">{theme.esc(t)}</div>'
    f'<div class="d">{theme.esc(d)}</div></div>' for i, (t, d) in enumerate(steps, 1)) + "</div>")

sc, res = state.sc(), state.result()
with st.container(border=True):
    h1, h2 = st.columns([4, 1], vertical_alignment="center")
    h1.html(f'<div class="bp-panel-title">Current scenario</div><div class="bp-panel-sub">{theme.esc(sc.name)}</div>')
    if h2.button("Open results", icon=":material/monitoring:", width="stretch"):
        st.switch_page("pages/p4_results.py")
    if sc.phases:
        st.html('<div class="bp-timeline">' + "".join(
            f'<div style="flex:{p.days};background:{PHASE_COLOR[p.type]}">{i}. {p.type}, {p.days} d</div>'
            for i, p in enumerate(sc.phases, 1)) + f'</div><div class="bp-axis"><span>day 0</span>'
            f'<span>day {sc.total_days}</span></div>')
    if res.ok:
        k = key_numbers(res)
        theme.kpis([dict(label="Total fresh medium", value=f"{k['fresh_medium_L']:.3f}", unit="L", lead=True),
                    dict(label="Total wet biomass", value=f"{k['wb_total_g']:.1f}", unit="g"),
                    dict(label="Final VCC", value=sci(k["final_vcc"]), unit="/mL"),
                    dict(label="Checks to review", value=str(sum(i.level == "warning" for i in res.issues)), unit="")])
    else:
        theme.issues([i for i in res.issues if i.level == "block"])

with st.expander("Model assumptions", icon=":material/info:"):
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
