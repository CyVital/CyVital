"""Tests for PlotManager – selection, zoom, save_data, events."""

from __future__ import annotations

import numpy as np
import pytest
from matplotlib.patches import Rectangle
from unittest.mock import MagicMock, patch

from conftest import MockEvent
from PlotManager import PlotManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager_with_ax():
    """Return a (PlotManager, ax) pair with a real Matplotlib figure/axes."""
    import matplotlib.pyplot as plt

    pm = PlotManager()
    fig, ax = plt.subplots()
    ax.set_xlim(0, 10)
    ax.set_ylim(-1, 1)
    return pm, ax


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

class TestInit:
    def test_initial_state(self):
        pm = PlotManager()
        assert pm.selected_samples == []
        assert pm.selected_times == []
        assert pm.selection_start is None
        assert pm.selection_rect is None


# ---------------------------------------------------------------------------
# zoom_around_cursor
# ---------------------------------------------------------------------------

class TestZoomAroundCursor:
    def setup_method(self):
        self.pm, self.ax = _make_manager_with_ax()

    def _capture_and_register(self):
        """Call zoom_around_cursor and return the scroll callback directly."""
        captured = {}
        orig_connect = self.ax.figure.canvas.mpl_connect

        def spy(event_name, cb):
            if event_name == "scroll_event":
                captured["cb"] = cb
            return orig_connect(event_name, cb)

        with patch.object(self.ax.figure.canvas, "mpl_connect", side_effect=spy):
            self.pm.zoom_around_cursor(self.ax)

        return captured.get("cb")

    def test_returns_none(self):
        result = self.pm.zoom_around_cursor(self.ax)
        assert result is None  # currently returns None (connects callback)

    def test_scroll_up_zooms_in(self):
        cb = self._capture_and_register()
        original_xlim = self.ax.get_xlim()

        event = MockEvent(button="up", inaxes=self.ax, xdata=5.0)
        cb(event)
        new_xlim = self.ax.get_xlim()
        assert (new_xlim[1] - new_xlim[0]) < (original_xlim[1] - original_xlim[0])

    def test_scroll_down_zooms_out(self):
        cb = self._capture_and_register()
        original_xlim = self.ax.get_xlim()

        event = MockEvent(button="down", inaxes=self.ax, xdata=5.0)
        cb(event)
        new_xlim = self.ax.get_xlim()
        assert (new_xlim[1] - new_xlim[0]) > (original_xlim[1] - original_xlim[0])

    def test_scroll_outside_axes_ignored(self):
        cb = self._capture_and_register()
        original_xlim = self.ax.get_xlim()

        event = MockEvent(button="up", inaxes=None, xdata=5.0)
        cb(event)
        assert self.ax.get_xlim() == original_xlim

    def test_scroll_other_button_no_change(self):
        cb = self._capture_and_register()
        original_xlim = self.ax.get_xlim()

        event = MockEvent(button="middle", inaxes=self.ax, xdata=5.0)
        cb(event)
        assert self.ax.get_xlim() == pytest.approx(original_xlim, abs=1e-9)


# ---------------------------------------------------------------------------
# on_press
# ---------------------------------------------------------------------------

