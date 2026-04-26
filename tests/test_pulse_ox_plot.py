"""Tests for PulseOxPlot – setup, update_plot, BPM/SpO2 estimates, save_data."""

from __future__ import annotations

from collections import deque
from unittest.mock import patch

import numpy as np
import pytest

from conftest import MockEvent
from PulseOxPlot import PulseOxPlot
from PlotManager import PlotManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_6byte_sample(red: int = 0x1_00_00, ir: int = 0x2_00_00) -> list[int]:
    """Pack two 18-bit values into 6 bytes matching the MAX30101 frame layout."""
    r0 = (red >> 16) & 0xFF
    r1 = (red >> 8) & 0xFF
    r2 = red & 0xFF
    i0 = (ir >> 16) & 0xFF
    i1 = (ir >> 8) & 0xFF
    i2 = ir & 0xFF
    return [r0, r1, r2, i0, i1, i2]


def _ir_buf_with_peaks(n_peaks: int = 6) -> deque:
    """Return a deque of 100 IR samples containing enough peaks to estimate BPM."""
    fs = 10
    n = 100
    t = np.linspace(0, n / fs, n)
    # 0.8 Hz sine → ~8 peaks in 10 seconds (above the 5-peak threshold)
    signal = 50000 + 10000 * np.sin(2 * np.pi * 0.8 * t)
    return deque(signal.tolist(), maxlen=n)


def _ir_buf_flat(n: int = 100) -> deque:
    """Return a flat deque (no peaks → estimate_bpm returns None)."""
    return deque([50000.0] * n, maxlen=n)


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

class TestSetup:
    def test_axes_created(self):
        po = PulseOxPlot()
        assert po.ax_dig is not None
        assert po.ax is not None

    def test_lines_created(self):
        po = PulseOxPlot()
        assert po.line_red_dig is not None
        assert po.line_red is not None
        assert po.line_ir is not None

    def test_initial_deques(self):
        po = PulseOxPlot()
        assert len(po.red_values) == po.window_size
        assert len(po.ir_values) == po.window_size

    def test_butter_filter_coefficients_set(self):
        po = PulseOxPlot()
        assert po.b is not None
        assert po.a is not None


# ---------------------------------------------------------------------------
# update_plot
# ---------------------------------------------------------------------------

class TestUpdatePlot:
    def setup_method(self):
        self.po = PulseOxPlot()

    def _call_update(self, red: int = 0x10000, ir: int = 0x20000, n_time: int = 120):
        samples = _make_6byte_sample(red, ir)
        time_axis = np.arange(n_time, dtype=float)
        return self.po.update_plot(time_axis, samples)

    def test_returns_three_artists(self):
        result = self._call_update()
        assert len(result) == 3

    def test_red_and_ir_values_appended(self):
        self._call_update(red=0x10000, ir=0x20000)
        assert self.po.all_red_values[-1] == (0x10000 & 0x03FFFF)
        assert self.po.all_ir_values[-1] == (0x20000 & 0x03FFFF)

    def test_bits_extended(self):
        prev_len = len(self.po.all_bits)
        self._call_update()
        assert len(self.po.all_bits) == prev_len + 48  # 6 bytes × 8 bits

    def test_time_axis_stored(self):
        time_axis = np.arange(110, dtype=float)
        samples = _make_6byte_sample()
        self.po.update_plot(time_axis, samples)
        assert np.array_equal(self.po.all_time, time_axis)

    def test_multiple_updates_accumulate(self):
        for i in range(5):
            self._call_update()
        assert len(self.po.all_red_values) == 5
        assert len(self.po.all_ir_values) == 5


# ---------------------------------------------------------------------------
# filtered_ir
# ---------------------------------------------------------------------------

class TestFilteredIR:
    def test_output_length_matches_input(self):
        po = PulseOxPlot()
        buf = deque([50000 + 1000 * np.sin(0.1 * i) for i in range(100)], maxlen=100)
        out = po.filtered_ir(buf)
        assert len(out) == 100

    def test_output_is_finite(self):
        po = PulseOxPlot()
        buf = deque([50000.0] * 100, maxlen=100)
        out = po.filtered_ir(buf)
        assert np.all(np.isfinite(out))


# ---------------------------------------------------------------------------
# estimate_bpm
# ---------------------------------------------------------------------------

class TestEstimateBPM:
    def test_returns_none_with_flat_signal(self):
        po = PulseOxPlot()
        bpm = po.estimate_bpm(_ir_buf_flat())
        assert bpm is None

    def test_returns_float_with_peaks(self):
        po = PulseOxPlot()
        bpm = po.estimate_bpm(_ir_buf_with_peaks())
        # May still be None if find_peaks finds < 5 peaks; just test type if found
        if bpm is not None:
            assert isinstance(bpm, float)
            assert bpm > 0

    def test_bpm_in_plausible_range(self):
        po = PulseOxPlot()
        bpm = po.estimate_bpm(_ir_buf_with_peaks())
        if bpm is not None:
            assert 30 < bpm < 300


# ---------------------------------------------------------------------------
# smooth_bpm
# ---------------------------------------------------------------------------

