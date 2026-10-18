"""Visual layer on top of Streamlit's theme: CSS polish, the Plotly template, and small HTML components.

Everything reads app/ui/tokens.py. Components return HTML strings rendered with st.html, so they carry
no logic: pages pass in numbers computed by the model.
"""
from __future__ import annotations

import html as _html

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from . import tokens as t

CSS = f"""
<style>
:root {{
  --bp-canvas:{t.CANVAS}; --bp-surface:{t.SURFACE}; --bp-surface-2:{t.SURFACE_2}; --bp-sidebar:{t.SIDEBAR};
  --bp-line:{t.HAIRLINE}; --bp-line-strong:{t.HAIRLINE_STRONG};
  --bp-text:{t.TEXT}; --bp-muted:{t.TEXT_MUTED}; --bp-subtle:{t.TEXT_SUBTLE};
  --bp-accent:{t.ACCENT}; --bp-accent-hover:{t.ACCENT_HOVER}; --bp-on-accent:{t.ON_ACCENT}; --bp-accent-soft:{t.ACCENT_SOFT};
  --bp-danger:{t.DANGER}; --bp-warning:{t.WARNING}; --bp-info:{t.INFO};
  --bp-danger-soft:{t.DANGER_SOFT}; --bp-warning-soft:{t.WARNING_SOFT};
  --bp-card:{t.RADIUS_CARD}; --bp-input:{t.RADIUS_INPUT}; --bp-pill:{t.RADIUS_PILL};
  --bp-mono:"{t.FONT_MONO}", ui-monospace, SFMono-Regular, Menlo, monospace;
}}

/* ---------- page frame */
[data-testid="stAppViewContainer"] {{ background: var(--bp-canvas); }}
header[data-testid="stHeader"] {{ background: transparent; height: 0; }}
[data-testid="stDecoration"] {{ display: none; }}
.block-container {{ padding-top: 1.25rem; padding-bottom: 4rem; max-width: 1400px; }}
h1, h2, h3, h4 {{ letter-spacing: -0.02em; }}
h1 {{ font-size: 1.6rem !important; }}
h2 {{ font-size: 1.2rem !important; }}
h3 {{ font-size: 1.02rem !important; }}
p, li {{ color: var(--bp-text); }}
[data-testid="stCaptionContainer"], .stCaption {{ color: var(--bp-muted) !important; }}
hr {{ border-color: var(--bp-line) !important; margin: 1.25rem 0 !important; }}

/* ---------- sidebar */
[data-testid="stSidebarHeader"] {{ padding-bottom: .5rem; }}
[data-testid="stLogo"] {{ height: 2.2rem; max-width: 100%; }}
[data-testid="stSidebar"] {{ border-right: 1px solid var(--bp-line); }}
[data-testid="stSidebarNav"] a {{ border-radius: var(--bp-pill); margin: 2px 6px; padding: 7px 14px; }}
[data-testid="stSidebarNav"] a span {{ font-size: 16.5px !important; font-weight: 500; color: var(--bp-text) !important; }}
[data-testid="stSidebarNav"] a [data-testid="stIconMaterial"] {{ font-size: 20px !important; }}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p, [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{ font-size: 15px !important; }}
[data-testid="stSidebar"] .bp-panel-title {{ font-size: 17px; }}
[data-testid="stSidebar"] .bp-issue {{ font-size: 15.5px; }}
[data-testid="stSidebar"] .bp-chip {{ font-size: 14px; }}
[data-testid="stSidebarNav"] a[aria-current="page"] {{ background: var(--bp-accent-soft); }}
[data-testid="stSidebarNav"] a[aria-current="page"] span {{ color: var(--bp-accent) !important; }}
[data-testid="stNavSectionHeader"], [data-testid="stNavSectionHeader"] * {{ color: var(--bp-muted) !important; font-size: 13px !important; letter-spacing: .08em; text-transform: uppercase; font-weight: 600; }}

/* ---------- cards: bordered containers become surfaces */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {{
  background: var(--bp-surface); border-color: var(--bp-line) !important; border-radius: var(--bp-card) !important;
}}

/* ---------- buttons: pills, accent primary, quiet secondary, tactile press */
.stButton button, .stDownloadButton button, [data-testid="stPopover"] button, .stFormSubmitButton button {{
  border-radius: var(--bp-pill) !important; font-weight: 500; padding: 0.35rem 1.05rem;
  transition: background-color .15s ease, border-color .15s ease, transform .08s ease;
}}
.stButton button:active, .stDownloadButton button:active {{ transform: scale(0.98); }}
.stButton button[kind="primary"], .stDownloadButton button[kind="primary"] {{
  background: var(--bp-accent); border-color: var(--bp-accent); color: var(--bp-on-accent);
}}
.stButton button[kind="primary"]:hover {{ background: var(--bp-accent-hover); border-color: var(--bp-accent-hover); }}
.stButton button[kind="secondary"], .stDownloadButton button[kind="secondary"], [data-testid="stPopover"] button {{
  background: var(--bp-surface-2); border-color: var(--bp-line-strong);
}}
.stButton button[kind="secondary"]:hover, .stDownloadButton button:hover {{ border-color: var(--bp-accent); color: var(--bp-text); }}

/* ---------- inputs */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] {{ border-radius: var(--bp-input) !important; }}
[data-testid="stWidgetLabel"] p {{ color: var(--bp-muted) !important; font-size: 13.5px !important; }}
input[type="number"] {{ font-family: var(--bp-mono); }}

/* ---------- tabs: segmented pill control */
[data-testid="stTabs"] [role="tablist"] {{ gap: 4px; background: var(--bp-surface); border: 1px solid var(--bp-line) !important;
  border-radius: var(--bp-pill); padding: 4px; width: fit-content; box-shadow: none !important; margin-bottom: 14px; }}
[data-testid="stTabs"] [role="tablist"]::before, [data-testid="stTabs"] [role="tablist"]::after {{ display: none !important; }}
[data-testid="stTab"] {{ border-radius: var(--bp-pill) !important; padding: 6px 14px !important; height: auto !important;
  border: none !important; box-shadow: none !important; }}
[data-testid="stTab"]::after, [data-testid="stTab"]::before {{ display: none !important; }}
[data-testid="stTab"] p {{ color: var(--bp-muted); font-size: 13px; }}
[data-testid="stTab"][aria-selected="true"] {{ background: var(--bp-surface-2); box-shadow: inset 0 0 0 1px var(--bp-line-strong), 0 1px 2px rgba(21,24,28,.08) !important; }}
[data-testid="stTab"][aria-selected="true"] p {{ color: var(--bp-text); }}
[data-testid="stTab"]:hover p {{ color: var(--bp-text); }}

/* ---------- expanders, alerts, tables, metrics */
[data-testid="stExpander"] details {{ border-radius: var(--bp-card) !important; border-color: var(--bp-line) !important; background: var(--bp-surface); }}
[data-testid="stAlert"] {{ border-radius: var(--bp-input); }}
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {{ border-radius: var(--bp-input); overflow: hidden; }}
[data-testid="stMetricValue"] {{ font-family: var(--bp-mono); letter-spacing: -0.02em; }}
[data-testid="stMetricLabel"] p {{ color: var(--bp-muted) !important; }}
[data-testid="stFileUploaderDropzone"] {{ border-radius: var(--bp-card); background: var(--bp-surface); }}
[data-testid="stPlotlyChart"] {{ background: #FFFFFF; border: 1px solid var(--bp-line); border-radius: var(--bp-card);
  overflow: hidden; box-sizing: border-box; }}
[data-testid="stPlotlyChart"] .modebar-container {{ right: 8px !important; top: 4px !important; }}
.bp-dl-row {{ margin-top: -4px; }}

/* ---------- custom components */
.bp-top {{ display:flex; align-items:flex-end; justify-content:space-between; gap:16px; flex-wrap:wrap;
  padding: 6px 0 18px; border-bottom: 1px solid var(--bp-line); margin-bottom: 20px; }}
.bp-top h1 {{ margin:0; padding:0; font-size:1.6rem; font-weight:600; letter-spacing:-0.025em; color:var(--bp-text); }}
.bp-top .bp-sub {{ color:var(--bp-muted); font-size:14.5px; margin-top:4px; max-width:70ch; }}
.bp-chips {{ display:flex; gap:6px; flex-wrap:wrap; }}
.bp-chip {{ display:inline-flex; align-items:center; gap:6px; border:1px solid var(--bp-line-strong); border-radius:var(--bp-pill);
  padding:3px 10px; font-size:13px; color:var(--bp-muted); background:var(--bp-surface); white-space:nowrap; }}
.bp-chip b {{ color:var(--bp-text); font-weight:500; font-family:var(--bp-mono); }}
.bp-chip.accent {{ border-color: var(--bp-accent); background: var(--bp-surface-2); color: var(--bp-accent); font-weight: 500; }}
.bp-chip.warning {{ border-color: var(--bp-warning); background: var(--bp-surface-2); color: var(--bp-warning); font-weight: 500; }}
.bp-chip.danger {{ border-color: var(--bp-danger); background: var(--bp-surface-2); color: var(--bp-danger); font-weight: 500; }}

.bp-kpis {{ display:grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap:10px; margin: 4px 0 18px; }}
.bp-kpi {{ background:var(--bp-surface); border:1px solid var(--bp-line); border-radius:var(--bp-card); padding:14px 16px; }}
.bp-kpi.lead {{ border-color: var(--bp-accent); background: var(--bp-surface-2); box-shadow: inset 3px 0 0 var(--bp-accent); }}
.bp-kpi .l {{ color:var(--bp-muted); font-size:13px; }}
.bp-kpi .v {{ font-family:var(--bp-mono); font-size:1.55rem; font-weight:500; letter-spacing:-0.03em; color:var(--bp-text); margin-top:6px; line-height:1.1; }}
.bp-kpi .v small {{ font-size:.8rem; color:var(--bp-muted); margin-left:4px; font-weight:400; letter-spacing:0; }}
.bp-kpi .h {{ color:var(--bp-subtle); font-size:11.5px; margin-top:6px; }}

.bp-issues {{ display:flex; flex-direction:column; gap:6px; margin: 4px 0 8px; }}
.bp-issue {{ display:grid; grid-template-columns: 84px 1fr; gap:12px; align-items:start; padding:9px 12px;
  border:1px solid var(--bp-line); border-radius:var(--bp-input); background:var(--bp-surface); font-size:14px; color:var(--bp-text); }}
.bp-issue .lv {{ font-size:11px; font-weight:600; letter-spacing:.04em; text-transform:uppercase; padding-top:1px; }}
.bp-issue.block {{ border-color: var(--bp-danger); }} .bp-issue.block .lv {{ color:var(--bp-danger); }}
.bp-issue.warning .lv {{ color:var(--bp-warning); }}
.bp-issue.info .lv {{ color:var(--bp-info); }}
.bp-issue .ph {{ color:var(--bp-muted); font-family:var(--bp-mono); font-size:12px; margin-right:6px; }}
.bp-ok {{ padding:9px 12px; border-radius:var(--bp-input); background:var(--bp-surface-2); border:1px solid var(--bp-accent); color:var(--bp-accent); font-size:13px; }}

.bp-timeline {{ display:flex; height:30px; border-radius:var(--bp-pill); overflow:hidden; border:1px solid var(--bp-line); margin:4px 0 6px; }}
.bp-timeline div {{ display:flex; align-items:center; padding:0 12px; font-size:12px; color:{t.TEXT}; font-weight:500; white-space:nowrap; overflow:hidden; }}
.bp-timeline div + div {{ border-left: 2px solid var(--bp-canvas); }}
.bp-axis {{ display:flex; justify-content:space-between; color:var(--bp-subtle); font-size:11.5px; font-family:var(--bp-mono); }}

.bp-state {{ display:flex; flex-wrap:wrap; gap:6px 8px; margin: 2px 0 12px; }}
.bp-steps {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap:10px; margin: 8px 0 20px; }}
.bp-step {{ background:var(--bp-surface); border:1px solid var(--bp-line); border-radius:var(--bp-card); padding:14px 16px; }}
.bp-step .n {{ font-family:var(--bp-mono); color:var(--bp-accent); font-size:12px; }}
.bp-step .t {{ font-weight:600; margin:6px 0 4px; color:var(--bp-text); }}
.bp-step .d {{ color:var(--bp-muted); font-size:12.5px; line-height:1.45; }}
.bp-panel-title {{ font-weight:600; font-size:14px; margin: 0 0 2px; color: var(--bp-text); }}
.bp-panel-sub {{ color:var(--bp-muted); font-size:12.5px; margin-bottom:10px; }}
.bp-badge {{ display:inline-block; border-radius:var(--bp-pill); padding:2px 10px; font-size:12px; font-weight:500; color:{t.TEXT}; }}
.bp-brand {{ display:flex; align-items:center; gap:10px; padding: 2px 4px 10px; }}
.bp-brand .mk {{ width:26px; height:26px; border-radius:8px; background: var(--bp-accent); color: var(--bp-on-accent);
  display:grid; place-items:center; font-weight:700; font-size:13px; font-family:var(--bp-mono); }}
.bp-brand .nm {{ font-weight:600; letter-spacing:-0.01em; color:var(--bp-text); line-height:1.15; }}
.bp-brand .nm small {{ display:block; color:var(--bp-subtle); font-weight:400; font-size:11.5px; }}

@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; }} }}
</style>
"""


