"""M0 spike: do the model's dependencies load in stlite, and does IndexedDB persist across reloads?"""
import importlib
import io
import json
import pathlib
import sys
import time

import streamlit as st

st.title("stlite spike")
st.write(f"Python {sys.version.split()[0]} · Streamlit {st.__version__}")

results = {}
for mod in ["numpy", "pandas", "plotly", "pydantic", "yaml", "openpyxl"]:
    try:
        m = importlib.import_module(mod)
        results[mod] = getattr(m, "__version__", "ok")
    except Exception as e:  # noqa: BLE001 - spike reports every failure
        results[mod] = f"FAIL: {e!r}"
st.subheader("Imports")
st.json(results)

# exercise each library once
import numpy as np
import openpyxl
import pandas as pd
import plotly.graph_objects as go
import yaml
from pydantic import BaseModel, Field

class Phase(BaseModel):
    days: int = Field(gt=0)
    mu: float

checks = {}
t0 = time.perf_counter()
x = 8e5 * np.exp(0.543 * np.arange(0, 2 + 1 / 24, 1 / 24))
df = pd.DataFrame({"t_h": np.arange(len(x)), "vcc": x})
checks["numpy/pandas hourly rows"] = len(df)
checks["pydantic"] = Phase(days=2, mu=0.543).model_dump()
try:
    Phase(days=0, mu=1)
    checks["pydantic validation"] = "FAIL (no error)"
except Exception:
    checks["pydantic validation"] = "ok (rejected days=0)"
checks["yaml round-trip"] = yaml.safe_load(yaml.safe_dump({"phases": [checks["pydantic"]]}))
wb = openpyxl.Workbook(); wb.active["A1"] = "ok"; buf = io.BytesIO(); wb.save(buf)
checks["openpyxl xlsx bytes"] = len(buf.getvalue())
checks["compute ms"] = round((time.perf_counter() - t0) * 1000, 1)
st.subheader("Library checks")
st.json(checks)
st.plotly_chart(go.Figure(go.Scatter(x=df.t_h, y=df.vcc, name="VCC")), use_container_width=True)
st.download_button("Download test.xlsx", buf.getvalue(), "test.xlsx")

st.subheader("IndexedDB persistence (/mnt)")
f = pathlib.Path("/mnt/spike_counter.json")
data = json.loads(f.read_text()) if f.exists() else {"loads": 0}
data["loads"] += 1
f.write_text(json.dumps(data))
st.metric("Page loads recorded in /mnt", data["loads"])
st.caption("Reload the page: the number must go up if persistence works.")

st.subheader("Where the runtime came from")
src = {}
try:
    import pyodide_js
    src["pyodide indexURL"] = str(pyodide_js._api.config.indexURL)
    src["pyodide version"] = str(pyodide_js.version)
except Exception as e:  # noqa: BLE001
    src["pyodide"] = repr(e)
try:
    import micropip
    pk = micropip.list()
    by_src = {}
    for n, p in pk.items():
        s_ = getattr(p, "source", "?")
        key = "local" if "localhost" in s_ else s_
        by_src.setdefault(key, []).append(f"{n}=={p.version}")
    src["packages_by_source"] = {k: sorted(v) for k, v in by_src.items()}
except Exception as e:  # noqa: BLE001
    src["micropip"] = repr(e)
st.json(src)

# Opt-in (open the page with ?csp-test): prove the page's CSP also binds the Python worker.
if "csp-test" in st.query_params:
    st.subheader("CSP check from inside the Python worker")
    from pyodide.http import pyfetch
    try:
        await pyfetch("https://example.com/")  # noqa: F704 - top-level await is fine in stlite
        st.error("CSP-TEST: external request ALLOWED")
    except Exception as e:  # noqa: BLE001
        st.success(f"CSP-TEST: external request BLOCKED ({type(e).__name__})")
