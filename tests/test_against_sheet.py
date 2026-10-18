"""Day-by-day parity with the original spreadsheet (sheet-parity mode: daily steps, bolus feeding)."""
import math

import pytest

from bioprocess.simulate import simulate

COLS = {  # fixture column -> model column
    "vcc": "vcc", "fb_bolus_L": "fb_feed_L", "volume_L": "volume_L", "avg_vcc": "avg_vcc",
    "perf_feed_L": "perf_feed_L", "bleed_L": "bleed_L", "harvest_L": "harvest_L", "cells_bled": "cells_bled",
    "cum_fresh_L": "cum_fresh_L", "cum_harvest_L": "cum_harvest_L", "cum_bleed_L": "cum_bleed_L",
    "cum_cells_bled": "cum_cells_bled", "Glucose": "Glucose", "Lactate": "Lactate", "Glutamine": "Glutamine",
    "Glutamate": "Glutamate", "Ammonia": "Ammonia", "wb_g_per_L": "wb_g_per_L", "wb_reactor_g": "wb_reactor_g",
    "cum_wb_bleed_g": "cum_wb_bleed_g",
}


@pytest.mark.parametrize("name", ["ref", "regB", "cc", "hold"])
def test_matches_spreadsheet_day_by_day(sheet, name):
    sc, rows = sheet(name)
    r = simulate(sc, steps_per_day=1, fedbatch_feeding="bolus")
    assert r.ok, [i.message for i in r.issues if i.level == "block"]
    assert len(r.table) == len(rows)
    for k, (row, (_, got)) in enumerate(zip(rows, r.table.iterrows())):
        assert got.phase == row["phase"] and got.type == row["type"], f"day {k}"
        for fc, mc in COLS.items():
            want = row[fc]
            if want in (None, ""):
                assert math.isnan(got[mc]), f"day {k} {fc}: expected blank, got {got[mc]}"
            else:
                assert got[mc] == pytest.approx(float(want), rel=1e-9, abs=1e-9), f"day {k} {fc}"