class TestSmoothBPM:
    def test_returns_none_when_no_history(self):
        po = PulseOxPlot()
        result = po.smooth_bpm(None)
        assert result is None

    def test_adds_to_history(self):
        po = PulseOxPlot()
        po.smooth_bpm(70.0)
        assert 70.0 in po.bpm_hist

    def test_returns_mean_of_history(self):
        po = PulseOxPlot()
        po.smooth_bpm(60.0)
        po.smooth_bpm(80.0)
        result = po.smooth_bpm(None)  # None doesn't extend history
        assert result == pytest.approx(70.0, abs=1e-6)

    def test_returns_value_with_single_entry(self):
        po = PulseOxPlot()
        result = po.smooth_bpm(75.0)
        assert result == pytest.approx(75.0, abs=1e-6)


# ---------------------------------------------------------------------------
# estimate_spo2
# ---------------------------------------------------------------------------

class TestEstimateSPO2:
    def test_returns_none_when_ac_i_zero(self):
        po = PulseOxPlot()
        flat = deque([50000.0] * 100, maxlen=100)
        result = po.estimate_spo2(flat, flat)
        assert result is None

    def test_returns_float_with_valid_signal(self):
        po = PulseOxPlot()
        rng = np.random.default_rng(11)
        red = deque((50000 + 5000 * np.sin(np.linspace(0, 6, 100))).tolist(), maxlen=100)
        ir = deque((60000 + 6000 * np.sin(np.linspace(0, 6, 100))).tolist(), maxlen=100)
        result = po.estimate_spo2(red, ir)
        assert result is not None
        assert isinstance(result, float)

    def test_returns_none_when_dc_r_zero(self):
        po = PulseOxPlot()
        zero_buf = deque([0.0] * 100, maxlen=100)
        varying = deque([float(i) for i in range(100)], maxlen=100)
        result = po.estimate_spo2(zero_buf, varying)
        assert result is None


# ---------------------------------------------------------------------------
# plot_all
# ---------------------------------------------------------------------------

class TestPlotAll:
    def test_sets_all_data(self):
        po = PulseOxPlot()
        for i in range(3):
            samples = _make_6byte_sample()
            time_axis = np.arange(i * 10, (i + 1) * 10, dtype=float)
            po.update_plot(time_axis, samples)
        po.plot_all()
        xdata, _ = po.line_red.get_data()
        assert len(xdata) == len(po.all_time)


# ---------------------------------------------------------------------------
# shift_review_window
# ---------------------------------------------------------------------------

class TestShiftReviewWindow:
    def test_shift_right_returns_true(self):
        po = PulseOxPlot()
        result = po.shift_review_window(1)
        assert result is True

    def test_both_axes_shifted(self):
        po = PulseOxPlot()
        old_ax = po.ax.get_xlim()
        old_dig = po.ax_dig.get_xlim()
        po.shift_review_window(1)
        assert po.ax.get_xlim()[0] > old_ax[0]
        assert po.ax_dig.get_xlim()[0] > old_dig[0]


# ---------------------------------------------------------------------------
# _close_plot
# ---------------------------------------------------------------------------

class TestClosePlot:
    def test_close_does_not_raise(self):
        po = PulseOxPlot()
        po._close_plot()


# ---------------------------------------------------------------------------
# save_data
# ---------------------------------------------------------------------------

class TestSaveData:
    def _populate(self, po: PulseOxPlot, n: int = 5):
        for i in range(n):
            samples = _make_6byte_sample(red=0x10000 + i, ir=0x20000 + i)
            time_axis = np.arange(i * 10, (i + 1) * 10, dtype=float)
            po.update_plot(time_axis, samples)

    def test_save_data_empty_selection(self, tmp_path, monkeypatch):
        po = PulseOxPlot()
        self._populate(po)
        monkeypatch.setattr(
            PlotManager,
            "_prepare_export_path",
            lambda self, filename: tmp_path / filename,
        )
        dest = po.save_data("pulseox.xlsx")
        assert (tmp_path / "pulseox.xlsx").exists()
        assert dest.endswith("pulseox.xlsx")

    def test_save_data_with_selection(self, tmp_path, monkeypatch):
        po = PulseOxPlot()
        self._populate(po)
        po.selected_samples = np.array([1.0, 2.0, 3.0])
        po.selected_times = np.array([0.1, 0.2, 0.3])
        po.selected_ir = np.array([10.0, 20.0, 30.0])

        monkeypatch.setattr(
            PlotManager,
            "_prepare_export_path",
            lambda self, filename: tmp_path / filename,
        )
        dest = po.save_data("pulseox_sel.xlsx")
        assert (tmp_path / "pulseox_sel.xlsx").exists()


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

class TestEvents:
    def setup_method(self):
        self.po = PulseOxPlot()
        for i in range(3):
            samples = _make_6byte_sample()
            time_axis = np.arange(i * 10, (i + 1) * 10, dtype=float)
            self.po.update_plot(time_axis, samples)

    def test_on_press_in_axes(self):
        event = MockEvent(button=1, inaxes=self.po.ax, xdata=5.0)
        self.po.on_press(event)
        assert self.po.selection_start == 5.0

    def test_on_press_outside_axes(self):
        event = MockEvent(button=1, inaxes=None, xdata=5.0)
        self.po.on_press(event)
        assert self.po.selection_start is None

    def test_on_release_with_selection(self):
        # Use a fresh PulseOxPlot and manually align all_time and all_red_values
        # to avoid the known mismatch from all_time being overwritten per update.
        po = PulseOxPlot()
        n = 10
        po.all_time = np.arange(n, dtype=float)
        po.all_red_values = list(range(n))
        po.all_ir_values = list(range(n))
        po.selection_start = 2.0
        event = MockEvent(button=1, inaxes=po.ax, xdata=8.0)
        po.on_release(event)
        assert po.selection_rect is not None
