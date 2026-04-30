"""Tests for src/Main.py and src/__init__.py.

These tests use importlib to load the files directly so that their
import-time statements are executed and tracked by the coverage tool,
and runpy to exercise the ``if __name__ == "__main__"`` block.
"""

from __future__ import annotations

import importlib.util
import os
import runpy
import sys
from unittest.mock import MagicMock, patch

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_MAIN_PATH = os.path.join(_REPO_ROOT, "src", "Main.py")
_SRC_INIT_PATH = os.path.join(_REPO_ROOT, "src", "__init__.py")


def _load_file(path: str, name: str):
    """Execute *path* as a module (not as __main__) and return the module."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# src/__init__.py
# ---------------------------------------------------------------------------

class TestSrcInit:
    def test_executes_without_error(self):
        """All 3 statements in src/__init__.py run on load."""
        mod = _load_file(_SRC_INIT_PATH, "_src_init_cov")
        assert mod is not None

    def test_has_os_and_sys_in_namespace(self):
        mod = _load_file(_SRC_INIT_PATH, "_src_init_cov2")
        assert hasattr(mod, "os")
        assert hasattr(mod, "sys")


# ---------------------------------------------------------------------------
# src/Main.py – import-time lines (1-6)
# ---------------------------------------------------------------------------

class TestMainImportTime:
    def test_loads_without_error(self):
        """Lines 1-6 (imports + sys.path setup) are covered by loading."""
        mod = _load_file(_MAIN_PATH, "_main_cov_import")
        assert mod is not None

    def test_has_sys_and_os(self):
        mod = _load_file(_MAIN_PATH, "_main_cov_import2")
        assert hasattr(mod, "sys")
        assert hasattr(mod, "os")


# ---------------------------------------------------------------------------
# src/Main.py – __main__ block (lines 7-25)
# ---------------------------------------------------------------------------

class TestMainBlock:
    def test_success_path_calls_gui_main(self):
        """Lines 8-18: gui.tkGui.main() is called when import succeeds."""
        tkgui_mock = MagicMock()
        with patch.dict(sys.modules, {"gui.tkGui": tkgui_mock}):
            runpy.run_path(_MAIN_PATH, run_name="__main__")
        tkgui_mock.main.assert_called_once()

    def test_import_error_path_calls_sys_exit(self):
        """Lines 19-25: sys.exit(1) is called when gui.tkGui cannot be imported."""
        with patch.dict(sys.modules, {"gui.tkGui": None}):
            with patch("sys.exit") as mock_exit:
                runpy.run_path(_MAIN_PATH, run_name="__main__")
        mock_exit.assert_called_once_with(1)

    def test_import_error_path_prints_diagnostic(self, capsys):
        """The except block prints helpful diagnostic messages."""
        with patch.dict(sys.modules, {"gui.tkGui": None}):
            with patch("sys.exit"):
                runpy.run_path(_MAIN_PATH, run_name="__main__")
        out = capsys.readouterr().out
        assert "Critical import error" in out or "Possible solutions" in out
