import math

import streamlit as st

from bioprocess.checks import validate
from bioprocess.defaults import blank_phase
from bioprocess.models import MAX_DAYS, MAX_PHASES, REGIME_DAYS, ContinuousPhase, FedBatchPhase
from bioprocess.suggest import plan_phases
from ui import state, theme
from ui.widgets import PHASE_COLOR, sci, show_issues

sc = state.sc()
theme.top("Phases", f"Up to {MAX_PHASES} phases and {MAX_DAYS} days. Each phase needs a duration and a specific "
                    "growth rate µ; the end cell density follows from them.",
          [("Phases", f"{len(sc.phases)}/{MAX_PHASES}", ""), ("Duration", f"{sc.total_days} d", "")])

if notes := st.session_state.pop("_import_notes", None):
    st.info("**Imported from the spreadsheet planner.** Check the converted values, then save it in *My scenarios*.\n\n"
            + "\n".join(f"- {n}" for n in notes), icon=":material/upload_file:")

issues = validate(sc)
try:
    plans = plan_phases(sc)
except Exception:  # noqa: BLE001 - e.g. a missing regime; the issues list explains it
    plans = []

# ---- timeline
if sc.phases:
    st.html('<div class="bp-timeline">' + "".join(
        f'<div title="{p.type}, {p.days} d" style="flex:{p.days};background:{PHASE_COLOR[p.type]}">'
        f'{i}. {p.type}, {p.days} d</div>' for i, p in enumerate(sc.phases, 1))
            + f'</div><div class="bp-axis"><span>day 0</span><span>day {sc.total_days}</span></div>')


def move(i, d):
    sc.phases[i], sc.phases[i + d] = sc.phases[i + d], sc.phases[i]
    state.bump()


def remove(i):
    sc.phases.pop(i)
    state.bump()


def retype(i):
    new_type = st.session_state[state.key(f"type{i}")]
    old = sc.phases[i]
    regime = sc.regimes[0].name if sc.regimes else "Regime A"
    p = blank_phase(new_type, mu=old.mu, regime=regime)
    p.days = min(old.days, REGIME_DAYS) if new_type == "Fed-batch" else old.days
    sc.phases[i] = p
    state.bump()


