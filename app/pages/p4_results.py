import streamlit as st

from bioprocess.io.export import table_csv
from bioprocess.summary import (KEY_NUMBERS, daily_table, fedbatch_volume_per_day, key_numbers, metabolite_check,
                                phase_summary)
from ui import charts, state
from ui.widgets import sci, show_issues

sc = state.sc()
r = state.result()
st.title("4 · Results")
st.caption(f"{sc.name} · {'hourly' if r.steps_per_day == 24 else 'daily'} resolution")

if r.table.empty:
    st.error("No results: fix the problems below first.", icon="⛔")
    show_issues(r.issues)
    st.stop()

k = key_numbers(r)
if r.blocked:
    st.error(f"⛔ Run stopped early — results are shown up to day {r.table.t_d.iloc[-1]:.2f} and are not valid.")

t1 = st.columns(4)
t1[0].metric("Total fresh medium", f"{k['fresh_medium_L']:.3f} L")
t1[1].metric("Max working volume", f"{k['max_volume_L']:.3f} L", help=f"Window {sc.setup.v_min_L:g}–{sc.setup.v_max_L:g} L")
t1[2].metric("Total cells produced", sci(k["cells_produced"]))
t1[3].metric("Total wet biomass", f"{k['wb_total_g']:.1f} g")
t2 = st.columns(4)
t2[0].metric("Final VCC (cells/mL)", sci(k["final_vcc"]))
t2[1].metric("Harvest (cell-free)", f"{k['harvest_L']:.3f} L")
t2[2].metric("Bleed", f"{k['bleed_L']:.3f} L")
t2[3].metric("Wet biomass in bleed", f"{k['wb_bleed_g']:.1f} g")

problems = [i for i in r.issues if i.level != "info"]
with st.expander(f"Checks — {sum(i.level == 'block' for i in problems)} ⛔ · "
                 f"{sum(i.level == 'warning' for i in problems)} ⚠", expanded=bool(problems)):
    show_issues(r.issues, empty="All checks passed.")

tab_charts, tab_play, tab_phase, tab_met, tab_table = st.tabs(
    ["📈 Charts", "▶ Hourly playback", "Per phase", "Metabolite check", "Time table"])

with tab_charts:
    t_end_h = int(round(r.table.t_h.iloc[-1]))
    c0, c1 = st.columns([4, 1])
    hour = c0.slider("Inspect hour", 0, t_end_h, t_end_h, 1, key="inspect_h",
                     help="Moves the dotted marker on every chart and fills the 'state at t' card.")
    log = c1.toggle("Log VCC axis", False)
    t_d = hour / 24
    row = r.table.iloc[(r.table.t_h - hour).abs().idxmin()]
    st.markdown(
        f"**State at day {int(t_d)} · hour {hour % 24:02d}** (phase {int(row.phase)}, {row.type}) — "
        f"VCC {sci(row.vcc)} /mL · V {row.volume_L:.3f} L · "
        + " · ".join(f"{m} {row[m]:.2f} mM" for m in r.metabolite_names if m in row and row[m] == row[m])
        + f" · fresh medium {row.cum_fresh_L:.3f} L · wet biomass bled {row.cum_wb_bleed_g:.2f} g")
    a, b = st.columns(2)
    a.plotly_chart(charts.vcc(r, log, t_d), width="stretch")
    b.plotly_chart(charts.metabolites(r, t_d), width="stretch")
    a.plotly_chart(charts.volume(r, t_d), width="stretch")
    b.plotly_chart(charts.cumulative(r, t_d), width="stretch")
    a.plotly_chart(charts.biomass(r, t_d), width="stretch")
    fb = fedbatch_volume_per_day(r)
    if len(fb):
        b.plotly_chart(charts.fedbatch_bars(fb), width="stretch")
    st.caption("Shaded bands: orange = fed-batch, blue = continuous.")

with tab_play:
    st.caption("Press ▶ Play or drag the slider: the four panels draw the process up to that time.")
    st.plotly_chart(charts.playback(r), width="stretch", config={"displayModeBar": False})

with tab_phase:
    ps = phase_summary(r)
    st.dataframe(ps, hide_index=True, width="stretch",
                 column_config={c: st.column_config.NumberColumn(format="%.3e") for c in ("Start VCC", "End VCC", "Cells bled")})
    if len(fb):
        st.markdown("**Fed-batch volume added per day**")
        st.dataframe(fb, hide_index=True)

with tab_met:
    st.dataframe(metabolite_check(r), hide_index=True, width="stretch")

with tab_table:
    daily = st.toggle("Daily rows (end-of-day states, flows summed per day)", True)
    tb = daily_table(r) if daily else r.table
    st.dataframe(tb, hide_index=True, width="stretch", height=420)

st.divider()
d1, d2, d3, _ = st.columns([1, 1, 1, 2])
d1.download_button("⬇ CSV (hourly)", table_csv(r), f"{sc.name}_hourly.csv", "text/csv")
d2.download_button("⬇ CSV (daily)", table_csv(r, daily=True), f"{sc.name}_daily.csv", "text/csv")
if d3.button("Prepare Excel"):
    from bioprocess.io.export import results_xlsx   # lazy: openpyxl is slow to import in the browser
    st.session_state._xlsx = (sc.name, results_xlsx(r))
if st.session_state.get("_xlsx") and st.session_state._xlsx[0] == sc.name:
    d3.download_button("⬇ Excel", st.session_state._xlsx[1], f"{sc.name}.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
with st.expander("All key numbers"):
    st.dataframe([{"Key number": KEY_NUMBERS[x][0], "Value": KEY_NUMBERS[x][2].format(v), "Unit": KEY_NUMBERS[x][1]}
                  for x, v in k.items()], hide_index=True, width="stretch")
