"""Small shared UI helpers."""
from __future__ import annotations

import math

import streamlit as st

from bioprocess.checks import Issue

PHASE_COLOR = {"Batch": "#8c8c8c", "Fed-batch": "#e8873a", "Continuous": "#3a7fd5"}
PHASE_ICON = {"Batch": "▣", "Fed-batch": "◧", "Continuous": "⟳"}


def sci(v: float | None, digits: int = 3) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:.{digits - 1}e}".replace("e+0", "E").replace("e+", "E").replace("e-0", "E-").replace("e-", "E-")


def show_issues(issues: list[Issue], empty: str | None = None) -> None:
    if not issues and empty:
        st.success(empty, icon="✅")
    for i in issues:
        txt = (f"**Phase {i.phase}:** " if i.phase else "") + i.message
        {"block": st.error, "warning": st.warning, "info": st.info}[i.level](txt, icon=i.icon)


def none_if_nan(v):
    try:
        return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)
    except (TypeError, ValueError):
        return None
