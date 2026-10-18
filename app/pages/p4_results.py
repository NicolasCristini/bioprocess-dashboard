import streamlit as st

from bioprocess.io.export import table_csv
from bioprocess.summary import (KEY_NUMBERS, daily_table, fedbatch_volume_per_day, key_numbers, metabolite_check,
                                phase_summary)
from ui import charts, state, theme
from ui.widgets import sci, show_issues

sc = state.sc()
r = state.result()
n_block = sum(i.level == "block" for i in r.issues)
n_warn = sum(i.level == "warning" for i in r.issues)
card = state.model()
theme.top("Results", sc.name,
          [("Model", card.label, "" if card.status == "validated" else "warning"),
           ("Resolution", "hourly" if r.steps_per_day == 24 else "daily", ""),
           ("Blocking", str(n_block), "danger") if n_block else ("Run", "complete", "accent"),
           ("Checks", str(n_warn), "warning" if n_warn else "")])

if r.table.empty:
    st.error("No results yet: fix the blocking problems below.", icon=":material/block:")
    show_issues(r.issues)
    st.stop()

k = key_numbers(r)
if r.blocked:
    st.error(f"The run stopped early. Results are shown up to day {r.table.t_d.iloc[-1]:.2f} and are not valid.",
             icon=":material/block:")

theme.kpis([
    dict(label="Total fresh medium", value=f"{k['fresh_medium_L']:.3f}", unit="L", lead=True,
         hint=f"{k['perf_medium_L']:.2f} L perfusion, {k['fb_feed_L']:.2f} L fed-batch"),
    dict(label="Total wet biomass", value=f"{k['wb_total_g']:.1f}", unit="g", hint=f"{k['wb_bleed_g']:.1f} g leaves with the bleed"),
    dict(label="Cells produced", value=sci(k["cells_produced"]), unit="cells", hint=f"final VCC {sci(k['final_vcc'])} /mL"),
    dict(label="Max working volume", value=f"{k['max_volume_L']:.3f}", unit="L",
         hint=f"window {sc.setup.v_min_L:g} to {sc.setup.v_max_L:g} L"),
    dict(label="Bleed", value=f"{k['bleed_L']:.3f}", unit="L"),
    dict(label="Harvest (cell-free)", value=f"{k['harvest_L']:.3f}", unit="L"),
    dict(label="Cells removed by bleed", value=sci(k["cells_bled"]), unit="cells"),
    dict(label="Duration", value=f"{k['duration_d']:.0f}", unit="days"),
])

problems = [i for i in r.issues if i.level != "info"]
with st.expander(f"Checks: {n_block} blocking, {n_warn} to review", expanded=bool(problems), icon=":material/fact_check:"):
    show_issues(r.issues, empty="All checks passed.")

tab_charts, tab_play, tab_phase, tab_met, tab_table = st.tabs(
    ["Charts", "Hourly playback", "Per phase", "Metabolites", "Time table"])

with tab_charts:
    t_end_h = int(round(r.table.t_h.iloc[-1]))
    c0, c1 = st.columns([5, 1], vertical_alignment="bottom")
    hour = c0.slider("Inspect hour", 0, t_end_h, t_end_h, 1, key="inspect_h",
                     help="Moves the dotted marker on every chart and updates the state below.")
    log = c1.toggle("Log VCC", False)
    t_d = hour / 24
    row = r.table.iloc[(r.table.t_h - hour).abs().idxmin()]
    theme.chips([("Day", f"{int(t_d)} h{hour % 24:02d}", "accent"), ("Phase", f"{int(row.phase)} {row.type}", ""),
                 ("VCC", sci(row.vcc), ""), ("Volume", f"{row.volume_L:.3f} L", "")]
                + [(m, f"{row[m]:.2f} mM", "") for m in r.metabolite_names if m in row and row[m] == row[m]]
                + [("Fresh medium", f"{row.cum_fresh_L:.3f} L", ""), ("Biomass bled", f"{row.cum_wb_bleed_g:.2f} g", "")])
    st.caption("Each chart: camera icon (top right) saves a PNG; Plot SVG, Legend and Data CSV below it. "
               "Shaded bands mark fed-batch (amber) and continuous (blue) phases.")
    fb = fedbatch_volume_per_day(r)
    figs = [("vcc", charts.vcc(r, log, t_d)), ("metabolites", charts.metabolites(r, t_d)),
            ("volume", charts.volume(r, t_d)), ("cumulative", charts.cumulative(r, t_d)),
            ("biomass", charts.biomass(r, t_d))] + ([("fedbatch", charts.fedbatch_bars(fb))] if len(fb) else []) \
        + ([("mu_eff", charts.growth_rate(r, t_d))] if "mu_eff" in r.table else [])
    for i in range(0, len(figs), 2):
        cols = st.columns(2, gap="medium")
        for col, (key, fig) in zip(cols, figs[i:i + 2]):
            with col:
                charts.show(fig, key, sc.name)

with tab_play:
    st.caption("Press Play or drag the slider: the four panels draw the process up to that time.")
    st.plotly_chart(theme.white(charts.playback(r)), width="stretch", config={"displayModeBar": False}, theme=None)
    st.caption("To export a chart, use the Charts tab: every chart there has PNG, SVG, legend and data downloads.")

with tab_phase:
    ps = phase_summary(r)
    st.dataframe(ps, hide_index=True, width="stretch",
                 column_config={c: st.column_config.NumberColumn(format="%.3e") for c in ("Start VCC", "End VCC", "Cells bled")})
    if len(fb):
        theme.panel_title("Fed-batch volume added per day")
        st.dataframe(fb, hide_index=True)

with tab_met:
    st.dataframe(metabolite_check(r), hide_index=True, width="stretch")

with tab_table:
    daily = st.toggle("Daily rows (end-of-day states, flows summed per day)", True)
    tb = daily_table(r) if daily else r.table
    st.dataframe(tb, hide_index=True, width="stretch", height=420)

st.divider()
theme.panel_title("Export")
d1, d2, d3, _ = st.columns([1, 1, 1, 2])
d1.download_button("CSV hourly", table_csv(r), f"{sc.name}_hourly.csv", "text/csv", icon=":material/download:",
                   width="stretch", on_click="ignore")
d2.download_button("CSV daily", table_csv(r, daily=True), f"{sc.name}_daily.csv", "text/csv",
                   icon=":material/download:", width="stretch", on_click="ignore")
if st.session_state.get("_xlsx") and st.session_state._xlsx[0] == sc.name:
    d3.download_button("Excel", st.session_state._xlsx[1], f"{sc.name}.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       icon=":material/download:", type="primary", width="stretch", on_click="ignore")
elif d3.button("Prepare Excel", icon=":material/table_view:", width="stretch"):
    from bioprocess.io.export import results_xlsx   # lazy: openpyxl is slow to import in the browser
    st.session_state._xlsx = (sc.name, results_xlsx(r))
    st.rerun()
with st.expander("All key numbers", icon=":material/list:"):
    st.dataframe([{"Key number": KEY_NUMBERS[x][0], "Value": KEY_NUMBERS[x][2].format(v), "Unit": KEY_NUMBERS[x][1]}
                  for x, v in k.items()], hide_index=True, width="stretch")
