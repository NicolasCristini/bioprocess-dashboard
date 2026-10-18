"""Derived outputs (MODEL.md §2.5): key numbers, per-phase summary, metabolite check, daily table."""
from __future__ import annotations

import math

import pandas as pd

from .simulate import SimResult

# key -> (label, unit, format); order is the display order
KEY_NUMBERS = {
    "duration_d": ("Process duration", "days", "{:.0f}"),
    "final_vcc": ("Final cell density", "cells/mL", "{:.3e}"),
    "final_volume_L": ("Final working volume", "L", "{:.3f}"),
    "max_volume_L": ("Max working volume", "L", "{:.3f}"),
    "fb_feed_L": ("Fed-batch feed added", "L", "{:.3f}"),
    "perf_medium_L": ("Perfusion medium used", "L", "{:.3f}"),
    "fresh_medium_L": ("Total fresh medium", "L", "{:.3f}"),
    "bleed_L": ("Bleed volume", "L", "{:.3f}"),
    "harvest_L": ("Harvest volume (cell-free)", "L", "{:.3f}"),
    "cells_inoculated": ("Cells inoculated", "cells", "{:.3e}"),
    "cells_end": ("Cells in reactor at end", "cells", "{:.3e}"),
    "cells_bled": ("Cells removed by bleed", "cells", "{:.3e}"),
    "cells_produced": ("Total cells produced", "cells", "{:.3e}"),
    "wb_reactor_end_g": ("Wet biomass in reactor at end", "g", "{:.2f}"),
    "wb_bleed_g": ("Wet biomass removed by bleed", "g", "{:.2f}"),
    "wb_total_g": ("Total wet biomass produced", "g", "{:.2f}"),
}


def key_numbers(r: SimResult) -> dict[str, float]:
    if r.table.empty:
        return {}
    tb, s = r.table, r.scenario.setup
    last = tb.iloc[-1]
    k = s.wet_biomass_g_per_L_at_1e6
    inoc = s.seeding_density * s.initial_wv_L * 1000
    end = last.vcc * last.volume_L * 1000
    produced = end + last.cum_cells_bled - inoc
    return {
        "duration_d": float(last.t_d),
        "final_vcc": float(last.vcc),
        "final_volume_L": float(last.volume_L),
        "max_volume_L": float(tb.volume_L.max()),
        "fb_feed_L": float(last.cum_fb_L),
        "perf_medium_L": float(last.cum_perf_L),
        "fresh_medium_L": float(last.cum_fresh_L),
        "bleed_L": float(last.cum_bleed_L),
        "harvest_L": float(last.cum_harvest_L),
        "cells_inoculated": inoc,
        "cells_end": float(end),
        "cells_bled": float(last.cum_cells_bled),
        "cells_produced": float(produced),
        "wb_reactor_end_g": float(end * k / 1e9),
        "wb_bleed_g": float(last.cum_cells_bled * k / 1e9),
        "wb_total_g": float(produced * k / 1e9),
    }


def phase_summary(r: SimResult) -> pd.DataFrame:
    tb = r.table
    rows = []
    for p in r.plans:
        seg = tb[tb.phase == p.index].iloc[1:] if p.index == 1 else tb[tb.phase == p.index]
        end = seg.iloc[-1] if len(seg) else None
        row = {
            "Phase": p.index, "Type": p.type, "Start day": p.start_day, "End day": p.end_day,
            "µ (1/day)": p.mu,
            "Doubling time (h)": math.log(2) / p.mu * 24 if p.mu > 0 else math.nan,
            "Start VCC": p.x_start, "End VCC": p.x_end,
            "Bleed (VVD)": p.bleed if p.type == "Continuous" else math.nan,
            "Feed (VVD)": p.feed if p.type == "Continuous" else math.nan,
            "Suggested min. feed (VVD)": p.suggested_min_feed if p.suggested_min_feed is not None else math.nan,
            "Fed-batch feed (L)": seg.fb_feed_L.sum(), "Perfusion medium (L)": seg.perf_feed_L.sum(),
            "Bleed (L)": seg.bleed_L.sum(), "Harvest (L)": seg.harvest_L.sum(),
            "Cells bled": seg.cells_bled.sum(),
            "Volume at end (L)": end.volume_L if end is not None else math.nan,
        }
        for m in r.metabolite_names:
            row[f"{m} at end (mM)"] = end[m] if end is not None else math.nan
        rows.append(row)
    return pd.DataFrame(rows)


def metabolite_check(r: SimResult) -> pd.DataFrame:
    rows = []
    for m in r.scenario.metabolites:
        col = r.table[m.name] if m.name in r.table else pd.Series(dtype=float)
        has = col.notna().any()
        lo, hi = (float(col.min()), float(col.max())) if has else (math.nan, math.nan)
        if not has or m.limit is None:
            status = "(no data)"
        elif m.sign < 0:
            status = "⚠ drops below limit" if lo < m.limit else "OK"
        else:
            status = "⚠ exceeds limit" if hi > m.limit else "OK"
        rows.append({"Metabolite": m.name, "Kind": m.kind, "Min (mM)": lo, "Max (mM)": hi,
                     "Limit (mM)": m.limit if m.limit is not None else math.nan, "Status": status})
    return pd.DataFrame(rows)


def daily_table(r: SimResult) -> pd.DataFrame:
    """One row per whole day: states at the end of the day, flows summed over the day."""
    tb = r.table
    if tb.empty:
        return tb
    flows = ["fb_feed_L", "perf_feed_L", "bleed_L", "harvest_L", "cells_bled"]
    body = tb.iloc[1:]
    agg = body.groupby("day")[flows].sum()
    states = body.groupby("day").last().drop(columns=flows + ["step", "avg_vcc"])
    out = pd.concat([states, agg], axis=1).reset_index()
    first = tb.iloc[[0]].drop(columns=["step", "avg_vcc"])
    return pd.concat([first, out], ignore_index=True)[list(first.columns)]


def fedbatch_volume_per_day(r: SimResult) -> pd.DataFrame:
    """Volume added by fed-batch feeding on each process day (L)."""
    tb = r.table.iloc[1:]
    fb = tb[tb.type == "Fed-batch"].groupby("day").fb_feed_L.sum()
    return fb[fb > 0].rename("Volume added (L)").reset_index().rename(columns={"day": "Day"})