for i, ph in enumerate(sc.phases):
    plan = plans[i] if i < len(plans) else None
    with st.container(border=True):
        h1, h2, h3, h4 = st.columns([10, 1, 1, 1], vertical_alignment="center")
        h1.html(f'<div style="display:flex;align-items:center;gap:10px"><span class="bp-panel-title" '
                f'style="margin:0">Phase {i + 1}</span>{theme.badge(ph.type, PHASE_COLOR[ph.type])}</div>')
        h2.button("", icon=":material/arrow_upward:", key=state.key(f"up{i}"), disabled=i == 0, on_click=move,
                  args=(i, -1), help="Move up")
        h3.button("", icon=":material/arrow_downward:", key=state.key(f"dn{i}"), disabled=i == len(sc.phases) - 1,
                  on_click=move, args=(i, 1), help="Move down")
        h4.button("", icon=":material/close:", key=state.key(f"rm{i}"), on_click=remove, args=(i,), help="Remove phase")

        c1, c2, c3 = st.columns(3)
        c1.selectbox("Type", ["Batch", "Fed-batch", "Continuous"], index=["Batch", "Fed-batch", "Continuous"].index(ph.type),
                     key=state.key(f"type{i}"), on_change=retype, args=(i,))
        max_days = REGIME_DAYS if ph.type == "Fed-batch" else MAX_DAYS
        ph.days = int(c2.number_input("Duration (days)", 1, max_days, min(ph.days, max_days), 1, key=state.key(f"days{i}")))
        ph.mu = float(c3.number_input("µ (1/day)", -5.0, 5.0, float(ph.mu), 0.01, format="%.5f", key=state.key(f"mu{i}"),
                                      help="Specific growth rate in this phase. Pre-filled from the previous phase."))
        if plan:
            td = f"{math.log(2) / ph.mu * 24:.1f} h" if ph.mu > 0 else "-"
            theme.chips([("Start VCC", sci(plan.x_start), ""), ("End VCC", sci(plan.x_end), "accent"),
                         ("Doubling time", td, "")])

        if isinstance(ph, FedBatchPhase):
            names = [r.name for r in sc.regimes]
            idx = names.index(ph.regime) if ph.regime in names else 0
            ph.regime = st.selectbox("Feed regime", names, index=idx, key=state.key(f"reg{i}"),
                                     help="Defined on Feed regimes. Fed as a constant flow over each day.")
            reg = sc.regime(ph.regime)
            if reg:
                vols = [reg.pct(d) / 100 * sc.setup.initial_wv_L for d in range(1, ph.days + 1)]
                if any(vols):
                    theme.chips([(f"Day {d}", f"{v:.3f} L", "") for d, v in enumerate(vols, 1) if v]
                                + [("Total", f"{sum(vols):.3f} L", "accent")])
                else:
                    st.caption("No feed in this regime for these days.")

        if isinstance(ph, ContinuousPhase):
            b1, b2 = st.columns(2)
            use_sug_bleed = b1.toggle("Bleed = µ (holds VCC)", ph.bleed_vvd == "suggested", key=state.key(f"bsug{i}"))
            if use_sug_bleed:
                ph.bleed_vvd = "suggested"
            else:
                cur = ph.mu if ph.bleed_vvd == "suggested" else float(ph.bleed_vvd)
                ph.bleed_vvd = float(b1.number_input("Bleed rate (VVD)", 0.0, 50.0, cur, 0.01, format="%.4f",
                                                     key=state.key(f"bleed{i}")))
            lock = b2.toggle("Feed = bleed", ph.feed_vvd == "= bleed", key=state.key(f"lock{i}"),
                             help="Default: no harvest, constant volume. Unlock to feed more than the bleed; "
                                  "the excess leaves as a cell-free harvest.")
            if not lock:
                cur = plan.feed if plan else 1.0
                ph.feed_vvd = float(b2.number_input("Feed rate (VVD)", 0.0, 50.0, float(cur), 0.01, format="%.4f",
                                                    key=state.key(f"feed{i}")))
            else:
                ph.feed_vvd = "= bleed"
            if plan:
                row = [("Bleed", f"{plan.bleed:.4f} VVD", ""), ("Feed", f"{plan.feed:.4f} VVD", "")]
                if plan.suggested_min_feed is not None:
                    low = plan.feed < plan.suggested_min_feed - 1e-6
                    row.append(("Suggested min. feed", f"{plan.suggested_min_feed:.4f} VVD", "warning" if low else "accent"))
                if plan.feed > plan.bleed + 1e-9:
                    res = state.result()
                    seg = res.table[res.table.phase == i + 1] if not res.table.empty else None
                    v_ph = float(seg.volume_L.iloc[0]) if seg is not None and len(seg) else sc.setup.initial_wv_L
                    row.append(("Harvest", f"{(plan.feed - plan.bleed) * v_ph:.3f} L/day", ""))
                theme.chips(row)
                if plan.suggested_min_feed is not None and plan.feed < plan.suggested_min_feed - 1e-6:
                    def use_sug(i=i, f=plan.suggested_min_feed):
                        sc.phases[i].feed_vvd = round(f, 4)
                        state.bump()
                    w1, w2 = st.columns([3, 1], vertical_alignment="center")
                    w1.caption(f"At {plan.feed:.3f} VVD some metabolites settle beyond their limits. The suggested "
                               "feed keeps them in range; the extra medium leaves as a cell-free harvest.")
                    w2.button("Use suggested feed", key=state.key(f"usesug{i}"), on_click=use_sug,
                              icon=":material/auto_fix_high:", width="stretch")
        show_issues([x for x in issues if x.phase == i + 1 and x.where == "phases"])


def add(kind):
    prev = sc.phases[-1] if sc.phases else None
    sc.phases.append(blank_phase(kind, mu=prev.mu if prev else 0.5,
                                 regime=sc.regimes[0].name if sc.regimes else "Regime A"))
    state.bump()


full = len(sc.phases) >= MAX_PHASES
a0, a1, a2, a3, _ = st.columns([1.1, 1, 1, 1, 2], vertical_alignment="center")
a0.html('<div class="bp-panel-title" style="margin:0">Add a phase</div>')
for col, kind in zip((a1, a2, a3), ("Batch", "Fed-batch", "Continuous")):
    col.button(kind, icon=":material/add:", key=state.key(f"add{kind}"), on_click=add, args=(kind,), disabled=full,
               width="stretch")
show_issues([x for x in issues if x.where == "phases" and x.phase is None])