class TestOnPress:
    def setup_method(self):
        self.pm, self.ax = _make_manager_with_ax()

    def test_button1_in_axes_sets_start(self):
        event = MockEvent(button=1, inaxes=self.ax, xdata=3.0)
        self.pm.on_press(event, self.ax)
        assert self.pm.selection_start == 3.0

    def test_button1_in_axes_clears_existing_rect(self):
        import matplotlib.pyplot as plt

        fig = self.ax.figure
        rect = Rectangle((0, -1), 2, 2)
        self.ax.add_patch(rect)
        self.pm.selection_rect = rect

        event = MockEvent(button=1, inaxes=self.ax, xdata=3.0)
        self.pm.on_press(event, self.ax)
        assert self.pm.selection_rect is None

    def test_button1_outside_axes_does_not_set_start(self):
        event = MockEvent(button=1, inaxes=None, xdata=3.0)
        self.pm.on_press(event, self.ax)
        assert self.pm.selection_start is None

    def test_other_button_with_rect_removes_rect(self):
        rect = Rectangle((0, -1), 2, 2)
        self.ax.add_patch(rect)
        self.pm.selection_rect = rect

        event = MockEvent(button=3, inaxes=self.ax, xdata=3.0)
        self.pm.on_press(event, self.ax)
        assert self.pm.selection_rect is None

    def test_other_button_without_rect_is_noop(self):
        event = MockEvent(button=3, inaxes=self.ax, xdata=3.0)
        # Should not raise even when selection_rect is None
        self.pm.on_press(event, self.ax)
        assert self.pm.selection_rect is None


# ---------------------------------------------------------------------------
# on_release
# ---------------------------------------------------------------------------

class TestOnRelease:
    def setup_method(self):
        self.pm, self.ax = _make_manager_with_ax()
        self.time = np.linspace(0, 10, 100)
        self.samples = np.random.default_rng(0).random(100)

    def test_in_axes_with_start_creates_rect(self):
        self.pm.selection_start = 2.0
        event = MockEvent(button=1, inaxes=self.ax, xdata=6.0)
        mask = self.pm.on_release(event, self.ax, self.time, self.samples)
        assert self.pm.selection_rect is not None
        assert mask is not None

    def test_selection_data_extracted_correctly(self):
        self.pm.selection_start = 3.0
        event = MockEvent(button=1, inaxes=self.ax, xdata=7.0)
        self.pm.on_release(event, self.ax, self.time, self.samples)
        assert len(self.pm.selected_times) > 0
        assert all((t >= 3.0) and (t <= 7.0) for t in self.pm.selected_times)

    def test_out_of_axes_returns_none(self):
        self.pm.selection_start = 2.0
        event = MockEvent(button=1, inaxes=None, xdata=6.0)
        result = self.pm.on_release(event, self.ax, self.time, self.samples)
        assert result is None

    def test_no_start_returns_none(self):
        event = MockEvent(button=1, inaxes=self.ax, xdata=6.0)
        result = self.pm.on_release(event, self.ax, self.time, self.samples)
        assert result is None


# ---------------------------------------------------------------------------
# on_scroll
# ---------------------------------------------------------------------------

class TestOnScroll:
    def setup_method(self):
        self.pm, self.ax = _make_manager_with_ax()

    def test_removes_rect_if_present(self):
        rect = Rectangle((0, -1), 2, 2)
        self.ax.add_patch(rect)
        self.pm.selection_rect = rect

        event = MockEvent(button="up")
        self.pm.on_scroll(event)
        assert self.pm.selection_rect is None

    def test_no_rect_is_noop(self):
        event = MockEvent(button="up")
        self.pm.on_scroll(event)  # should not raise
        assert self.pm.selection_rect is None


# ---------------------------------------------------------------------------
# save_data
# ---------------------------------------------------------------------------

class TestSaveData:
    def test_save_data_writes_file(self, tmp_path, monkeypatch):
        pm = PlotManager()
        pm.selected_samples = np.array([1.0, 2.0, 3.0])
        pm.selected_times = np.array([0.1, 0.2, 0.3])

        monkeypatch.setattr(
            PlotManager,
            "_prepare_export_path",
            lambda self, filename: tmp_path / filename,
        )
        dest = pm.save_data("test_output.xlsx")
        assert dest.endswith("test_output.xlsx")
        assert (tmp_path / "test_output.xlsx").exists()

    def test_save_data_empty_selection(self, tmp_path, monkeypatch):
        pm = PlotManager()
        monkeypatch.setattr(
            PlotManager,
            "_prepare_export_path",
            lambda self, filename: tmp_path / filename,
        )
        dest = pm.save_data("empty.xlsx")
        assert (tmp_path / "empty.xlsx").exists()