# simple geometric mark (rounded square + monogram); text falls back to the system sans inside an <img>
_MARK = (f'<rect x="0" y="4" width="32" height="32" rx="9" fill="{t.ACCENT}"/>'
         f'<text x="16" y="25.5" text-anchor="middle" font-family="ui-monospace,Menlo,monospace" font-size="14" '
         f'font-weight="700" fill="{t.ON_ACCENT}">Bp</text>')
LOGO_SVG = (f'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="40" viewBox="0 0 200 40">{_MARK}'
            f'<text x="42" y="26" font-family="system-ui,-apple-system,Segoe UI,sans-serif" font-size="16" '
            f'font-weight="600" fill="{t.TEXT}" letter-spacing="-0.3">Phase Planner</text></svg>')
ICON_SVG = f'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 -2 32 40">{_MARK}</svg>'


def inject() -> None:
    st.html(CSS)
    st.logo(LOGO_SVG, icon_image=ICON_SVG, size="large")


# ---------------------------------------------------------------- Plotly
def _register_template() -> None:
    axis = dict(gridcolor=t.GRID, zerolinecolor=t.GRID, linecolor=t.HAIRLINE_STRONG, automargin=True,
                tickfont=dict(color=t.TEXT_SUBTLE, family=t.FONT_MONO, size=11),
                title=dict(font=dict(color=t.TEXT_MUTED, size=12)))
    pio.templates["bioprocess"] = go.layout.Template(layout=go.Layout(
        font=dict(family=f"{t.FONT}, system-ui, sans-serif", color=t.TEXT_MUTED, size=12),
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        colorway=t.CHART, xaxis=axis, yaxis=axis,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=t.TEXT_MUTED, size=11.5)),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=t.HAIRLINE_STRONG,
                        font=dict(family=t.FONT_MONO, color=t.TEXT, size=12)),
        title=dict(font=dict(color=t.TEXT, size=14, family=t.FONT)),
    ))
    pio.templates.default = "bioprocess"


