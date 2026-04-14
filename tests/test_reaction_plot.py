"""Tests for ReactionPlot – setup, update_plot, cue/reaction logic, save_data."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest

from conftest import MockEvent
from ReactionPlot import ReactionPlot
from PlotManager import PlotManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _t_s(n: int = 100, sample_rate: int = 10000) -> tuple[np.ndarray, np.ndarray]:
    """Simple (t_axis, samples) below the voltage threshold (no button press)."""
    t = np.linspace(0.0, n / sample_rate, n)
    s = np.zeros(n, dtype=float) + 0.5  # below threshold of 2 V
    return t, s


def _t_s_button_press(n: int = 100, sample_rate: int = 10000) -> tuple[np.ndarray, np.ndarray]:
    """Samples containing a button press above threshold."""
    t = np.linspace(0.0, n / sample_rate, n)
    s = np.zeros(n, dtype=float) + 0.5
    s[50] = 3.0  # above threshold
    return t, s


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

class TestSetup:
    def test_axes_created(self):
        rp = ReactionPlot()
        assert rp.ax_signal is not None
        assert rp.ax_reaction is not None

    def test_line_created(self):
        rp = ReactionPlot()
        assert rp.line_signal is not None

    def test_cue_text_starts_empty(self):
        rp = ReactionPlot()
        assert rp.cue_text.get_text() == ""

    def test_initial_buffers_empty(self):
        rp = ReactionPlot()
        assert rp.reaction_times == []
        assert rp.full_time == []
        assert rp.full_samples == []
        assert rp.raw_time == []
        assert rp.raw_samples == []

    def test_cue_inactive_at_start(self):
        rp = ReactionPlot()
        assert rp.cue_active is False


# ---------------------------------------------------------------------------
# update_plot – no cue, no button press
# ---------------------------------------------------------------------------

class TestUpdatePlotNoCue:
    def setup_method(self):
        self.rp = ReactionPlot()
        # Freeze time so the cue delay never fires during tests
        self._time_patcher = patch(
            "ReactionPlot.time.time", return_value=0.0
        )
        self._time_patcher.start()
        # Set last_cue_time to "now" so the delay condition is never met
        self.rp.last_cue_time = 0.0
        self.rp.random_delay = 9999.0

    def teardown_method(self):
        self._time_patcher.stop()

    def test_returns_two_artists(self):
        t, s = _t_s()
        result = self.rp.update_plot(t, s)
        assert len(result) == 2

    def test_full_time_extended(self):
        t, s = _t_s()
        self.rp.update_plot(t, s)
        assert len(self.rp.full_time) == len(t)

    def test_full_samples_extended(self):
        t, s = _t_s()
        self.rp.update_plot(t, s)
        assert len(self.rp.full_samples) == len(t)

    def test_raw_time_extended(self):
        t, s = _t_s()
        self.rp.update_plot(t, s)
        assert len(self.rp.raw_time) == len(t)

    def test_consecutive_calls_offset_time(self):
        t, s = _t_s()
        self.rp.update_plot(t, s)
        total_first = len(self.rp.full_time)
        self.rp.update_plot(t, s)
        assert len(self.rp.full_time) == total_first * 2

    def test_no_reaction_recorded(self):
        t, s = _t_s()
        self.rp.update_plot(t, s)
        assert len(self.rp.reaction_times) == 0

    def test_signal_line_data_set(self):
        t, s = _t_s()
        self.rp.update_plot(t, s)
        xdata, _ = self.rp.line_signal.get_data()
        assert len(xdata) > 0

    def test_xlim_set(self):
        t, s = _t_s()
        self.rp.update_plot(t, s)
        xlim = self.rp.ax_signal.get_xlim()
        assert xlim[1] > xlim[0]


# ---------------------------------------------------------------------------
# update_plot – cue triggers
# ---------------------------------------------------------------------------

class TestCueLogic:
    def test_cue_activates_when_delay_elapsed(self):
        rp = ReactionPlot()
        # Simulate time advancing so delay has passed
        rp.last_cue_time = 0.0
        rp.random_delay = 1.0
        rp.cue_active = False

        t, s = _t_s()
        with patch("ReactionPlot.time.time", return_value=5.0):
            with patch("ReactionPlot.random.uniform", return_value=3.0):
                rp.update_plot(t, s)

        assert rp.cue_active is True
        assert rp.cue_text.get_text() == "GO!"

    def test_reaction_recorded_when_button_pressed_during_cue(self):
        rp = ReactionPlot()
        t, s = _t_s()

        # First call: activate cue
        rp.last_cue_time = 0.0
        rp.random_delay = 1.0
        with patch("ReactionPlot.time.time", return_value=5.0):
            with patch("ReactionPlot.random.uniform", return_value=3.0):
                rp.update_plot(t, s)

        assert rp.cue_active is True

        # Second call: button press above threshold
        t2, s2 = _t_s_button_press()
        with patch("ReactionPlot.time.time", return_value=5.1):
            with patch("ReactionPlot.random.uniform", return_value=3.0):
                rp.update_plot(t2, s2)

        assert len(rp.reaction_times) == 1
        assert rp.cue_active is False

    def test_reaction_time_is_positive(self):
        rp = ReactionPlot()
        rp.last_cue_time = 0.0
        rp.random_delay = 1.0
        t, s = _t_s()

        with patch("ReactionPlot.time.time", return_value=5.0):
            with patch("ReactionPlot.random.uniform", return_value=3.0):
                rp.update_plot(t, s)

        t2, s2 = _t_s_button_press()
        with patch("ReactionPlot.time.time", return_value=5.2):
            with patch("ReactionPlot.random.uniform", return_value=3.0):
                rp.update_plot(t2, s2)

        assert rp.reaction_times[0] > 0

    def test_cue_text_updated_after_reaction(self):
        rp = ReactionPlot()
        rp.last_cue_time = 0.0
        rp.random_delay = 1.0
        t, s = _t_s()

        with patch("ReactionPlot.time.time", return_value=5.0):
            with patch("ReactionPlot.random.uniform", return_value=3.0):
                rp.update_plot(t, s)

        t2, s2 = _t_s_button_press()
        with patch("ReactionPlot.time.time", return_value=5.15):
            with patch("ReactionPlot.random.uniform", return_value=3.0):
                rp.update_plot(t2, s2)

        assert "Reaction" in rp.cue_text.get_text()


# ---------------------------------------------------------------------------
# update_plot – window size edge case
# ---------------------------------------------------------------------------

class TestWindowEdgeCase:
    def test_large_accumulation_triggers_index_exception_path(self):
        """Fill beyond window_size to exercise the try/except IndexError paths."""
        rp = ReactionPlot()
        rp.last_cue_time = 0.0
        rp.random_delay = 9999.0
        n = 100
        total_calls = rp.window_size // n + 2
        with patch("ReactionPlot.time.time", return_value=0.0):
            for i in range(total_calls):
                t = np.linspace(0.0, n / rp.sample_rate, n)
                s = np.zeros(n) + 0.5
                rp.update_plot(t, s)
        assert len(rp.full_time) > rp.window_size


# ---------------------------------------------------------------------------
# shift_review_window
# ---------------------------------------------------------------------------

class TestShiftReviewWindow:
    def test_shift_right_returns_true(self):
        rp = ReactionPlot()
        old_lim = rp.ax_signal.get_xlim()
        result = rp.shift_review_window(1)
        assert result is True
        assert rp.ax_signal.get_xlim()[0] > old_lim[0]

    def test_shift_left(self):
        rp = ReactionPlot()
        old_lim = rp.ax_signal.get_xlim()
        rp.shift_review_window(-1)
        assert rp.ax_signal.get_xlim()[0] < old_lim[0]


# ---------------------------------------------------------------------------
# plot_all
# ---------------------------------------------------------------------------

class TestPlotAll:
    def test_sets_full_data(self):
        rp = ReactionPlot()
        with patch("ReactionPlot.time.time", return_value=0.0):
            t, s = _t_s()
            rp.last_cue_time = 0.0
            rp.random_delay = 9999.0
            rp.update_plot(t, s)
        rp.plot_all()
        xdata, _ = rp.line_signal.get_data()
        assert list(xdata) == rp.full_time


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

class TestEvents:
    def setup_method(self):
        self.rp = ReactionPlot()
        with patch("ReactionPlot.time.time", return_value=0.0):
            self.rp.last_cue_time = 0.0
            self.rp.random_delay = 9999.0
            t, s = _t_s()
            self.rp.update_plot(t, s)
        self.t = self.rp.full_time

    def test_on_press_in_axes(self):
        event = MockEvent(button=1, inaxes=self.rp.ax_signal, xdata=0.001)
        self.rp.on_press(event)
        assert self.rp.selection_start == 0.001

    def test_on_press_outside_axes(self):
        event = MockEvent(button=1, inaxes=None, xdata=0.001)
        self.rp.on_press(event)
        # selection_start was set to 0 in _setup_plot, so stays 0 (no change)
        assert self.rp.selection_start == 0

    def test_on_release_creates_rect(self):
        self.rp.selection_start = float(self.t[5])
        event = MockEvent(button=1, inaxes=self.rp.ax_signal, xdata=float(self.t[50]))
        self.rp.on_release(event)
        assert self.rp.selection_rect is not None


# ---------------------------------------------------------------------------
# save_data
# ---------------------------------------------------------------------------

class TestSaveData:
    def _make_rp_with_data(self) -> ReactionPlot:
        rp = ReactionPlot()
        rp.last_cue_time = 0.0
        rp.random_delay = 9999.0
        with patch("ReactionPlot.time.time", return_value=0.0):
            t, s = _t_s()
            rp.update_plot(t, s)
        return rp

    def test_save_data_no_reaction_no_selection(self, tmp_path, monkeypatch):
        rp = self._make_rp_with_data()
        rp.selected_samples = np.array([])
        rp.selected_times = np.array([])
        monkeypatch.setattr(
            PlotManager,
            "_prepare_export_path",
            lambda self, filename: tmp_path / filename,
        )
        dest = rp.save_data("reaction.xlsx")
        assert (tmp_path / "reaction.xlsx").exists()
        assert dest.endswith("reaction.xlsx")

    def test_save_data_with_reactions(self, tmp_path, monkeypatch):
        rp = self._make_rp_with_data()
        rp.reaction_times = [120.5, 98.3]
        rp.trial_timestamps = [0.01, 0.02]
        rp.selected_samples = np.array([])
        rp.selected_times = np.array([])
        monkeypatch.setattr(
            PlotManager,
            "_prepare_export_path",
            lambda self, filename: tmp_path / filename,
        )
        rp.save_data("reaction_with.xlsx")
        assert (tmp_path / "reaction_with.xlsx").exists()

    def test_save_data_with_selection(self, tmp_path, monkeypatch):
        rp = self._make_rp_with_data()
        rp.reaction_times = [100.0]
        rp.trial_timestamps = [0.01]
        rp.selected_samples = np.array([1.0, 2.0])
        rp.selected_times = np.array([0.1, 0.2])
        monkeypatch.setattr(
            PlotManager,
            "_prepare_export_path",
            lambda self, filename: tmp_path / filename,
        )
        rp.save_data("reaction_sel.xlsx")
        assert (tmp_path / "reaction_sel.xlsx").exists()


# ---------------------------------------------------------------------------
# _close_plot
# ---------------------------------------------------------------------------

class TestClosePlot:
    def test_close_does_not_raise(self):
        rp = ReactionPlot()
        rp._close_plot()
