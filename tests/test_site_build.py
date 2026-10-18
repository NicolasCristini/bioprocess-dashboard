"""The static site: self-contained, CSP inside the page, works under a sub-path."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not (ROOT / "web" / "vendor" / "pyodide" / "pyodide.mjs").exists(),
                                reason="runtime not vendored (python3 scripts/vendor_runtime.py)")


def test_build_static_site(tmp_path):
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_site import CSP, build

    out = build("/some-repo/", tmp_path / "dist")
    page = (out / "index.html").read_text()
    assert f'content="{CSP}"' in page and '<base href="/some-repo/" />' in page
    assert "{{" not in page
    cfg = (out / "theme" / "config.toml").read_text()
    sys.path.insert(0, str(ROOT / "app"))
    from ui import tokens
    assert f'primaryColor = "{tokens.ACCENT}"' in cfg and 'buttonRadius = "full"' in cfg and "[server]" not in cfg
    assert ".streamlit/config.toml" in json.loads((out / "manifest.json").read_text())
    assert (out / "app" / "static" / "fonts" / "Geist-Variable.woff2").is_file()
    assert (out / "404.html").read_text() == page                      # deep links load the app on static hosts
    assert "connect-src 'self' blob: data:" in CSP and "https:" not in CSP  # nothing may leave the browser
    files = json.loads((out / "manifest.json").read_text())
    assert "app/Home.py" in files and "src/bioprocess/simulate.py" in files
    assert {"models/v1-baseline/model.py", "models/v2-monod/MODEL2.md", "MODEL.md"} <= set(files)
    assert all((out / f).is_file() for f in files if f != ".streamlit/config.toml")
    import re
    stl = re.search(r"streamlitConfig: (\{.*?\}),", page).group(1)
    assert all(not isinstance(v, (list, dict)) for v in json.loads(stl).values())   # stlite accepts primitives only
    assert not any("__pycache__" in f for f in files)
    assert (out / "vendor" / "pyodide" / "pyodide.mjs").is_file() and (out / ".nojekyll").exists()
    assert "Content-Security-Policy" in (out / "spike" / "index.html").read_text()
    # every absolute URL in the page shell is relative to the base (works under any sub-path)
    assert 'src="/' not in page and 'href="/vendor' not in page


def test_bad_base_rejected(tmp_path):
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_site import build
    with pytest.raises(SystemExit):
        build("no-slashes", tmp_path / "d")


def test_native_theme_config_in_sync():
    import subprocess
    import sys
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "sync_theme.py"), "--check"])
    assert r.returncode == 0, "run python3 scripts/sync_theme.py after changing app/ui/tokens.py"
