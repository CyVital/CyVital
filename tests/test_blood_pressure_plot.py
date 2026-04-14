"""Tests for BloodPressurePlot – setup, update_plot, pressure calc, events."""

from __future__ import annotations

import numpy as np
import pytest

from conftest import MockEvent
from BloodPressurePlot import BloodPressurePlot
from PlotManager import PlotManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_samples(n: int = 200) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(13)
    t = np.linspace(0.0, n / 1000.0, n)
    s = rng.uniform(0.0, 1.0, n)
    return t, s


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

class TestSetup:
    def test_axes_created(self):
        bp = BloodPressurePlot()
        assert bp.ax_raw is not None
        assert bp.ax_pressure is not None

    def test_lines_created(self):
        bp = BloodPressurePlot()
        assert bp.line_raw is not None
        assert bp.line_pressure is not None

    def test_raw_axis_ylim(self):
        bp = BloodPressurePlot()
        assert bp.ax_raw.get_ylim() == (0.0, 1.0)

    def test_pressure_axis_ylim(self):
        bp = BloodPressurePlot()
        assert bp.ax_pressure.get_ylim() == (0.0, 200.0)

    def test_initial_buffers_empty(self):
        bp = BloodPressurePlot()
        assert bp.full_times == []
        assert bp.raw_volts == []
        assert bp.pressures == []


# ---------------------------------------------------------------------------
# update_plot
# ---------------------------------------------------------------------------

class TestUpdatePlot:
    def setup_method(self):
        self.bp = BloodPressurePlot()

    def test_returns_two_artists(self):
        t, s = _make_samples()
        result = self.bp.update_plot(t, s)
        assert len(result) == 2

    def test_raw_line_data_set(self):
        t, s = _make_samples()
        self.bp.update_plot(t, s)
        xdata, ydata = self.bp.line_raw.get_data()
        assert len(xdata) == min(len(t), self.bp.window_size)

    def test_pressure_line_data_set(self):
        t, s = _make_samples()
        self.bp.update_plot(t, s)
        xdata, ydata = self.bp.line_pressure.get_data()
        assert len(xdata) == min(len(t), self.bp.window_size)

    def test_buffers_accumulate(self):
        t, s = _make_samples()
        self.bp.update_plot(t, s)
        self.bp.update_plot(t + t[-1], s)
        assert len(self.bp.full_times) == 2 * len(t)

    def test_pressures_calculated(self):
        t, s = _make_samples()
        self.bp.update_plot(t, s)
        assert len(self.bp.pressures) == len(t)

    def test_window_rolling(self):
        """When total samples > window_size, only last window_size shown."""
        rng = np.random.default_rng(5)
        # Accumulate enough to exceed window_size
        for i in range(3):
            t = np.linspace(i * 0.2, (i + 1) * 0.2, 200)
            s = rng.uniform(0.0, 1.0, 200)
            self.bp.update_plot(t, s)
        xdata, _ = self.bp.line_raw.get_data()
        assert len(xdata) <= self.bp.window_size


# ---------------------------------------------------------------------------
# _calc_pressure
# ---------------------------------------------------------------------------

class TestCalcPressure:
    def test_output_length_matches_input(self):
        bp = BloodPressurePlot()
        s = np.array([0.1, 0.5, 1.0])
        result = bp._calc_pressure(s)
        assert len(result) == 3

    def test_linear_scaling_by_m(self):
        bp = BloodPressurePlot()
        bp.m = 2.0
        s = np.array([1.0, 2.0, 3.0])
        result = bp._calc_pressure(s)
        assert result == pytest.approx([2.0, 4.0, 6.0])

    def test_default_m_is_one(self):
        bp = BloodPressurePlot()
        s = np.array([0.5])
        result = bp._calc_pressure(s)
        assert result == pytest.approx([0.5])


# ---------------------------------------------------------------------------
# plot_all
# ---------------------------------------------------------------------------

class TestPlotAll:
    def test_sets_full_data(self):
        bp = BloodPressurePlot()
        t, s = _make_samples()
        bp.update_plot(t, s)
        bp.plot_all()
        xdata, _ = bp.line_raw.get_data()
        assert list(xdata) == bp.full_times

    def test_plot_all_accepts_event_arg(self):
        bp = BloodPressurePlot()
        t, s = _make_samples()
        bp.update_plot(t, s)
        bp.plot_all(event=None)  # event parameter is optional


# ---------------------------------------------------------------------------
# shift_review_window
# ---------------------------------------------------------------------------

class TestShiftReviewWindow:
    def test_shift_right(self):
        bp = BloodPressurePlot()
        old_raw = bp.ax_raw.get_xlim()
        result = bp.shift_review_window(1)
        assert result is True
        assert bp.ax_raw.get_xlim()[0] > old_raw[0]

    def test_shift_left(self):
        bp = BloodPressurePlot()
        old_raw = bp.ax_raw.get_xlim()
        bp.shift_review_window(-1)
        assert bp.ax_raw.get_xlim()[0] < old_raw[0]

    def test_both_axes_shifted(self):
        bp = BloodPressurePlot()
        old_pressure = bp.ax_pressure.get_xlim()
        bp.shift_review_window(1)
        assert bp.ax_pressure.get_xlim()[0] > old_pressure[0]


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

class TestEvents:
    def setup_method(self):
        self.bp = BloodPressurePlot()
        t, s = _make_samples()
        self.bp.update_plot(t, s)
        self.t = t

    def test_on_press_in_axes_sets_start(self):
        event = MockEvent(button=1, inaxes=self.bp.ax_raw, xdata=0.05)
        self.bp.on_press(event)
        assert self.bp.selection_start == 0.05

    def test_on_press_outside_axes(self):
        event = MockEvent(button=1, inaxes=None, xdata=0.05)
        self.bp.on_press(event)
        assert self.bp.selection_start is None

    def test_on_release_creates_rect(self):
        self.bp.selection_start = float(self.t[5])
        event = MockEvent(button=1, inaxes=self.bp.ax_raw, xdata=float(self.t[100]))
        self.bp.on_release(event)
        assert self.bp.selection_rect is not None

    def test_on_release_outside_axes(self):
        self.bp.selection_start = 0.01
        event = MockEvent(button=1, inaxes=None, xdata=0.1)
        self.bp.on_release(event)
        assert self.bp.selection_rect is None


# ---------------------------------------------------------------------------
# _close_plot
# ---------------------------------------------------------------------------

class TestClosePlot:
    def test_close_does_not_raise(self):
        bp = BloodPressurePlot()
        bp._close_plot()
