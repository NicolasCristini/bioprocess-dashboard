# models/: model versions

Every sub-folder is one model version. The app discovers the folders automatically: the model selector at the
bottom of the left panel, the Model page, and Compare in "Models" mode.

```
models/
  v1-baseline/   model.md   card only; the spec is the root MODEL.md      model.py  (the shared core)
  v2-monod/      MODEL2.md  card + full spec (Monod limitation)           model.py
  <your-id>/     <NAME>.md  card + spec                                   model.py
```

## How a model is described

A model has three parts, each with one job:

| Part | Read by | Content |
|---|---|---|
| **Card**: the YAML front matter of the `.md` | the app | `id`, `name`, `version`, `status` (development / validated), `summary`, `order`, `parameters` (and `spec:` if the full text lives elsewhere) |
| **Spec**: the Markdown body | people | equations (LaTeX `$$ ... $$` renders on the Model page), parameters, assumptions, reference values |
| **Implementation**: `model.py` | the simulator | `def simulate(scenario, params, steps_per_day=None, **kw) -> SimResult` |

The `.md` is not executed. The equations in the spec and the code in `model.py` are tied together by tests in
`tests/test_models.py`:
- **reduction:** with the new terms switched off, the model must equal its parent;
- **reference values:** pinned numbers that are also printed in the spec.

### Parameters on the card

```yaml
parameters:
  per_metabolite:
    - key: Ks                 # name the model reads: params[metabolite][key]
      label: "Ks, Monod half-saturation"
      unit: mM
      applies_to: consumed    # consumed | produced | any
      help: "..."
      default: {Glucose: 0.5} # blank for the others = term off
```

The Model page builds its editor from this. Values are stored in the scenario under
`model_params[<id>]`, so one scenario runs under every model.

## Adding a version

1. Copy the closest folder to `models/<new-id>/` and rename the spec, for example `MODEL3.md`.
2. Edit the card. Start with `status: development`.
3. Change `model.py`. Reuse `bioprocess.simulate.table_row` and `run_checks`, so the result table has the same
   columns and every page works. Extra columns (like `mu_eff`) are allowed.
4. Add tests: the reduction to the parent model, plus reference values that also go in the spec.
5. `uv run pytest -q`, then push. The shared link picks up the new model on the next deploy.
6. Switch to `status: validated` once it has been reviewed against data.
