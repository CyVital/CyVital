"""Shared pytest configuration for the CyVital plot-module test suite.

Sets up:
- Non-interactive Agg backend (must happen before any matplotlib import).
- sys.path entries so bare-module imports used by ECGPlot, EMGPlot, etc. resolve.
- A stub for the 'dwfpy' hardware library so EMGPlot can be imported in CI.
- A MockEvent helper used across several test modules.
- An autouse fixture that closes all Matplotlib figures after every test.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# 1. Force non-interactive backend BEFORE matplotlib is imported anywhere.
# ---------------------------------------------------------------------------
os.environ["MPLBACKEND"] = "Agg"

# ---------------------------------------------------------------------------
# 2. Extend sys.path so both styles of imports work:
#    - src/plots is needed by modules that do `from PlotManager import …`
#    - src is needed by RespiratoryPlot which does `from .PlotManager import …`
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SRC_PLOTS = os.path.join(_REPO_ROOT, "src", "plots")
_SRC_ROOT = os.path.join(_REPO_ROOT, "src")

for _path in (_SRC_PLOTS, _SRC_ROOT):
    if _path not in sys.path:
        sys.path.insert(0, _path)

# ---------------------------------------------------------------------------
# 3. Stub out hardware-only dependency used by EMGPlot.
# ---------------------------------------------------------------------------
sys.modules.setdefault("dwfpy", MagicMock())

# ---------------------------------------------------------------------------
# 4. Now it's safe to import matplotlib and pytest helpers.
# ---------------------------------------------------------------------------
import matplotlib  # noqa: E402
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class MockEvent:
    """Minimal stand-in for a Matplotlib mouse/scroll event."""

    def __init__(
        self,
        button=1,
        inaxes=None,
        xdata: float = 1.0,
        ydata: float = 0.5,
        name: str = "scroll_event",
        key: str | None = None,
    ):
        self.button = button
        self.inaxes = inaxes
        self.xdata = xdata
        self.ydata = ydata
        self.name = name
        self.key = key
        self.step = 1


# Make MockEvent importable from conftest directly.
@pytest.fixture
def mock_event_cls():
    return MockEvent


# ---------------------------------------------------------------------------
# Autouse: close all figures after every test to avoid resource leaks.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def close_all_figures():
    yield
    plt.close("all")
