"""Result exports: CSV and Excel (values only)."""
from __future__ import annotations

import io

import pandas as pd

from ..simulate import SimResult
from ..summary import KEY_NUMBERS, daily_table, key_numbers, metabolite_check, phase_summary
from .scenario_file import to_yaml


def table_csv(r: SimResult, daily: bool = False) -> bytes:
    tb = daily_table(r) if daily else r.table
    return tb.to_csv(index=False).encode("utf-8")


def key_numbers_frame(r: SimResult) -> pd.DataFrame:
    k = key_numbers(r)
    return pd.DataFrame([{"Key number": KEY_NUMBERS[key][0], "Value": v, "Unit": KEY_NUMBERS[key][1]}
                         for key, v in k.items()])


def results_xlsx(r: SimResult) -> bytes:
    import openpyxl  # noqa: F401  (lazy: slow to import in the browser)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        key_numbers_frame(r).to_excel(xw, sheet_name="Key numbers", index=False)
        phase_summary(r).to_excel(xw, sheet_name="Per phase", index=False)
        metabolite_check(r).to_excel(xw, sheet_name="Metabolites", index=False)
        daily_table(r).to_excel(xw, sheet_name="Daily", index=False)
        r.table.to_excel(xw, sheet_name="Time steps", index=False)
        pd.DataFrame({"Scenario (YAML)": to_yaml(r.scenario).splitlines()}).to_excel(xw, sheet_name="Inputs", index=False)
        issues = pd.DataFrame([{"Level": i.level, "Where": i.where, "Phase": i.phase, "Message": i.message}
                               for i in r.issues])
        issues.to_excel(xw, sheet_name="Issues", index=False)
    return buf.getvalue()
