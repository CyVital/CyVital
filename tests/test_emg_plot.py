"""Tests for EMGPlot – setup, update_plot, filters, events, shift window."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# dwfpy is stubbed in conftest.py before this import
from conftest import MockEvent
from EMGPlot import EMGPlot
from PlotManager import PlotManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_samples(n: int = 2048, fs: int = 4000) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(7)
    t = np.linspace(0.0, n / fs, n)
    s = rng.normal(0.0, 0.01, n).astype(float)
    return t, s


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

class TestSetup:
    def test_axes_created(self):
        emg = EMGPlot()
        assert emg.ax_raw is not None
        assert emg.ax_env is not None

    def test_lines_created(self):
        emg = EMGPlot()
        assert emg.line_raw is not None
        assert emg.line_env is not None

    def test_figure_title(self):
        emg = EMGPlot()
        assert "EMG" in emg.fig._suptitle.get_text()

    def test_initial_buffers_empty(self):
        emg = EMGPlot()
        assert emg.raw_time_vals == []
        assert emg.raw_vals == []
        assert emg.env_time_vals == []
        assert emg.env_vals == []


# ---------------------------------------------------------------------------
# update_plot
# ---------------------------------------------------------------------------

class TestUpdatePlot:
    def setup_method(self):
        self.emg = EMGPlot()

    def test_returns_two_artists(self):
        t, s = _make_samples()
        result = self.emg.update_plot(t, s)
        assert len(result) == 2

    def test_raw_line_data_set(self):
        t, s = _make_samples()
        self.emg.update_plot(t, s)
        xdata, _ = self.emg.line_raw.get_data()
        assert len(xdata) == len(t)

    def test_env_line_data_set(self):
        t, s = _make_samples()
        self.emg.update_plot(t, s)
        xdata, _ = self.emg.line_env.get_data()
        assert len(xdata) > 0

    def test_raw_buffers_populated(self):
        t, s = _make_samples()
        self.emg.update_plot(t, s)
        assert len(self.emg.raw_time_vals) == len(t)
        assert len(self.emg.raw_vals) == len(s)

    def test_env_buffers_populated(self):
        t, s = _make_samples()
        self.emg.update_plot(t, s)
        assert len(self.emg.env_time_vals) == 1
        assert len(self.emg.env_vals) == 1

    def test_env_time_is_last_t_sample(self):
        t, s = _make_samples()
        self.emg.update_plot(t, s)
        assert self.emg.env_time_vals[-1] == t[-1]

    def test_xlim_set_raw(self):
        t, s = _make_samples()
        self.emg.update_plot(t, s)
        xlim = self.emg.ax_raw.get_xlim()
        assert xlim[0] == pytest.approx(t[0], abs=1e-9)
        assert xlim[1] == pytest.approx(t[-1], abs=1e-9)

    def test_env_xlim_less_than_window_size(self):
        """When we have fewer than window_size env points, uses first/last."""
        t, s = _make_samples()
        self.emg.update_plot(t, s)
        # Only one point, so IndexError path is taken → still sets xlim
        xlim = self.emg.ax_env.get_xlim()
        assert xlim[0] == xlim[1] or xlim[0] <= xlim[1]

    def test_env_xlim_with_many_updates(self):
        """With > window_size updates the rolling window xlim is used."""
        n = 2048
        fs = 4000
        rng = np.random.default_rng(99)
        for i in range(self.emg.window_size + 2):
            t = np.linspace(i * n / fs, (i + 1) * n / fs, n)
            s = rng.normal(0.0, 0.01, n)
            self.emg.update_plot(t, s)
        xlim = self.emg.ax_env.get_xlim()
        assert xlim[1] > xlim[0]


# ---------------------------------------------------------------------------
# plot_all
# ---------------------------------------------------------------------------

class TestPlotAll:
    def test_sets_raw_and_env_data(self):
        emg = EMGPlot()
        t, s = _make_samples()
        emg.update_plot(t, s)
        emg.plot_all()
        xdata, _ = emg.line_raw.get_data()
        assert list(xdata) == list(emg.raw_time_vals)


# ---------------------------------------------------------------------------
# shift_review_window
# ---------------------------------------------------------------------------

class TestShiftReviewWindow:
    def test_shift_right(self):
        emg = EMGPlot()
        old_raw = emg.ax_raw.get_xlim()
        result = emg.shift_review_window(1)
        assert result is True
        new_raw = emg.ax_raw.get_xlim()
        assert new_raw[0] > old_raw[0]

    def test_shift_left(self):
        emg = EMGPlot()
        old_raw = emg.ax_raw.get_xlim()
        result = emg.shift_review_window(-1)
        assert result is True
        assert emg.ax_raw.get_xlim()[0] < old_raw[0]

    def test_both_axes_shifted(self):
        emg = EMGPlot()
        old_env = emg.ax_env.get_xlim()
        emg.shift_review_window(1)
        new_env = emg.ax_env.get_xlim()
        assert new_env[0] > old_env[0]


# ---------------------------------------------------------------------------
# _close_plot
# ---------------------------------------------------------------------------

class TestClosePlot:
    def test_close_does_not_raise(self):
        emg = EMGPlot()
        emg._close_plot()


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

class TestEvents:
    def setup_method(self):
        self.emg = EMGPlot()
        t, s = _make_samples()
        self.emg.update_plot(t, s)
        self.t = t

    def test_on_press_in_axes(self):
        event = MockEvent(button=1, inaxes=self.emg.ax_raw, xdata=0.1)
        self.emg.on_press(event)
        assert self.emg.selection_start == 0.1

    def test_on_press_outside_axes(self):
        event = MockEvent(button=1, inaxes=None, xdata=0.1)
        self.emg.on_press(event)
        assert self.emg.selection_start is None

    def test_on_release_creates_rect(self):
        self.emg.selection_start = float(self.t[10])
        event = MockEvent(button=1, inaxes=self.emg.ax_raw, xdata=float(self.t[200]))
        self.emg.on_release(event)
        assert self.emg.selection_rect is not None


# ---------------------------------------------------------------------------
# Filter helpers
# ---------------------------------------------------------------------------

class TestFilterHelpers:
    def setup_method(self):
        self.emg = EMGPlot()

    def test_butter_bandpass_returns_ba(self):
        b, a = self.emg._butter_bandpass(fs=4000)
        assert len(b) > 0
        assert len(a) > 0

    def test_bandpass_filter_output_shape(self):
        _, s = _make_samples()
        filtered = self.emg._bandpass_filter(s, fs=4000)
        assert filtered.shape == s.shape

    def test_moving_average_output_shape(self):
        _, s = _make_samples()
        rectified = np.abs(s)
        smoothed = self.emg._moving_average(rectified)
        assert smoothed.shape == rectified.shape

    def test_moving_average_values_non_negative(self):
        rng = np.random.default_rng(3)
        data = np.abs(rng.normal(0, 0.01, 2048))
        smoothed = self.emg._moving_average(data)
        assert np.all(smoothed >= 0)
