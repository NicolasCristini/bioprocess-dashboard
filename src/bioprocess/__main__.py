"""python -m bioprocess [scenario.yaml]  — print key numbers; with no file, the MODEL.md §5 reference table."""
import sys
from pathlib import Path

from .defaults import example_scenario
from .io.scenario_file import from_text
from .simulate import simulate
from .summary import key_numbers


def _row(label, r):
    k = key_numbers(r)
    return (f"{label:44s} D={r.plans[-1].feed:.4f}  fresh={k['fresh_medium_L']:.3f} L  harvest={k['harvest_L']:.3f} L  "
            f"maxV={k['max_volume_L']:.3f} L  bled={k['cells_bled']:.3e}  wet={k['wb_total_g']:.1f} g  "
            f"lactate peak/end={r.table.Lactate.max():.2f}/{r.table.Lactate.iloc[-1]:.2f}  glucose min={r.table.Glucose.min():.2f}")


def main(argv: list[str]) -> None:
    if argv:
        r = simulate(from_text(Path(argv[0]).read_text(encoding="utf-8")))
        for i in r.issues:
            print(i.icon, i.message)
        for key, v in key_numbers(r).items():
            print(f"{key:20s} {v:.6g}")
        return
    print("MODEL.md §5 reference plan")
    print(_row("Example plan (hourly, flow, D = b)", simulate(example_scenario(mu_digits=None))))
    print(_row("Hourly, flow, D = suggested", simulate(example_scenario("suggested", None))))
    print(_row("Sheet parity (daily, bolus, D = suggested)",
               simulate(example_scenario("suggested", None), steps_per_day=1, fedbatch_feeding="bolus")))


if __name__ == "__main__":
    main(sys.argv[1:])
