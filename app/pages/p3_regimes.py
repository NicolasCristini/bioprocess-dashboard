import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from bioprocess.checks import validate
from bioprocess.models import REGIME_DAYS
from ui import state, theme
from ui.widgets import show_issues

sc = state.sc()
v0 = sc.setup.initial_wv_L
used = sorted({p.regime for p in sc.phases if p.type == "Fed-batch"})
theme.top("Feed regimes", "Feed volume per phase day as % of the initial working volume, fed as a constant flow "
                          "over that day with the fed-batch feed composition from Setup.",
          [("Used by this scenario", ", ".join(used) if used else "none", "accent" if used else "")])

dcols = st.columns(len(sc.regimes))
for col, r in zip(dcols, sc.regimes):
    r.description = col.text_input(f"{r.name}", r.description, key=state.key(f"desc{r.name}"),
                                   placeholder="Description")

df = pd.DataFrame({r.name: [r.pct(d) or float("nan") for d in range(1, REGIME_DAYS + 1)] for r in sc.regimes},
                  index=pd.Index(range(1, REGIME_DAYS + 1), name="Phase day"), dtype=float)
left, right = st.columns([3, 2], gap="medium")
with left, st.container(border=True):
    theme.panel_title("Feed per phase day", "% of V0. Leave a cell empty for no feed that day.")
    edited = st.data_editor(df, key=state.key("regimes"), width="stretch", height=440,
                            column_config={r.name: st.column_config.NumberColumn(f"{r.name}", min_value=0.0, format="%.2f")
                                           for r in sc.regimes})
for r in sc.regimes:
    col = edited[r.name]
    r.pct_per_day = {int(d): float(v) for d, v in col.items() if pd.notna(v) and float(v) != 0.0}

with right, st.container(border=True):
    theme.panel_title("Totals over 30 days", f"At V0 = {v0:g} L.")
    theme.kpis([dict(label=r.name, value=f"{sum(r.pct_per_day.values()) / 100 * v0:.3f}", unit="L",
                     hint=f"{sum(r.pct_per_day.values()):g} % of V0", lead=r.name in used) for r in sc.regimes])

with st.container(border=True):
    theme.panel_title("Volume added per day", "Litres per phase day for each regime.")
    fig = go.Figure()
    for r in sc.regimes:
        fig.add_bar(x=list(range(1, REGIME_DAYS + 1)), y=[r.pct(d) / 100 * v0 for d in range(1, REGIME_DAYS + 1)],
                    name=r.name, marker_cornerradius=3)
    fig.update_layout(barmode="group", height=260, margin=dict(l=10, r=10, t=10, b=10), bargap=0.3,
                      xaxis_title="Phase day", yaxis_title="L/day",
                      legend=dict(orientation="h", y=1.08, yanchor="bottom", x=0))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

show_issues([i for i in validate(sc) if i.where == "regimes"])
