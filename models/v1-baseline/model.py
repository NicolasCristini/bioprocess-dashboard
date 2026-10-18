"""v1.1 baseline: the shared core simulation (MODEL.md). No model-specific parameters."""
from bioprocess.simulate import simulate as _core


def simulate(scenario, params=None, **kw):
    return _core(scenario, **kw)