_register_template()


# ---------------------------------------------------------------- HTML components
def white(fig):
    """Streamlit's front end paints paper_bgcolor with the page colour unless the figure sets it explicitly."""
    fig.update_layout(paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF")
    return fig


def esc(s) -> str:
    return _html.escape(str(s))


def top(title: str, subtitle: str = "", chips: list[tuple[str, str, str]] | None = None) -> None:
    """Page header. chips: (label, value, tone) with tone in '', 'accent', 'warning', 'danger'."""
    chip_html = "".join(
        f'<span class="bp-chip {tone}">{esc(label)}{f" <b>{esc(value)}</b>" if value else ""}</span>'
        for label, value, tone in (chips or []))
    st.html(f'<div class="bp-top"><div><h1>{esc(title)}</h1>'
            + (f'<div class="bp-sub">{esc(subtitle)}</div>' if subtitle else "")
            + f'</div><div class="bp-chips">{chip_html}</div></div>')


def kpis(items: list[dict]) -> None:
    """items: dict(label, value, unit='', hint='', lead=False)."""
    cells = "".join(
        f'<div class="bp-kpi{" lead" if it.get("lead") else ""}"><div class="l">{esc(it["label"])}</div>'
        f'<div class="v">{esc(it["value"])}<small>{esc(it.get("unit", ""))}</small></div>'
        + (f'<div class="h">{esc(it["hint"])}</div>' if it.get("hint") else "") + "</div>"
        for it in items)
    st.html(f'<div class="bp-kpis">{cells}</div>')


LEVEL_LABEL = {"block": "Blocking", "warning": "Check", "info": "Note"}


def issues(items, ok_text: str | None = None) -> None:
    if not items:
        if ok_text:
            st.html(f'<div class="bp-ok">{esc(ok_text)}</div>')
        return
    rows = "".join(
        f'<div class="bp-issue {i.level}"><div class="lv">{LEVEL_LABEL[i.level]}</div><div>'
        + (f'<span class="ph">Phase {i.phase}</span>' if i.phase else "") + f'{esc(i.message)}</div></div>'
        for i in items)
    st.html(f'<div class="bp-issues">{rows}</div>')


def chips(items: list[tuple[str, str, str]]) -> None:
    st.html('<div class="bp-state">' + "".join(
        f'<span class="bp-chip {tone}">{esc(label)}{f" <b>{esc(value)}</b>" if value else ""}</span>'
        for label, value, tone in items) + "</div>")


def panel_title(title: str, sub: str = "") -> None:
    st.html(f'<div class="bp-panel-title">{esc(title)}</div>' + (f'<div class="bp-panel-sub">{esc(sub)}</div>' if sub else ""))


def badge(text: str, color: str) -> str:
    return f'<span class="bp-badge" style="background:{color}">{esc(text)}</span>'
