import pandas as pd
import streamlit as st

from bioprocess import registry
from ui import state, theme
from ui.widgets import none_if_nan

sc = state.sc()
card = state.model()
cards = registry.discover()
theme.top("Model", card.summary.strip(),
          [("Selected", card.label, "accent"), ("Status", card.status, "accent" if card.status == "validated" else "warning"),
           ("Available", str(len(cards)), "")])

# ---- parameters declared by the model card (generic editor: any future model gets one for free)
specs = card.parameters.get("per_metabolite", [])
with st.container(border=True):
    if not specs:
        theme.panel_title("Model parameters", "This model has no parameters of its own. It uses only the scenario inputs "
                                              "(Setup, Phases, Feed regimes).")
    else:
        theme.panel_title("Model parameters", "Stored in the scenario for this model only, so the scenario still runs "
                                              "unchanged under other models. Leave a cell empty to switch the term off.")
        current = card.params_for(sc)
        rows = []
        for m in sc.metabolites:
            row = {"Metabolite": m.name, "Kind": m.kind}
            for p in specs:
                applies = p.get("applies_to", "any") in ("any", m.kind)
                row[p["key"]] = (current.get(m.name) or {}).get(p["key"]) if applies else None
            rows.append(row)
        df = pd.DataFrame(rows)
        for p in specs:
            df[p["key"]] = df[p["key"]].astype(float)
        edited = st.data_editor(
            df, hide_index=True, width="stretch", key=state.key(f"mp_{card.id}"), disabled=["Metabolite", "Kind"],
            column_config={p["key"]: st.column_config.NumberColumn(f'{p["label"]} ({p["unit"]})', help=p.get("help"),
                                                                  min_value=0.0, format="%.4g") for p in specs})
        new = {}
        for row in edited.to_dict("records"):
            kind = row["Kind"]
            vals = {p["key"]: none_if_nan(row.get(p["key"])) for p in specs
                    if p.get("applies_to", "any") in ("any", kind)}
            if vals:
                new[row["Metabolite"]] = vals
        if new != (sc.model_params.get(card.id) or card.params_for(sc)):
            sc.model_params = {**sc.model_params, card.id: new}
        d1, d2 = st.columns([1, 3], vertical_alignment="center")
        if d1.button("Reset to card defaults", icon=":material/restart_alt:"):
            sc.model_params = {k: v for k, v in sc.model_params.items() if k != card.id}
            state.bump()
            st.rerun()
        d2.caption("Applies to: " + "; ".join(f'{p["key"]} on {p.get("applies_to", "any")} metabolites' for p in specs))

# ---- quick comparison of this scenario across all models
with st.container(border=True):
    theme.panel_title("This scenario under every model", "Same inputs, different models. Open Compare for the overlays.")
    from bioprocess.summary import key_numbers
    rows = []
    for mid, c in cards.items():
        r = state.result(mid)
        k = key_numbers(r) if r.ok else {}
        rows.append({"Model": c.label, "Status": c.status,
                     "Fresh medium (L)": k.get("fresh_medium_L"), "Final VCC": k.get("final_vcc"),
                     "Wet biomass (g)": k.get("wb_total_g"),
                     "Checks": sum(i.level == "warning" for i in r.issues), "Blocking": sum(i.level == "block" for i in r.issues)})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                 column_config={"Final VCC": st.column_config.NumberColumn(format="%.3e"),
                                "Fresh medium (L)": st.column_config.NumberColumn(format="%.3f"),
                                "Wet biomass (g)": st.column_config.NumberColumn(format="%.2f")})
    if st.button("Compare models", icon=":material/compare_arrows:"):
        st.session_state.compare_mode = "Models"
        st.switch_page("pages/p5_compare.py")

# ---- the spec itself
with st.expander(f"Specification: {card.spec_file.name}", expanded=False, icon=":material/description:"):
    st.markdown(card.spec_text())

with st.expander("Adding a model version", icon=":material/add_circle:"):
    st.markdown("""
Model versions live in the repository folder **`models/`**, one sub-folder per version:

```
models/
  v1-baseline/   model.md (card, points to MODEL.md)   model.py
  v2-monod/      MODEL2.md (card + spec)                model.py
  <your-id>/     <NAME>.md                              model.py
```

1. Copy the closest folder, for example `v2-monod`, to `models/<your-id>/`.
2. In the `.md` front matter set `id`, `name`, `version`, `status: development`, `summary`, and the
   `parameters` your model needs. The Model page builds its editor from these.
3. In `model.py` implement `simulate(scenario, params, steps_per_day=None, **kw)` returning a `SimResult`.
   Reuse `bioprocess.simulate.table_row` and `run_checks`, so every output, chart and comparison works unchanged.
4. Add tests next to `tests/test_models.py`: the reduction to the parent model, plus reference values.
5. Push. The app discovers the folder and the shared link updates. Mark it `validated` once the tests and a review pass.
""")
