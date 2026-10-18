"""Chart downloads: SVG plot, legend-only SVG and CSV, built from the same figures the app shows."""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from ui import charts, svg_export  # noqa: E402

from bioprocess.defaults import example_scenario  # noqa: E402
from bioprocess.simulate import simulate  # noqa: E402
from bioprocess.summary import fedbatch_volume_per_day  # noqa: E402

R = simulate(example_scenario())
FIGS = {"vcc": charts.vcc(R, False, 3.5), "vcc_log": charts.vcc(R, True), "metabolites": charts.metabolites(R),
        "volume": charts.volume(R), "cumulative": charts.cumulative(R), "biomass": charts.biomass(R),
        "fedbatch": charts.fedbatch_bars(fedbatch_volume_per_day(R))}


@pytest.mark.parametrize("name", FIGS)
def test_figure_svg_is_valid_and_complete(name):
    svg = svg_export.figure_svg(FIGS[name])
    root = ET.fromstring(svg)                                  # well-formed XML
    assert root.tag.endswith("svg")
    assert "#FFFFFF" in svg                                    # white background
    assert ("<polyline" in svg) or ("<rect clip-path" in svg)  # data drawn
    assert "nan" not in svg.lower()


def test_legend_contains_series_phases_and_limits():
    items = {i["name"]: i for i in svg_export.legend_items(FIGS["metabolites"])}
    assert {"Glucose", "Lactate", "Fed-batch phase", "Continuous phase", "Glucose minimum", "Lactate maximum"} <= set(items)
    assert items["Fed-batch phase"]["kind"] == "band" and items["Glucose minimum"]["kind"] == "line"
    svg = svg_export.legend_svg(FIGS["metabolites"], "Metabolites")
    ET.fromstring(svg)
    assert "Lactate maximum" in svg and "<polyline" not in svg   # legend only, no data


def test_marker_line_not_in_legend_and_volume_window_named():
    names = [i["name"] for i in svg_export.legend_items(FIGS["vcc"])]
    assert "VCC" in names and all("marker" not in n.lower() for n in names)
    vol = [i["name"] for i in svg_export.legend_items(FIGS["volume"])]
    assert "Allowed volume window" in vol and "V_min" in vol


def test_csv_matches_figure_data():
    csv = svg_export.figure_csv(FIGS["vcc"]).decode().splitlines()
    assert csv[0] == "series,x,y" and len(csv) == 1 + len(R.table)
    assert csv[1].startswith('"VCC",0,800000')


def test_log_axis_has_several_ticks_within_one_decade():
    svg = svg_export.figure_svg(FIGS["vcc_log"])
    assert sum(lbl in svg for lbl in (">1.0E6<", ">2.0E6<", ">5.0E6<")) == 3
