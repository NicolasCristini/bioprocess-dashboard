"""Build the static site: dist/ can be served by ANY static host (GitHub Pages, Netlify, a USB stick + any
web server). No server-side logic: the Python runs in the visitor's browser and their data stays there.

usage: python3 scripts/build_site.py [--base /repo-name/] [--out dist]

dist/
  index.html, 404.html     page shell (404.html = same page, so deep links on static hosts still load the app)
  manifest.json            list of Python sources the page mounts
  app/, src/bioprocess/    the Python sources (copied)
  vendor/                  stlite + Pyodide + wheels (from web/vendor, see scripts/vendor_runtime.py)
  spike/                   runtime health-check page
  .nojekyll                GitHub Pages: serve files as-is
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
SOURCES = {"app": ROOT / "app", "src/bioprocess": ROOT / "src" / "bioprocess", "models": ROOT / "models"}

# Only this origin. 'data:' scripts: stlite's worker is an inline data: script (not a network source).
CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' 'wasm-unsafe-eval' blob: data:",
    "worker-src 'self' blob: data:",
    "connect-src 'self' blob: data:",
    "img-src 'self' data: blob:",
    "style-src 'self' 'unsafe-inline'",
    "font-src 'self' data:",
    "frame-src 'self' blob:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'none'",
])


def streamlit_config() -> dict:
    """Primitive settings passed to stlite's mount() (it accepts no lists). The theme travels as a mounted
    .streamlit/config.toml instead (see build)."""
    return {"browser.gatherUsageStats": False, "client.toolbarMode": "minimal"}


def theme_toml() -> str:
    import importlib.util
    spec = importlib.util.spec_from_file_location("sync_theme", ROOT / "scripts" / "sync_theme.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.render(native=False)


def build(base: str = "/", out: Path = ROOT / "dist") -> Path:
    if not base.startswith("/") or not base.endswith("/"):
        raise SystemExit("--base must start and end with '/', e.g. /bioprocess-dashboard/")
    if not (WEB / "vendor" / "pyodide" / "pyodide.mjs").exists():
        raise SystemExit("web/vendor/ is missing: run python3 scripts/vendor_runtime.py first")
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)

    files = []
    for prefix, src in SOURCES.items():
        for p in sorted([*src.rglob("*.py"), *(src.rglob("*.md") if prefix == "models" else [])]):
            if "__pycache__" in p.parts:
                continue
            rel = f"{prefix}/{p.relative_to(src).as_posix()}"
            (out / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, out / rel)
            files.append(rel)
    # theme from app/ui/tokens.py: served as theme/config.toml (no dot-folder, which static hosts may drop),
    # mounted by index.html at .streamlit/config.toml where Streamlit reads it
    (out / "theme").mkdir()
    (out / "theme" / "config.toml").write_text(theme_toml())
    files.append(".streamlit/config.toml")
    # specs referenced by model cards outside models/ (v1-baseline points to the root MODEL.md)
    for doc in ("MODEL.md",):
        shutil.copy2(ROOT / doc, out / doc)
        files.append(doc)
    (out / "manifest.json").write_text(json.dumps(files, indent=1))

    page = (WEB / "index.html").read_text(encoding="utf-8").replace("{{CSP}}", CSP).replace("{{BASE}}", base)
    page = page.replace("{{STREAMLIT_CONFIG}}", json.dumps(streamlit_config()))
    for name in ("index.html", "404.html"):
        (out / name).write_text(page, encoding="utf-8")

    shutil.copytree(ROOT / "app" / "static", out / "app" / "static")     # fonts (OFL), referenced by the theme
    shutil.copytree(WEB / "vendor", out / "vendor")
    spike = (WEB / "spike" / "index.html").read_text(encoding="utf-8")
    (out / "spike").mkdir()
    (out / "spike" / "index.html").write_text(spike.replace("<head>", f'<head>\n  <meta http-equiv="Content-Security-Policy" content="{CSP}" />', 1), encoding="utf-8")
    shutil.copy2(WEB / "spike" / "spike_app.py", out / "spike" / "spike_app.py")
    (out / ".nojekyll").write_text("")
    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"built {out} for base {base}: {len(files)} Python files, {size / 1e6:.0f} MB")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="/")
    ap.add_argument("--out", default=str(ROOT / "dist"))
    a = ap.parse_args()
    build(a.base, Path(a.out))
