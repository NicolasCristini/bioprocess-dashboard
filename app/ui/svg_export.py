"""Vector (SVG) export of the app's Plotly figures, written in Python because image engines (kaleido) do not run
in the browser. Covers what the app draws: lines, bars, phase bands, limit/marker lines, log axes, legends.
"""
from __future__ import annotations

import math
from html import escape

import numpy as np

from . import tokens as t

FONT = "Geist, 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'Geist Mono', Menlo, Consolas, monospace"
DASH = {"dash": "7 5", "dot": "2 4", "dashdot": "7 4 2 4", "longdash": "12 6"}


# ---------------------------------------------------------------- helpers
def _nice_ticks(lo: float, hi: float, n: int = 6) -> list[float]:
    if not math.isfinite(lo) or not math.isfinite(hi):
        return []
    if hi == lo:
        hi = lo + 1
    raw = (hi - lo) / max(n - 1, 1)
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    start = math.ceil(lo / step - 1e-9) * step
    out, v = [], start
    while v <= hi + 1e-9 * step:
        out.append(round(v, 12))
        v += step
    return out


def _fmt(v: float, big: bool) -> str:
    if big:
        if v == 0:
            return "0"
        m, e = f"{v:.1e}".split("e")
        return f"{m}E{int(e)}"
    return f"{v:g}"


def _color(c, default=t.TEXT_MUTED) -> str:
    return c if isinstance(c, str) and c else default


def _series(fig):
    """Yield (trace, x array, y array) for scatter and bar traces."""
    for tr in fig.data:
        if tr.type not in ("scatter", "bar") or tr.x is None or tr.y is None:
            continue
        yield tr, np.asarray(tr.x, dtype=float), np.asarray(tr.y, dtype=float)


def legend_items(fig) -> list[dict]:
    """Colour key of a figure: named traces plus named shapes (phase bands, limits, volume window)."""
    items, seen = [], set()
    for tr, _, _ in _series(fig):
        if tr.showlegend is False or not tr.name or tr.name in seen:
            continue
        seen.add(tr.name)
        if tr.type == "bar":
            items.append(dict(name=tr.name, kind="box", color=_color(tr.marker.color)))
        else:
            items.append(dict(name=tr.name, kind="line", color=_color(tr.line.color), dash=tr.line.dash))
    for sh in fig.layout.shapes:
        if not sh.name or sh.name in seen:
            continue
        seen.add(sh.name)
        if sh.type == "rect":
            items.append(dict(name=sh.name, kind="band", color=_color(sh.fillcolor), opacity=sh.opacity or 0.15))
        else:
            items.append(dict(name=sh.name, kind="line", color=_color(sh.line.color), dash=sh.line.dash))
    return items


def _legend_glyph(it: dict, x: float, y: float) -> str:
    if it["kind"] == "line":
        dash = DASH.get(it.get("dash") or "", "")
        return (f'<line x1="{x}" y1="{y}" x2="{x + 22}" y2="{y}" stroke="{it["color"]}" stroke-width="2.4" '
                f'stroke-linecap="round"{f" stroke-dasharray=\"{dash}\"" if dash else ""}/>')
    if it["kind"] == "band":
        return (f'<rect x="{x}" y="{y - 7}" width="22" height="14" rx="3" fill="{it["color"]}" '
                f'fill-opacity="{max(it.get("opacity", 0.15), 0.25)}" stroke="{it["color"]}" stroke-opacity=".6"/>')
    return f'<rect x="{x + 4}" y="{y - 7}" width="14" height="14" rx="3" fill="{it["color"]}"/>'


# ---------------------------------------------------------------- public
def legend_svg(fig, title: str | None = None) -> str:
    """Legend only: one row per series, vertical, on white. Drop it next to a chart in slides or papers."""
    items = legend_items(fig)
    row, pad = 26, 14
    width = pad * 2 + 32 + max([len(i["name"]) for i in items] + [len(title or "")]) * 7.6
    top = pad + (26 if title else 0)
    height = top + row * len(items) + pad - 8
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
             f'viewBox="0 0 {width:.0f} {height:.0f}" font-family="{FONT}">',
             f'<rect width="100%" height="100%" fill="#FFFFFF"/>']
    if title:
        parts.append(f'<text x="{pad}" y="{pad + 12}" font-size="13" font-weight="600" fill="{t.TEXT}">{escape(title)}</text>')
    for k, it in enumerate(items):
        y = top + k * row + 9
        parts.append(_legend_glyph(it, pad, y))
        parts.append(f'<text x="{pad + 32}" y="{y + 4.5}" font-size="13" fill="{t.TEXT}">{escape(it["name"])}</text>')
    parts.append("</svg>")
    return "".join(parts)


