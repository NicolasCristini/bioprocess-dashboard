"""Model versions: discovery and loading.

Every sub-folder of `models/` that holds a Markdown spec with a YAML front-matter card and a `model.py` is a model:

    models/<id>/
        <ANY>.md     front matter (id, name, version, status, summary, parameters) + the human-readable spec
        model.py     def simulate(scenario, params, steps_per_day=None, **kw) -> SimResult

The card is what the app reads (selector, parameter editor, info page). The body is the spec shown to people.
Models import the shared core (bioprocess.*) for the data model, checks and table layout, so every model returns
the same SimResult and all summaries, charts and comparisons work unchanged.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .models import Scenario

DEFAULT_ID = "v1-baseline"


def models_dir() -> Path:
    if os.environ.get("BIOPROCESS_MODELS"):
        return Path(os.environ["BIOPROCESS_MODELS"])
    return Path(__file__).resolve().parents[2] / "models"     # repo root natively; /home/pyodide in the browser


@dataclass
class ModelCard:
    id: str
    name: str
    version: str
    status: str                       # "validated" or "development"
    summary: str
    folder: Path
    spec_file: Path
    parameters: dict = field(default_factory=dict)   # {"per_metabolite": [ {key, label, unit, applies_to, default}, ...]}
    order: int = 100

    @property
    def label(self) -> str:
        return f"{self.name} (v{self.version})"

    def spec_text(self) -> str:
        """The spec body without front matter. A card may point to a spec elsewhere (`spec: path`)."""
        try:
            return _split(self.spec_file.read_text(encoding="utf-8"))[1]
        except FileNotFoundError:
            return f"*Specification file not found: `{self.spec_file.name}`.*"

    def _module(self):
        name = f"bioprocess_model_{self.id.replace('-', '_')}"
        if name not in sys.modules:
            spec = importlib.util.spec_from_file_location(name, self.folder / "model.py")
            mod = importlib.util.module_from_spec(spec)
            sys.modules[name] = mod
            spec.loader.exec_module(mod)
        return sys.modules[name]

    def default_params(self, sc: Scenario) -> dict:
        """Card defaults for every metabolite the parameter applies to (None = not set)."""
        out = {}
        for p in self.parameters.get("per_metabolite", []):
            for m in sc.metabolites:
                kind_ok = p.get("applies_to", "any") in ("any", m.kind)
                if kind_ok:
                    out.setdefault(m.name, {})[p["key"]] = (p.get("default") or {}).get(m.name)
        return out

    def params_for(self, sc: Scenario) -> dict:
        """Defaults overlaid with the scenario's own values for this model."""
        merged = self.default_params(sc)
        for met, vals in (sc.model_params.get(self.id) or {}).items():
            merged.setdefault(met, {}).update(vals)
        return merged

    def simulate(self, sc: Scenario, **kw):
        res = self._module().simulate(sc, params=self.params_for(sc), **kw)
        res.model_id = self.id
        return res


def _split(text: str) -> tuple[dict, str]:
    if text.startswith("---"):
        _, fm, body = text.split("---", 2)
        return (yaml.safe_load(fm) or {}), body.lstrip("\n")
    return {}, text


def discover(root: Path | None = None) -> dict[str, ModelCard]:
    root = Path(root) if root else models_dir()
    cards: dict[str, ModelCard] = {}
    if not root.is_dir():
        return cards
    for folder in sorted(p for p in root.iterdir() if p.is_dir() and (p / "model.py").is_file()):
        for md in sorted(folder.glob("*.md")):
            fm, _ = _split(md.read_text(encoding="utf-8"))
            if not fm.get("id"):
                continue
            spec = (folder / fm["spec"]).resolve() if fm.get("spec") else md
            cards[fm["id"]] = ModelCard(
                id=fm["id"], name=fm.get("name", fm["id"]), version=str(fm.get("version", "?")),
                status=fm.get("status", "development"), summary=fm.get("summary", ""), folder=folder,
                spec_file=spec, parameters=fm.get("parameters") or {}, order=int(fm.get("order", 100)))
            break
    return dict(sorted(cards.items(), key=lambda kv: (kv[1].order, kv[0])))


def get(model_id: str | None = None) -> ModelCard:
    cards = discover()
    if model_id in cards:
        return cards[model_id]
    return cards.get(DEFAULT_ID) or next(iter(cards.values()))
