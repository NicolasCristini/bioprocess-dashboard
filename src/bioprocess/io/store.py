"""Scenario library on a directory: the IndexedDB mount in the browser (/mnt), a local folder natively."""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime
from pathlib import Path

from ..models import Scenario
from .scenario_file import from_text, to_yaml

IN_BROWSER = sys.platform == "emscripten"


def default_dir() -> Path:
    if os.environ.get("BIOPROCESS_STORE"):          # set by web/index.html: the app's IndexedDB mount
        return Path(os.environ["BIOPROCESS_STORE"])
    if IN_BROWSER:
        return Path("/bioprocess-planner/scenarios")
    return Path(__file__).resolve().parents[3] / "scenarios" / "private"


def slug(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip()).strip("-.")
    return (s or "scenario")[:80]


class ScenarioStore:
    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root else default_dir()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, name: str) -> Path:
        return self.root / f"{slug(name)}.yaml"

    def list(self) -> list[dict]:
        out = []
        for f in sorted(self.root.glob("*.yaml")):
            try:
                sc = from_text(f.read_text(encoding="utf-8"))
                name, ok = sc.name, True
            except ValueError:
                name, ok = f.stem, False
            out.append({"name": name, "file": f.name, "ok": ok,
                        "modified": datetime.fromtimestamp(f.stat().st_mtime)})
        return sorted(out, key=lambda d: d["modified"], reverse=True)

    def save(self, sc: Scenario) -> Path:
        p = self.path(sc.name)
        p.write_text(to_yaml(sc), encoding="utf-8")
        return p

    def load(self, file: str) -> Scenario:
        return from_text((self.root / file).read_text(encoding="utf-8"))

    def delete(self, file: str) -> None:
        (self.root / file).unlink(missing_ok=True)

    def clear(self) -> int:
        files = list(self.root.glob("*.yaml"))
        for f in files:
            f.unlink()
        return len(files)

    # ---- working copy: survives reloads and new sessions (not listed with the saved scenarios)
    AUTOSAVE = ".autosave.json"

    def autosave(self, sc: Scenario, meta: dict) -> None:
        import json
        from .scenario_file import to_dict
        (self.root / self.AUTOSAVE).write_text(json.dumps({"meta": meta, "scenario": to_dict(sc)}), encoding="utf-8")

    def restore(self) -> tuple[Scenario, dict] | None:
        import json
        f = self.root / self.AUTOSAVE
        if not f.exists():
            return None
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            return Scenario.model_validate(d["scenario"]), d.get("meta", {})
        except Exception:  # noqa: BLE001 - a corrupt working copy is simply ignored
            return None

    def export_all(self) -> bytes:
        """All scenarios as one zip (backup / move to another browser)."""
        import io
        import zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(self.root.glob("*.yaml")):
                z.write(f, f.name)
        return buf.getvalue()

    def import_zip(self, data: bytes) -> int:
        import io
        import zipfile
        n = 0
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for info in z.infolist():
                if info.filename.endswith((".yaml", ".yml", ".json")) and "/" not in info.filename:
                    sc = from_text(z.read(info).decode("utf-8"))
                    self.save(sc)
                    n += 1
        return n