def figure_svg(fig, width: int = 960, height: int = 540, legend: bool = True) -> str:
    """The chart as a standalone SVG on white (title, axes, ticks, series, bands, limit lines, legend)."""
    lay = fig.layout
    title = lay.title.text or ""
    xt = lay.xaxis.title.text or ""
    yt = lay.yaxis.title.text or ""
    ylog = lay.yaxis.type == "log"
    items = legend_items(fig) if legend else []
    # legend laid out in rows under the title
    lx, rows, row_w = [], 0, 0
    avail = width - 90
    for it in items:
        w = 32 + len(it["name"]) * 7.2 + 18
        if row_w + w > avail:
            rows, row_w = rows + 1, 0
        lx.append((rows, row_w))
        row_w += w
    n_rows = rows + 1 if items else 0
    ml, mr, mb = 78, 24, 56
    mt = 46 + n_rows * 22
    pw, ph = width - ml - mr, height - mt - mb

    xs, ys = [], []
    for tr, x, y in _series(fig):
        ok = np.isfinite(x) & np.isfinite(y)
        if ylog:
            ok &= y > 0
        xs.append(x[ok])
        ys.append(y[ok])
        if tr.type == "bar":
            ys.append(np.array([0.0]))
    for sh in lay.shapes:
        if sh.type == "line" and sh.yref == "y" and sh.y0 is not None:
            ys.append(np.array([sh.y0]))
    xall = np.concatenate(xs) if xs else np.array([0.0, 1.0])
    yall = np.concatenate(ys) if ys else np.array([0.0, 1.0])
    x0, x1 = (float(lay.xaxis.range[0]), float(lay.xaxis.range[1])) if lay.xaxis.range else (float(xall.min()), float(xall.max()))
    if lay.yaxis.range and not ylog:
        y0, y1 = float(lay.yaxis.range[0]), float(lay.yaxis.range[1])
    else:
        lo, hi = float(yall.min()), float(yall.max())
        if ylog:
            y0, y1 = math.log10(lo) - 0.05, math.log10(hi) + 0.05
        else:
            span = (hi - lo) or abs(hi) or 1
            y0, y1 = (0.0 if lo >= 0 and lo - 0.05 * span <= 0 else lo - 0.05 * span), hi + 0.06 * span
    if x1 == x0:
        x1 = x0 + 1
    if y1 == y0:
        y1 = y0 + 1

    def X(v):
        return ml + (v - x0) / (x1 - x0) * pw

    def Y(v):
        v = math.log10(v) if ylog else v
        return mt + ph - (v - y0) / (y1 - y0) * ph

    big_y = ylog or max(abs(y0), abs(y1)) >= 1e5
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
         f'font-family="{FONT}">', '<rect width="100%" height="100%" fill="#FFFFFF"/>',
         f'<defs><clipPath id="plot"><rect x="{ml}" y="{mt}" width="{pw}" height="{ph}"/></clipPath></defs>']
    if title:
        p.append(f'<text x="{ml}" y="24" font-size="16" font-weight="600" fill="{t.TEXT}">{escape(title)}</text>')
    for it, (r, off) in zip(items, lx):
        y = 44 + r * 22
        p.append(_legend_glyph(it, ml + off, y))
        p.append(f'<text x="{ml + off + 30}" y="{y + 4.5}" font-size="12" fill="{t.TEXT_MUTED}">{escape(it["name"])}</text>')

    # bands under everything
    for sh in lay.shapes:
        if sh.type == "rect" and sh.xref == "x":
            p.append(f'<rect clip-path="url(#plot)" x="{X(sh.x0):.1f}" y="{mt}" width="{X(sh.x1) - X(sh.x0):.1f}" '
                     f'height="{ph}" fill="{_color(sh.fillcolor)}" fill-opacity="{sh.opacity or 0.1}"/>')
        elif sh.type == "rect" and sh.yref == "y":
            p.append(f'<rect clip-path="url(#plot)" x="{ml}" y="{Y(sh.y1):.1f}" width="{pw}" '
                     f'height="{Y(sh.y0) - Y(sh.y1):.1f}" fill="{_color(sh.fillcolor)}" fill-opacity="{sh.opacity or 0.1}"/>')
    # grid + ticks
    if ylog:
        decades = range(math.floor(y0), math.ceil(y1) + 1)
        yticks = [m * 10 ** k for k in decades for m in (1, 2, 5) if y0 <= math.log10(m * 10 ** k) <= y1]
    else:
        yticks = _nice_ticks(y0, y1)
    for v in yticks:
        yy = Y(v)
        p.append(f'<line x1="{ml}" x2="{ml + pw}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="{t.GRID}"/>')
        p.append(f'<text x="{ml - 8}" y="{yy + 4:.1f}" font-size="11" text-anchor="end" font-family="{MONO}" '
                 f'fill="{t.TEXT_SUBTLE}">{_fmt(v, big_y)}</text>')
    for v in _nice_ticks(x0, x1, 8):
        xx = X(v)
        p.append(f'<line x1="{xx:.1f}" x2="{xx:.1f}" y1="{mt}" y2="{mt + ph}" stroke="{t.GRID}"/>')
        p.append(f'<text x="{xx:.1f}" y="{mt + ph + 18}" font-size="11" text-anchor="middle" font-family="{MONO}" '
                 f'fill="{t.TEXT_SUBTLE}">{_fmt(v, False)}</text>')
    p.append(f'<rect x="{ml}" y="{mt}" width="{pw}" height="{ph}" fill="none" stroke="{t.HAIRLINE_STRONG}"/>')
    if xt:
        p.append(f'<text x="{ml + pw / 2}" y="{height - 14}" font-size="12" text-anchor="middle" fill="{t.TEXT_MUTED}">{escape(xt)}</text>')
    if yt:
        p.append(f'<text transform="translate(20 {mt + ph / 2}) rotate(-90)" font-size="12" text-anchor="middle" '
                 f'fill="{t.TEXT_MUTED}">{escape(yt)}</text>')

    # series
    for tr, x, y in _series(fig):
        if tr.type == "bar":
            n = max(len(x), 1)
            bw = max(pw / max((x1 - x0 + 1), n) * 0.6, 2)
            for xi, yi in zip(x, y):
                if np.isfinite(xi) and np.isfinite(yi):
                    top = min(Y(yi), Y(max(y0, 0)))
                    p.append(f'<rect clip-path="url(#plot)" x="{X(xi) - bw / 2:.1f}" y="{top:.1f}" width="{bw:.1f}" '
                             f'height="{abs(Y(max(y0, 0)) - Y(yi)):.1f}" rx="2" fill="{_color(tr.marker.color)}"/>')
            continue
        dash = DASH.get(tr.line.dash or "", "")
        seg, segs = [], []
        for xi, yi in zip(x, y):
            if np.isfinite(xi) and np.isfinite(yi) and (not ylog or yi > 0):
                seg.append(f"{X(xi):.1f},{Y(yi):.1f}")
            elif seg:
                segs.append(seg)
                seg = []
        if seg:
            segs.append(seg)
        for sg in segs:
            p.append(f'<polyline clip-path="url(#plot)" fill="none" stroke="{_color(tr.line.color)}" '
                     f'stroke-width="{tr.line.width or 2}" stroke-linejoin="round" stroke-linecap="round"'
                     f'{f" stroke-dasharray=\"{dash}\"" if dash else ""} points="{" ".join(sg)}"/>')

    # reference lines (limits, window, marker) + their labels
    for sh in lay.shapes:
        if sh.type != "line":
            continue
        dash = DASH.get(sh.line.dash or "", "")
        attrs = (f'stroke="{_color(sh.line.color)}" stroke-width="{sh.line.width or 1.4}"'
                 f'{f" stroke-dasharray=\"{dash}\"" if dash else ""} opacity="{sh.opacity if sh.opacity is not None else 1}"')
        if sh.yref == "y":
            p.append(f'<line x1="{ml}" x2="{ml + pw}" y1="{Y(sh.y0):.1f}" y2="{Y(sh.y0):.1f}" {attrs}/>')
        elif sh.xref == "x":
            p.append(f'<line x1="{X(sh.x0):.1f}" x2="{X(sh.x0):.1f}" y1="{mt}" y2="{mt + ph}" {attrs}/>')
    for an in lay.annotations:
        if an.text and an.yref == "y" and an.y is not None:
            p.append(f'<text x="{ml + pw - 4}" y="{Y(an.y) - 5:.1f}" font-size="11" text-anchor="end" '
                     f'fill="{t.TEXT_MUTED}">{escape(str(an.text))}</text>')
    p.append("</svg>")
    return "".join(p)


def figure_csv(fig) -> bytes:
    """The plotted data in long form: series, x, y."""
    lines = ["series,x,y"]
    for tr, x, y in _series(fig):
        name = (tr.name or "series").replace('"', "'")
        lines += [f'"{name}",{xi:.6g},{"" if not np.isfinite(yi) else f"{yi:.6g}"}' for xi, yi in zip(x, y)]
    return ("\n".join(lines) + "\n").encode("utf-8")
