"""Plotly figures built from simulation results. No model arithmetic here: columns only."""
from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from bioprocess.simulate import SimResult

from . import theme  # noqa: F401  (registers the "bioprocess" Plotly template)
from .tokens import ACCENT, HAIRLINE, SURFACE_2, TEXT, CHART, DANGER, HAIRLINE_STRONG, INFO, PHASE as PHASE_COLOR, TEXT_MUTED, TEXT_SUBTLE, WARNING

MET_COLORS = [CHART[2], CHART[3], CHART[4], CHART[5], CHART[1], CHART[0], CHART[6]]   # glucose blue, lactate rose, ...
SCEN_COLORS = CHART


def _layout(fig: go.Figure, title: str, ytitle: str, height: int = 320) -> go.Figure:
    fig.update_layout(title=dict(text=title, x=0, y=0.98, yanchor="top", font=dict(size=15)), height=height,
                      hovermode="x unified", margin=dict(l=10, r=10, t=64, b=10),
                      legend=dict(orientation="h", x=0, y=1.0, yanchor="bottom", font=dict(size=11)),
                      xaxis_title="Process time (days)", yaxis_title=ytitle)
    return fig


def phase_bands(fig: go.Figure, r: SimResult, row=None, col=None) -> None:
    for p in r.plans:
        if p.type == "Batch":
            continue
        fig.add_vrect(x0=p.start_day, x1=p.end_day, fillcolor=PHASE_COLOR[p.type], opacity=0.10, line_width=0, layer="below",
                      row=row, col=col)


def marker(fig: go.Figure, t_d: float | None) -> None:
    if t_d is not None:
        fig.add_vline(x=t_d, line_dash="dot", line_color=TEXT_MUTED, line_width=1)


def vcc(r: SimResult, log: bool = False, t_d=None) -> go.Figure:
    tb = r.table
    fig = go.Figure(go.Scatter(x=tb.t_d, y=tb.vcc, name="VCC", line=dict(color=ACCENT, width=2.4),
                               hovertemplate="%{y:.3e} cells/mL"))
    phase_bands(fig, r)
    marker(fig, t_d)
    _layout(fig, "Viable cell density", "cells/mL")
    fig.update_yaxes(type="log" if log else "linear", exponentformat="E")
    return fig


def metabolites(r: SimResult, t_d=None) -> go.Figure:
    tb, fig = r.table, go.Figure()
    for j, m in enumerate(r.scenario.metabolites):
        if m.name not in tb or tb[m.name].isna().all():
            continue
        c = MET_COLORS[j % len(MET_COLORS)]
        fig.add_scatter(x=tb.t_d, y=tb[m.name], name=m.name, line=dict(color=c, width=2),
                        hovertemplate="%{y:.2f} mM")
        if m.limit is not None:
            fig.add_hline(y=m.limit, line_dash="dash", line_color=c, opacity=0.6,
                          annotation_text=f"{m.name} {'min' if m.sign < 0 else 'max'} {m.limit:g}",
                          annotation_font_size=10)
    phase_bands(fig, r)
    marker(fig, t_d)
    return _layout(fig, "Metabolites (dashed = limits)", "mM")


def volume(r: SimResult, t_d=None) -> go.Figure:
    tb, s = r.table, r.scenario.setup
    fig = go.Figure(go.Scatter(x=tb.t_d, y=tb.volume_L, name="Working volume", line=dict(color=ACCENT, width=2.4),
                               hovertemplate="%{y:.3f} L"))
    fig.add_hrect(y0=s.v_min_L, y1=s.v_max_L, fillcolor=ACCENT, opacity=0.06, line_width=0)
    lines = [(s.v_min_L, "V_min", DANGER), (s.v_max_L, "V_max", DANGER)]
    if abs(s.vessel_volume_L - s.v_max_L) > 1e-9:
        lines.append((s.vessel_volume_L, "Vessel", TEXT_SUBTLE))
    else:
        lines[1] = (s.v_max_L, "V_max = vessel", DANGER)
    for y, name, colr in lines:
        fig.add_hline(y=y, line_dash="dash", line_color=colr, annotation_text=f"{name} {y:g} L", annotation_font_size=10)
    phase_bands(fig, r)
    marker(fig, t_d)
    _layout(fig, "Working volume vs window", "L")
    fig.update_yaxes(range=[0, max(s.vessel_volume_L, tb.volume_L.max()) * 1.08])
    return fig


def cumulative(r: SimResult, t_d=None) -> go.Figure:
    tb, fig = r.table, go.Figure()
    for colname, name, c in (("cum_fresh_L", "Fresh medium", ACCENT), ("cum_harvest_L", "Harvest", INFO),
                             ("cum_bleed_L", "Bleed", CHART[3]), ("cum_fb_L", "Fed-batch feed", WARNING)):
        fig.add_scatter(x=tb.t_d, y=tb[colname], name=name, line=dict(color=c, width=2), hovertemplate="%{y:.3f} L")
    phase_bands(fig, r)
    marker(fig, t_d)
    return _layout(fig, "Cumulative medium, harvest and bleed", "L")


def biomass(r: SimResult, t_d=None) -> go.Figure:
    tb = r.table
    fig = go.Figure()
    fig.add_scatter(x=tb.t_d, y=tb.cum_wb_bleed_g, name="Cum. wet biomass in bleed", line=dict(color=ACCENT, width=2.4),
                    hovertemplate="%{y:.2f} g")
    fig.add_scatter(x=tb.t_d, y=tb.wb_reactor_g, name="Wet biomass in reactor", line=dict(color=TEXT_MUTED, dash="dot"),
                    hovertemplate="%{y:.2f} g")
    phase_bands(fig, r)
    marker(fig, t_d)
    return _layout(fig, "Wet biomass", "g")


