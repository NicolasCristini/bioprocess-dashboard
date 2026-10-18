"""Small shared UI helpers."""
from __future__ import annotations

import math

from . import theme
from .tokens import PHASE as PHASE_COLOR  # noqa: F401  (re-exported for pages and charts)


def sci(v: float | None, digits: int = 3) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "-"
    return f"{v:.{digits - 1}e}".replace("e+0", "E").replace("e+", "E").replace("e-0", "E-").replace("e-", "E-")


def show_issues(issues, empty: str | None = None) -> None:
    theme.issues(issues, ok_text=empty)


def none_if_nan(v):
    try:
        return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)
    except (TypeError, ValueError):
        return None
