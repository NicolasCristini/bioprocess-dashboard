import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from bioprocess.checks import validate
from bioprocess.models import REGIME_DAYS
from ui import state
from ui.widgets import show_issues

sc = state.sc()
v0 = sc.setup.initial_wv_L
st.title("3 · Feed regimes")
st.caption("Feed volume per phase day as **% of the initial working volume**, for fed-batch phases. "
           "It is fed as a constant flow over that day, with the 'Fed-batch feed' composition from Setup.")

for r in sc.regimes:
    r.description = st.text_input(f"{r.name} — description", r.description, key=state.key(f"desc{r.name}"))

df = pd.DataFrame({r.name: [r.pct(d) or None for d in range(1, REGIME_DAYS + 1)] for r in sc.regimes},
                  index=pd.Index(range(1, REGIME_DAYS + 1), name="Phase day"))
left, right = st.columns([3, 2])
with left:
    edited = st.data_editor(df, key=state.key("regimes"), width="stretch", height=420,
                            column_config={r.name: st.column_config.NumberColumn(f"{r.name} (% of V0)", min_value=0.0,
                                                                                format="%.2f")
                                           for r in sc.regimes})
for r in sc.regimes:
    col = edited[r.name]
    r.pct_per_day = {int(d): float(v) for d, v in col.items() if pd.notna(v) and float(v) != 0.0}

with right:
    fig = go.Figure()
    for r in sc.regimes:
        fig.add_bar(x=list(range(1, REGIME_DAYS + 1)), y=[r.pct(d) / 100 * v0 for d in range(1, REGIME_DAYS + 1)],
                    name=r.name)
    fig.update_layout(barmode="group", height=300, margin=dict(l=10, r=10, t=30, b=10),
                      title=f"Volume added per day at V0 = {v0:g} L", xaxis_title="Phase day", yaxis_title="L/day",
                      legend=dict(orientation="h"))
    st.plotly_chart(fig, width="stretch")
    tot = pd.DataFrame({"Regime": [r.name for r in sc.regimes],
                        "Total over 30 days (% of V0)": [sum(r.pct_per_day.values()) for r in sc.regimes],
                        "Total (L)": [sum(r.pct_per_day.values()) / 100 * v0 for r in sc.regimes]})
    st.dataframe(tot, hide_index=True, width="stretch")
    used = sorted({p.regime for p in sc.phases if p.type == "Fed-batch"})
    st.caption("Used by this scenario: " + (", ".join(used) if used else "none"))

show_issues([i for i in validate(sc) if i.where == "regimes"])
