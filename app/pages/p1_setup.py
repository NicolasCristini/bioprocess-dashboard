import pandas as pd
import streamlit as st

from bioprocess.checks import validate
from bioprocess.models import Metabolite
from ui import state
from ui.widgets import none_if_nan, show_issues

sc = state.sc()
s = sc.setup
st.title("1 · Setup")
st.caption("Process settings and metabolites. All example values are placeholders.")

c1, c2 = st.columns([3, 2])
with c1:
    a, b = st.columns(2)
    name = a.text_input("Scenario name", sc.name, key=state.key("name"))
    if name.strip() and name != sc.name:
        sc.name = name.strip()
    vessel = a.number_input("Vessel volume (L)", 0.01, 10000.0, s.vessel_volume_L, 0.1, key=state.key("vessel"))
    v0 = a.number_input("Initial working volume V0 (L)", 0.001, 10000.0, s.initial_wv_L, 0.05, key=state.key("v0"))
    vmin = b.number_input("Minimum working volume V_min (L)", 0.0, 10000.0, s.v_min_L, 0.05, key=state.key("vmin"),
                          help="The run is stopped if the volume drops below this.")
    vmax = b.number_input("Maximum working volume V_max (L)", 0.001, 10000.0, s.v_max_L, 0.05, key=state.key("vmax"),
                          help="The run is stopped if the volume rises above this. Must not exceed the vessel.")
    seed = a.number_input("Seeding density (cells/mL)", 1.0, 1e9, s.seeding_density, 1e5, format="%.3e",
                          key=state.key("seed"))
    kwb = b.number_input("Wet biomass at 1E6 cells/mL (g/L)", 0.0, 1000.0, s.wet_biomass_g_per_L_at_1e6, 0.1,
                         key=state.key("kwb"), help="Placeholder assumption: wet biomass scales linearly with VCC.")
    res = b.selectbox("Time resolution", ["Hourly (24 steps/day)", "Daily (1 step/day)"],
                      index=0 if s.steps_per_day == 24 else 1, key=state.key("res"))
    sc.setup = s.model_copy(update=dict(vessel_volume_L=vessel, initial_wv_L=v0, v_min_L=vmin, v_max_L=vmax,
                                        seeding_density=seed, wet_biomass_g_per_L_at_1e6=kwb,
                                        steps_per_day=24 if res.startswith("Hourly") else 1))
with c2:
    st.markdown("**Volume window**")
    top = max(vessel, vmax, v0) or 1
    bar = lambda v: f"{max(0, min(100, v / top * 100)):.0f}%"  # noqa: E731
    st.markdown(
        f"""<div style="position:relative;height:150px;border:2px solid #888;border-top:none;border-radius:0 0 10px 10px;width:120px">
        <div style="position:absolute;bottom:{bar(vmin)};width:100%;border-top:2px dashed #d33"></div>
        <div style="position:absolute;bottom:{bar(vmax)};width:100%;border-top:2px dashed #d33"></div>
        <div style="position:absolute;bottom:0;height:{bar(v0)};width:100%;background:#3a7fd544"></div>
        <div style="position:absolute;left:128px;bottom:{bar(vmax)};font-size:12px;white-space:nowrap">V_max {vmax:g} L</div>
        <div style="position:absolute;left:128px;bottom:{bar(v0)};font-size:12px;white-space:nowrap">V0 {v0:g} L</div>
        <div style="position:absolute;left:128px;bottom:{bar(vmin)};font-size:12px;white-space:nowrap">V_min {vmin:g} L</div>
        <div style="position:absolute;left:128px;bottom:100%;font-size:12px;white-space:nowrap">vessel {vessel:g} L</div>
        </div>""", unsafe_allow_html=True)

st.subheader("Metabolites")
st.caption("q in 1E-11 mmol/cell/h. Limit: consumed → minimum to keep; produced → maximum tolerated. "
           "Leave q or the batch-medium value blank if unknown (the metabolite is then not calculated).")
df = pd.DataFrame([m.model_dump() for m in sc.metabolites])
edited = st.data_editor(
    df, key=state.key("mets"), num_rows="dynamic", width="stretch", hide_index=True,
    column_config={
        "name": st.column_config.TextColumn("Metabolite", required=True),
        "kind": st.column_config.SelectboxColumn("Consumed / produced", options=["consumed", "produced"], required=True),
        "q": st.column_config.NumberColumn("q (1E-11 mmol/cell/h)", format="%.3g"),
        "limit": st.column_config.NumberColumn("Limit (mM)", format="%.3g"),
        "c_batch": st.column_config.NumberColumn("Batch medium (mM)", format="%.3g"),
        "c_fedbatch": st.column_config.NumberColumn("Fed-batch feed (mM)", format="%.3g"),
        "c_perfusion": st.column_config.NumberColumn("Perfusion medium (mM)", format="%.3g"),
    })
mets = []
for row in edited.to_dict("records"):
    if not str(row.get("name") or "").strip():
        continue
    mets.append(Metabolite(name=str(row["name"]).strip(), kind=row.get("kind") or "consumed",
                           **{c: none_if_nan(row.get(c)) for c in ("q", "limit", "c_batch", "c_fedbatch", "c_perfusion")}))
sc.metabolites = mets

show_issues([i for i in validate(sc) if i.where == "setup"], empty="Setup is complete.")
