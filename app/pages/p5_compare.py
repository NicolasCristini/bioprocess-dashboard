import plotly.graph_objects as go
import streamlit as st

from bioprocess.compare import key_numbers_table, long_series
from bioprocess.simulate import simulate
from ui import state
from ui.charts import SCEN_COLORS, _layout

st.title("5 · Compare")
st.caption("Overlay the current scenario and saved ones. Runs that were stopped (⛔) are listed but not overlaid.")

store = state.store()
saved = [d for d in store.list() if d["ok"]]
CURRENT = f"● Current: {state.sc().name}"
options = [CURRENT] + [d["name"] for d in saved]
pick = st.multiselect("Scenarios (2–6)", options, default=options[: min(3, len(options))], max_selections=6)
if len(pick) < 2:
    st.info("Pick at least two scenarios. Save variants in **My scenarios** (e.g. *Save as copy* after a change).")
    st.stop()

results = {}
for name in pick:
    if name == CURRENT:
        results["Current"] = state.result()
    else:
        f = next(d["file"] for d in saved if d["name"] == name)
        cache = st.session_state.setdefault("_cmp_cache", {})
        mtime = next(d["modified"] for d in saved if d["name"] == name)
        if cache.get(f, (None,))[0] != mtime:
            cache[f] = (mtime, simulate(store.load(f)))
        results[name] = cache[f][1]

for name, r in results.items():
    if not r.ok:
        st.warning(f"⛔ **{name}** has blocking problems and is left out of the charts and table.")

names_ok = [n for n, r in results.items() if r.ok]
if not names_ok:
    st.stop()
baseline = st.selectbox("Baseline for Δ%", names_ok)
tbl = key_numbers_table(results, baseline)
def _num(v):
    return f"{v:.4g}" if abs(v) < 1e5 else f"{v:.3e}"


fmt = {c: (lambda v: f"{v:+.1f} %") if c.startswith("Δ%") else _num for c in tbl.columns}
st.dataframe(tbl.style.format(fmt, na_rep="—"), width="stretch")

VARS = {"VCC (cells/mL)": "vcc", "Working volume (L)": "volume_L", "Cum. fresh medium (L)": "cum_fresh_L",
        "Cum. harvest (L)": "cum_harvest_L", "Cum. bleed (L)": "cum_bleed_L",
        "Cum. wet biomass in bleed (g)": "cum_wb_bleed_g"}
mets = sorted({m for r in results.values() if r.ok for m in r.metabolite_names
               if r.table[m].notna().any()})
VARS.update({f"{m} (mM)": m for m in mets})
chosen = st.multiselect("Charts", list(VARS), default=["VCC (cells/mL)", *[f"{m} (mM)" for m in mets[:2]],
                                                       "Working volume (L)", "Cum. fresh medium (L)"])
data = long_series({n: results[n] for n in names_ok}, [VARS[c] for c in chosen])
cols = st.columns(2)
for j, label in enumerate(chosen):
    fig = go.Figure()
    for i, n in enumerate(names_ok):
        d = data[(data.scenario == n) & (data.variable == VARS[label])]
        fig.add_scatter(x=d.t_d, y=d.value, name=n, line=dict(color=SCEN_COLORS[i % len(SCEN_COLORS)], width=2))
    _layout(fig, label, label.split("(")[-1].rstrip(")"))
    if VARS[label] == "vcc":
        fig.update_yaxes(exponentformat="E")
    cols[j % 2].plotly_chart(fig, width="stretch")
