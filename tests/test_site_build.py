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
    assert (out / "404.html").read_text() == page                      # deep links load the app on static hosts
    assert "connect-src 'self' blob: data:" in CSP and "https:" not in CSP  # nothing may leave the browser
    files = json.loads((out / "manifest.json").read_text())
    assert "app/Home.py" in files and "src/bioprocess/simulate.py" in files
    assert all((out / f).is_file() for f in files)
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
