"""Scenario comparison: key numbers side by side and aligned time series."""
from __future__ import annotations

import pandas as pd

from .simulate import SimResult
from .summary import KEY_NUMBERS, key_numbers


def key_numbers_table(results: dict[str, SimResult], baseline: str | None = None) -> pd.DataFrame:
    """Rows = key numbers, columns = scenarios (+ Δ% vs baseline for each other scenario)."""
    data = {name: key_numbers(r) for name, r in results.items() if r.ok}
    df = pd.DataFrame(data)
    if df.empty:
        return df
    df.index = pd.Index([f"{KEY_NUMBERS[k][0]} ({KEY_NUMBERS[k][1]})" for k in df.index], name="Key number")
    if baseline in df:
        for col in [c for c in data if c != baseline]:
            base = df[baseline].where(df[baseline] != 0)
            df[f"Δ% {col}"] = (df[col] - df[baseline]) / base.abs() * 100
    return df


def long_series(results: dict[str, SimResult], columns: list[str]) -> pd.DataFrame:
    """Long table (scenario, t_d, variable, value) for overlay charts. Blocked runs are left out."""
    parts = []
    for name, r in results.items():
        if not r.ok:
            continue
        cols = [c for c in columns if c in r.table]
        m = r.table[["t_d", *cols]].melt("t_d", var_name="variable", value_name="value")
        m.insert(0, "scenario", name)
        parts.append(m)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["scenario", "t_d", "variable", "value"])
