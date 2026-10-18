import pandas as pd
import streamlit as st

from bioprocess.checks import validate
from bioprocess.models import Metabolite
from ui import state, theme
from ui.tokens import ACCENT, DANGER, HAIRLINE_STRONG, TEXT_MUTED, TEXT_SUBTLE
from ui.widgets import none_if_nan, show_issues

sc = state.sc()
s = sc.setup
theme.top("Setup", "Process settings and metabolites. Example values are placeholders.")

left, right = st.columns([3, 2], gap="medium")
with left, st.container(border=True):
    theme.panel_title("Vessel and volumes")
    name = st.text_input("Scenario name", sc.name, key=state.key("name"))
    if name.strip() and name != sc.name:
        sc.name = name.strip()
    a, b = st.columns(2)
    vessel = a.number_input("Vessel volume (L)", 0.01, 10000.0, s.vessel_volume_L, 0.1, key=state.key("vessel"))
    v0 = b.number_input("Initial working volume V0 (L)", 0.001, 10000.0, s.initial_wv_L, 0.05, key=state.key("v0"))
    vmin = a.number_input("Minimum working volume V_min (L)", 0.0, 10000.0, s.v_min_L, 0.05, key=state.key("vmin"),
                          help="The run is stopped if the volume drops below this.")
    vmax = b.number_input("Maximum working volume V_max (L)", 0.001, 10000.0, s.v_max_L, 0.05, key=state.key("vmax"),
                          help="The run is stopped if the volume rises above this. Must not exceed the vessel.")
    seed = a.number_input("Seeding density (cells/mL)", 1.0, 1e9, s.seeding_density, 1e5, format="%.3e",
                          key=state.key("seed"))
    kwb = b.number_input("Wet biomass at 1E6 cells/mL (g/L)", 0.0, 1000.0, s.wet_biomass_g_per_L_at_1e6, 0.1,
                         key=state.key("kwb"), help="Placeholder assumption: wet biomass scales linearly with VCC.")
    res = a.segmented_control("Time resolution", ["Hourly", "Daily"], default="Hourly" if s.steps_per_day == 24 else "Daily",
                              key=state.key("res")) or "Hourly"
    sc.setup = s.model_copy(update=dict(vessel_volume_L=vessel, initial_wv_L=v0, v_min_L=vmin, v_max_L=vmax,
                                        seeding_density=seed, wet_biomass_g_per_L_at_1e6=kwb,
                                        steps_per_day=24 if res == "Hourly" else 1))

with right, st.container(border=True):
    theme.panel_title("Volume window", "Where the working volume may move during the run.")
    top = max(vessel, vmax, v0) or 1
    pct = lambda v: f"{max(0, min(100, v / top * 100)):.1f}%"  # noqa: E731
    line = lambda v, label, color: (  # noqa: E731
        f'<div style="position:absolute;left:0;right:0;bottom:{pct(v)};border-top:1.5px dashed {color}"></div>'
        f'<div style="position:absolute;left:172px;bottom:calc({pct(v)} - 8px);font:12px var(--bp-mono);color:{color};white-space:nowrap">{label} {v:g} L</div>')
    st.html(
        f'<div style="position:relative;height:210px;margin:10px 0 6px 6px">'
        f'<div style="position:absolute;left:0;bottom:0;width:150px;height:100%;border:1.5px solid {HAIRLINE_STRONG};'
        f'border-top:none;border-radius:0 0 18px 18px;overflow:hidden">'
        f'<div style="position:absolute;left:0;right:0;bottom:0;height:{pct(v0)};background:linear-gradient(180deg,{ACCENT}55,{ACCENT}22)"></div>'
        f'{line(vmax, "", DANGER)}{line(vmin, "", DANGER)}</div>'
        f'{line(vmax, "V_max = vessel" if abs(vmax - vessel) < 1e-9 else "V_max", DANGER)}{line(v0, "V0", ACCENT)}'
        f'{line(vmin, "V_min", DANGER)}'
        + ("" if abs(vmax - vessel) < 1e-9 else
           f'<div style="position:absolute;left:172px;top:-8px;font:12px var(--bp-mono);color:{TEXT_SUBTLE}">vessel {vessel:g} L</div>')
        + f'</div><div style="color:{TEXT_MUTED};font-size:12px">Vessel outline to scale; the fill is V0.</div>')

with st.container(border=True):
    theme.panel_title("Metabolites", "q in 1E-11 mmol/cell/h. Limit: minimum for consumed, maximum for produced. "
                                     "Leave q or the batch medium blank if unknown.")
    num = ["q", "limit", "c_batch", "c_fedbatch", "c_perfusion"]
    df = pd.DataFrame([m.model_dump() for m in sc.metabolites], columns=["name", "kind", *num])
    df[num] = df[num].astype(float)          # blanks show as empty cells, not "None"
    edited = st.data_editor(
        df, key=state.key("mets"), num_rows="dynamic", width="stretch", hide_index=True,
        column_config={
            "name": st.column_config.TextColumn("Metabolite", required=True),
            "kind": st.column_config.SelectboxColumn("Consumed / produced", options=["consumed", "produced"], required=True),
            "q": st.column_config.NumberColumn("q", format="%.3g"),
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
