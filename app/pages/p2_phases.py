import math

import streamlit as st

from bioprocess.checks import validate
from bioprocess.defaults import blank_phase
from bioprocess.models import MAX_DAYS, MAX_PHASES, REGIME_DAYS, ContinuousPhase, FedBatchPhase
from bioprocess.suggest import plan_phases
from ui import state
from ui.widgets import PHASE_COLOR, PHASE_ICON, sci, show_issues

sc = state.sc()
st.title("2 · Phases")
st.caption(f"Up to {MAX_PHASES} phases, {MAX_DAYS} days in total. Every phase needs a duration and a specific "
           "growth rate µ; the end cell density follows from them.")

issues = validate(sc)
try:
    plans = plan_phases(sc)
except Exception:  # noqa: BLE001 - e.g. a missing regime; the issues list explains it
    plans = []

# ---- timeline strip
total = max(sc.total_days, 1)
strip = "".join(
    f'<div title="{p.type}, {p.days} d" style="flex:{p.days};background:{PHASE_COLOR[p.type]};color:white;'
    f'padding:4px 6px;font-size:12px;overflow:hidden;white-space:nowrap;border-right:2px solid white">'
    f'{i}. {p.type} · {p.days} d</div>' for i, p in enumerate(sc.phases, 1))
st.markdown(f'<div style="display:flex;border-radius:6px;overflow:hidden;margin-bottom:4px">{strip}</div>'
            f'<div style="font-size:12px;color:#888">day 0 → day {sc.total_days}</div>', unsafe_allow_html=True)


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
        h1, h2, h3, h4 = st.columns([5, 1, 1, 1])
        h1.markdown(f"#### {PHASE_ICON[ph.type]} Phase {i + 1} · <span style='color:{PHASE_COLOR[ph.type]}'>"
                    f"{ph.type}</span>", unsafe_allow_html=True)
        h2.button("↑", key=state.key(f"up{i}"), disabled=i == 0, on_click=move, args=(i, -1), help="Move up")
        h3.button("↓", key=state.key(f"dn{i}"), disabled=i == len(sc.phases) - 1, on_click=move, args=(i, 1),
                  help="Move down")
        h4.button("✕", key=state.key(f"rm{i}"), on_click=remove, args=(i,), help="Remove phase")

        c1, c2, c3, c4 = st.columns(4)
        c1.selectbox("Type", ["Batch", "Fed-batch", "Continuous"], index=["Batch", "Fed-batch", "Continuous"].index(ph.type),
                     key=state.key(f"type{i}"), on_change=retype, args=(i,))
        max_days = REGIME_DAYS if ph.type == "Fed-batch" else MAX_DAYS
        ph.days = int(c2.number_input("Duration (days)", 1, max_days, min(ph.days, max_days), 1, key=state.key(f"days{i}")))
        ph.mu = float(c3.number_input("µ (1/day)", -5.0, 5.0, float(ph.mu), 0.01, format="%.5f", key=state.key(f"mu{i}"),
                                      help="Specific growth rate in this phase. Pre-filled from the previous phase."))
        if plan:
            td = f"{math.log(2) / ph.mu * 24:.1f} h" if ph.mu > 0 else "—"
            c4.markdown(f"<div style='font-size:13px;line-height:1.6'>Start VCC {sci(plan.x_start)}<br>"
                        f"End VCC <b>{sci(plan.x_end)}</b><br>Doubling time {td}</div>", unsafe_allow_html=True)

        if isinstance(ph, FedBatchPhase):
            names = [r.name for r in sc.regimes]
            idx = names.index(ph.regime) if ph.regime in names else 0
            ph.regime = st.selectbox("Feed regime", names, index=idx, key=state.key(f"reg{i}"),
                                     help="Defined on 3 · Feed regimes. Fed as a constant flow over each day.")
            reg = sc.regime(ph.regime)
            if reg:
                vols = [reg.pct(d) / 100 * sc.setup.initial_wv_L for d in range(1, ph.days + 1)]
                st.caption("Volume added per day: " + " · ".join(f"d{d}: {v:.3f} L" for d, v in enumerate(vols, 1) if v)
                           + f"  —  **total {sum(vols):.3f} L**" if any(vols) else "No feed in this regime for these days.")

        if isinstance(ph, ContinuousPhase):
            b1, b2, b3 = st.columns([1, 1, 1])
            use_sug_bleed = b1.toggle("Bleed = suggested (µ, holds VCC)", ph.bleed_vvd == "suggested",
                                      key=state.key(f"bsug{i}"))
            if use_sug_bleed:
                ph.bleed_vvd = "suggested"
                b1.metric("Bleed rate", f"{ph.mu:.4f} VVD")
            else:
                cur = ph.mu if ph.bleed_vvd == "suggested" else float(ph.bleed_vvd)
                ph.bleed_vvd = float(b1.number_input("Bleed rate (VVD)", 0.0, 50.0, cur, 0.01, format="%.4f",
                                                     key=state.key(f"bleed{i}")))
            lock = b2.toggle("Feed = bleed", ph.feed_vvd == "= bleed", key=state.key(f"lock{i}"),
                             help="Default: no harvest, constant volume. Unlock to feed more than the bleed; "
                                  "the excess leaves as a cell-free harvest.")
            if lock:
                ph.feed_vvd = "= bleed"
                b2.metric("Feed rate", f"{plan.feed:.4f} VVD" if plan else "—")
            else:
                cur = plan.feed if plan else 1.0
                ph.feed_vvd = float(b2.number_input("Feed rate (VVD)", 0.0, 50.0, float(cur), 0.01, format="%.4f",
                                                    key=state.key(f"feed{i}")))
            if plan and plan.suggested_min_feed is not None:
                b3.markdown(f"<div style='font-size:13px;line-height:1.6'>Suggested bleed {plan.suggested_bleed:.4f} VVD"
                            f"<br>Suggested min. feed <b>{plan.suggested_min_feed:.4f} VVD</b></div>",
                            unsafe_allow_html=True)
                if plan.feed < plan.suggested_min_feed - 1e-6:
                    def use_sug(i=i, f=plan.suggested_min_feed):
                        sc.phases[i].feed_vvd = round(f, 4)
                        state.bump()
                    b3.button("Use suggested feed", key=state.key(f"usesug{i}"), on_click=use_sug,
                              help="Unlocks feed = bleed; the extra medium leaves as a cell-free harvest.")
                    b3.caption(f"⚠ At {plan.feed:.3f} VVD some metabolites settle beyond their limits.")
            if plan and plan.feed > plan.bleed + 1e-9:
                res = state.result()
                seg = res.table[res.table.phase == i + 1] if not res.table.empty else None
                v_ph = float(seg.volume_L.iloc[0]) if seg is not None and len(seg) else sc.setup.initial_wv_L
                st.caption(f"Cell-free harvest = (feed − bleed) × V ≈ {(plan.feed - plan.bleed) * v_ph:.3f} L/day "
                           f"at V = {v_ph:.3f} L.")
        show_issues([x for x in issues if x.phase == i + 1 and x.where == "phases"])


def add(kind):
    prev = sc.phases[-1] if sc.phases else None
    sc.phases.append(blank_phase(kind, mu=prev.mu if prev else 0.5,
                                 regime=sc.regimes[0].name if sc.regimes else "Regime A"))
    state.bump()


st.markdown("**+ Add phase**")
a1, a2, a3, _ = st.columns([1, 1, 1, 3])
full = len(sc.phases) >= MAX_PHASES
for col, kind in zip((a1, a2, a3), ("Batch", "Fed-batch", "Continuous")):
    col.button(f"{PHASE_ICON[kind]} {kind}", key=state.key(f"add{kind}"), on_click=add, args=(kind,), disabled=full,
               width="stretch")
show_issues([x for x in issues if x.where == "phases" and x.phase is None])