def fedbatch_bars(fb_df) -> go.Figure:
    fig = go.Figure(go.Bar(x=fb_df["Day"], y=fb_df["Volume added (L)"], marker_color=PHASE_COLOR["Fed-batch"], marker_cornerradius=6,
                           hovertemplate="day %{x}: %{y:.3f} L"))
    _layout(fig, "Fed-batch volume added per day", "L/day", height=260)
    fig.update_xaxes(title="Process day", dtick=1)
    return fig


def playback(r: SimResult, max_frames: int = 120) -> go.Figure:
    """2x2 animated overview (client-side Plotly frames: smooth, no reruns)."""
    tb = r.table
    n = len(tb) - 1
    stride = max(1, -(-n // max_frames))
    idx = list(range(0, n + 1, stride))
    if idx[-1] != n:
        idx.append(n)
    sub = tb.iloc[idx]
    mets = [m for m in r.scenario.metabolites if m.name in tb and tb[m.name].notna().any()]
    fig = make_subplots(rows=2, cols=2, subplot_titles=("VCC (cells/mL)", "Metabolites (mM)", "Working volume (L)",
                                                        "Fresh medium (L) · biomass bled (g)"),
                        specs=[[{}, {}], [{}, {"secondary_y": True}]], vertical_spacing=0.14)

    def traces(k):
        d = sub.iloc[: k + 1]
        out = [go.Scatter(x=d.t_d, y=d.vcc, name="VCC", line=dict(color=ACCENT))]
        out += [go.Scatter(x=d.t_d, y=d[m.name], name=m.name, line=dict(color=MET_COLORS[j % 7]))
                for j, m in enumerate(mets)]
        out += [go.Scatter(x=d.t_d, y=d.volume_L, name="Volume", line=dict(color=INFO)),
                go.Scatter(x=d.t_d, y=d.cum_fresh_L, name="Fresh medium (L)", line=dict(color=WARNING)),
                go.Scatter(x=d.t_d, y=d.cum_wb_bleed_g, name="Wet biomass bled (g)", line=dict(color=ACCENT, dash="dot"))]
        return out

    pos = [(1, 1)] + [(1, 2)] * len(mets) + [(2, 1), (2, 2), (2, 2)]
    for tr, (rr, cc), sec in zip(traces(0), pos, [False] * (len(pos) - 1) + [True]):
        fig.add_trace(tr, row=rr, col=cc, **({"secondary_y": sec} if (rr, cc) == (2, 2) else {}))
    t_end = float(tb.t_d.iloc[-1])
    rng = lambda c: [0, float(tb[c].max()) * 1.08 or 1]  # noqa: E731
    fig.update_xaxes(range=[0, t_end])
    fig.update_yaxes(range=rng("vcc"), row=1, col=1, exponentformat="E")
    met_max = max([float(tb[m.name].max()) for m in mets] or [1])
    fig.update_yaxes(range=[0, met_max * 1.08], row=1, col=2)
    fig.update_yaxes(range=[0, max(r.scenario.setup.v_max_L, float(tb.volume_L.max())) * 1.08], row=2, col=1)
    fig.update_yaxes(range=rng("cum_fresh_L"), row=2, col=2, secondary_y=False)
    fig.update_yaxes(range=rng("cum_wb_bleed_g"), row=2, col=2, secondary_y=True)
    def label(t):
        return f"day {int(t + 1e-9)} · h {round((t % 1) * 24) % 24:02d}"

    fig.frames = [go.Frame(data=traces(k), name=str(k)) for k in range(len(sub))]
    anim = dict(mode="immediate", frame=dict(duration=60, redraw=False), transition=dict(duration=0))
    steps = [dict(method="animate", label=label(sub.t_d.iloc[k]), args=[[str(k)], anim]) for k in range(len(sub))]
    fig.update_layout(
        height=660, margin=dict(l=10, r=10, t=60, b=110), showlegend=True,
        legend=dict(orientation="h", x=0, y=1.08, yanchor="bottom"),
        updatemenus=[dict(type="buttons", direction="left", x=0, y=-0.1, xanchor="left", yanchor="top",
                          pad=dict(t=0, r=6), bgcolor=SURFACE_2, bordercolor=HAIRLINE_STRONG, borderwidth=1,
                          font=dict(color=TEXT, size=12), showactive=False, buttons=[
                              dict(label="Play", method="animate", args=[None, {**anim, "fromcurrent": True}]),
                              dict(label="Pause", method="animate",
                                   args=[[None], dict(mode="immediate", frame=dict(duration=0, redraw=False))]),
                          ])],
        sliders=[dict(active=0, steps=steps, x=0.16, len=0.84, y=-0.1, yanchor="top", pad=dict(t=0, b=0),
                      bgcolor=SURFACE_2, activebgcolor=ACCENT, bordercolor=HAIRLINE, borderwidth=1, tickcolor=HAIRLINE,
                      currentvalue=dict(prefix="t = ", font=dict(size=13, color=TEXT, family="Geist Mono")), ticklen=0, minorticklen=0,
                      font=dict(size=1, color="rgba(0,0,0,0)"))],
    )
    return fig
