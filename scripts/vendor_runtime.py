"""Download the pinned in-browser runtime into web/vendor/ so the app runs fully offline.

usage: python3 scripts/vendor_runtime.py      (stdlib only; needs npm for the two npm packages)

web/vendor/stlite/   @stlite/browser build (no source maps)
web/vendor/pyodide/  Pyodide core + the prebuilt wheels listed in web/vendor.json (sha256-checked)
web/vendor/pypi/     pure-Python wheels from PyPI listed in web/vendor.json (sha256-checked)
"""
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "web" / "vendor"
CFG = json.loads((ROOT / "web" / "vendor.json").read_text())


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def fetch(url: str, dest: Path, sha256: str | None = None) -> None:
    if dest.exists() and (sha256 is None or hashlib.sha256(dest.read_bytes()).hexdigest() == sha256):
        return
    with urllib.request.urlopen(url) as r:
        data = r.read()
    if sha256 and hashlib.sha256(data).hexdigest() != sha256:
        raise SystemExit(f"sha256 mismatch for {url}")
    dest.write_bytes(data)


def npm_unpack(spec: str, dest: Path, skip=(".map", ".html", ".d.ts")) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = subprocess.run(["npm", "pack", spec, "--silent"], cwd=tmp, check=True,
                             capture_output=True, text=True).stdout.strip().splitlines()[-1]
        with tarfile.open(Path(tmp) / out) as t:
            t.extractall(tmp, filter="data")
        src = Path(tmp) / "package"
        src = src / "build" if (src / "build").is_dir() else src
        shutil.rmtree(dest, ignore_errors=True)
        shutil.copytree(src, dest, ignore=lambda d, names: [n for n in names if n.endswith(skip)])


def main() -> None:
    VENDOR.mkdir(parents=True, exist_ok=True)

    npm_unpack(f"@stlite/browser@{CFG['stlite']}", VENDOR / "stlite")
    print("stlite", CFG["stlite"])

    pyo = VENDOR / "pyodide"
    npm_unpack(f"pyodide@{CFG['pyodide']}", pyo)
    lock = json.loads((pyo / "pyodide-lock.json").read_text())["packages"]
    by_norm = {norm(k): v for k, v in lock.items()}
    todo, done = [norm(n) for n in CFG["pyodide_packages"]], set()
    while todo:
        n = todo.pop()
        if n in done:
            continue
        if n not in by_norm:
            raise SystemExit(f"{n} is not in pyodide-lock.json")
        done.add(n)
        todo += [norm(d) for d in by_norm[n]["depends"]]
    base = f"https://cdn.jsdelivr.net/pyodide/v{CFG['pyodide']}/full/"
    for n in sorted(done):
        p = by_norm[n]
        fetch(base + p["file_name"], pyo / p["file_name"], p["sha256"])
    print("pyodide", CFG["pyodide"], f"+ {len(done)} packages")

    pypi = VENDOR / "pypi"
    pypi.mkdir(exist_ok=True)
    wheels = []
    for name, ver in CFG["pypi"].items():
        meta = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{name}/{ver}/json"))
        whl = next((u for u in meta["urls"] if u["filename"].endswith("-none-any.whl")), None)
        if whl is None:
            raise SystemExit(f"no pure-Python wheel for {name}=={ver}")
        fetch(whl["url"], pypi / whl["filename"], whl["digests"]["sha256"])
        wheels.append(whl["filename"])
    (pypi / "wheels.json").write_text(json.dumps(sorted(wheels), indent=1))
    print("pypi", len(wheels), "wheels")
    total = sum(f.stat().st_size for f in VENDOR.rglob("*") if f.is_file())
    print(f"web/vendor total: {total / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
