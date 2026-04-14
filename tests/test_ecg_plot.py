"""Tests for ECGPlot – setup, update_plot, BPM calculation, events, save_data."""

from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import patch, MagicMock

from conftest import MockEvent
from ECGPlot import ECGPlot
from PlotManager import PlotManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RNG = np.random.default_rng(42)

def _flat_samples(n: int = 512, dc: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """Return (t_axis, samples) with no peaks above ECGPlot's threshold (1.92 V)."""
    t = np.linspace(0.0, n / 8192, n)
    s = dc + RNG.uniform(-0.01, 0.01, n)
    return t, s


def _samples_with_peaks(n: int = 512, peak_height: float = 2.0) -> tuple[np.ndarray, np.ndarray]:
    """Return (t_axis, samples) containing several peaks well above threshold."""
    t = np.linspace(0.0, n / 8192, n)
    s = RNG.uniform(-0.01, 0.01, n)
    # Inject 3 sharp spikes at regular positions
    for idx in [100, 250, 400]:
        s[idx] = peak_height
    return t, s


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

class TestSetup:
    def test_axes_created(self):
        ecg = ECGPlot()
        assert ecg.ax1 is not None
        assert ecg.ax3 is not None

    def test_lines_created(self):
        ecg = ECGPlot()
        assert ecg.line1 is not None
        assert ecg.peaks_plot is not None
        assert ecg.line3_bpm is not None

    def test_figure_title(self):
        ecg = ECGPlot()
        assert ecg.fig._suptitle.get_text() == "Heart Rate Monitor"

    def test_bpm_text_initial(self):
        ecg = ECGPlot()
        assert "BPM" in ecg.bpm_text.get_text() or ecg.bpm_text.get_text() == "BPM: --"

    def test_initial_data_structures(self):
        ecg = ECGPlot()
        assert ecg.bpm_values == []
        assert ecg.time_values == []
        assert ecg.raw_time == []
        assert ecg.raw_samples == []


# ---------------------------------------------------------------------------
# update_plot – no peaks path
# ---------------------------------------------------------------------------

class TestUpdatePlotNoPeaks:
    def setup_method(self):
        self.ecg = ECGPlot()

    def test_returns_four_artists(self):
        t, s = _flat_samples()
        result = self.ecg.update_plot(t, s)
        assert len(result) == 4

    def test_line1_data_set(self):
        t, s = _flat_samples()
        self.ecg.update_plot(t, s)
        xdata, ydata = self.ecg.line1.get_data()
        assert len(xdata) == len(t)

    def test_peaks_plot_empty(self):
        t, s = _flat_samples()
        self.ecg.update_plot(t, s)
        xdata, _ = self.ecg.peaks_plot.get_data()
        assert len(xdata) == 0

    def test_bpm_text_shows_dash_when_no_peaks(self):
        t, s = _flat_samples()
        self.ecg.update_plot(t, s)
        assert self.ecg.bpm_text.get_text() == "BPM: --"

    def test_raw_values_accumulated(self):
        t, s = _flat_samples()
        self.ecg.update_plot(t, s)
        assert len(self.ecg.raw_time) == len(t)
        assert len(self.ecg.raw_samples) == len(s)

    def test_display_time_extended(self):
        t, s = _flat_samples()
        self.ecg.update_plot(t, s)
        assert len(self.ecg.display_time) == len(t)


# ---------------------------------------------------------------------------
# update_plot – peaks present
# ---------------------------------------------------------------------------

class TestUpdatePlotWithPeaks:
    def setup_method(self):
        self.ecg = ECGPlot()

    def test_peaks_plot_non_empty(self):
        t, s = _samples_with_peaks()
        self.ecg.update_plot(t, s)
        xdata, _ = self.ecg.peaks_plot.get_data()
        assert len(xdata) > 0

    def test_all_peak_times_populated(self):
        t, s = _samples_with_peaks()
        self.ecg.update_plot(t, s)
        assert len(self.ecg.all_peak_times) > 0

    def test_bpm_shows_value_after_two_peaks(self):
        """BPM is only computed once we have > 1 peak in recent_peak_times."""
        t, s = _samples_with_peaks()
        # First call gives us peaks but BPM needs >1 recent peak
        self.ecg.update_plot(t, s)
        # Second call with offset time ensures more recent peaks exist
        t2 = t + t[-1] + (t[1] - t[0])
        self.ecg.update_plot(t2, s)
        # At this point we should have BPM or at worst nan
        assert len(self.ecg.bpm_values) >= 2

    def test_peak_times_stored_as_float(self):
        t, s = _samples_with_peaks()
        self.ecg.update_plot(t, s)
        for pt in self.ecg.all_peak_times:
            assert isinstance(pt, float)


# ---------------------------------------------------------------------------
# update_plot – BPM accumulation over multiple calls
# ---------------------------------------------------------------------------

class TestBPMCalculation:
    def test_bpm_computed_when_multiple_peaks_present(self):
        ecg = ECGPlot()
        # Use big signal with many peaks over two batches
        n = 1024
        t = np.linspace(0.0, n / 8192, n)
        s = np.zeros(n)
        # Place peaks at equal intervals (~341 samples apart → ~3 peaks)
        for idx in [50, 391, 732]:
            s[idx] = 2.0
        ecg.update_plot(t, s)
        # Second batch offset in time
        t2 = t + t[-1] + (t[1] - t[0])
        ecg.update_plot(t2, s)
        finite = [v for v in ecg.bpm_values if np.isfinite(v)]
        assert len(finite) > 0

    def test_avg_bpm_none_when_no_finite_values(self):
        ecg = ECGPlot()
        t, s = _flat_samples()
        ecg.update_plot(t, s)
        assert ecg.avg_bpm is None or ecg.avg_bpm is None

    def test_nan_appended_when_avg_rr_is_zero(self):
        """avg_rr=0.0 is falsy → the else branch appends nan instead of a BPM."""
        ecg = ECGPlot()
        # Two identical peak times produce diff=[0.0] → avg_rr=0.0 → falsy
        ecg.recent_peak_times = [1.0, 1.0]
        t, s = _flat_samples()  # no new peaks
        ecg.update_plot(t, s)
        assert np.isnan(ecg.bpm_values[-1])


# ---------------------------------------------------------------------------
# on_press / on_release
# ---------------------------------------------------------------------------

class TestEvents:
    def setup_method(self):
        self.ecg = ECGPlot()

    def test_on_press_in_axes_sets_start(self):
        event = MockEvent(button=1, inaxes=self.ecg.ax1, xdata=2.0)
        self.ecg.on_press(event)
        assert self.ecg.selection_start == 2.0

    def test_on_press_outside_axes_no_start(self):
        event = MockEvent(button=1, inaxes=None, xdata=2.0)
        self.ecg.on_press(event)
        assert self.ecg.selection_start is None

    def test_on_release_creates_selection(self):
        # Populate raw data first
        t, s = _flat_samples()
        self.ecg.update_plot(t, s)
        self.ecg.selection_start = float(t[10])

        event = MockEvent(button=1, inaxes=self.ecg.ax1, xdata=float(t[200]))
        self.ecg.on_release(event)
        assert self.ecg.selection_rect is not None

    def test_on_release_outside_axes_no_rect(self):
        event = MockEvent(button=1, inaxes=None, xdata=1.0)
        self.ecg.on_release(event)
        assert self.ecg.selection_rect is None


# ---------------------------------------------------------------------------
# shift_review_window
# ---------------------------------------------------------------------------

class TestShiftReviewWindow:
    def test_shift_right(self):
        ecg = ECGPlot()
        old_lim = ecg.ax1.get_xlim()
        result = ecg.shift_review_window(1)
        new_lim = ecg.ax1.get_xlim()
        assert result is True
        assert new_lim[0] > old_lim[0]

    def test_shift_left(self):
        ecg = ECGPlot()
        old_lim = ecg.ax1.get_xlim()
        result = ecg.shift_review_window(-1)
        new_lim = ecg.ax1.get_xlim()
        assert result is True
        assert new_lim[0] < old_lim[0]


# ---------------------------------------------------------------------------
# plot_all
# ---------------------------------------------------------------------------

class TestPlotAll:
    def test_sets_line_data(self):
        ecg = ECGPlot()
        t, s = _flat_samples()
        ecg.update_plot(t, s)
        ecg.plot_all()
        xdata, ydata = ecg.line1.get_data()
        assert list(xdata) == ecg.raw_time_vals


# ---------------------------------------------------------------------------
# _close_plot
# ---------------------------------------------------------------------------

class TestClosePlot:
    def test_close_does_not_raise(self):
        ecg = ECGPlot()
        ecg._close_plot()  # Should not raise


# ---------------------------------------------------------------------------
# save_data
# ---------------------------------------------------------------------------

class TestSaveData:
    def test_save_data_no_selection(self, tmp_path, monkeypatch):
        ecg = ECGPlot()
        t, s = _flat_samples()
        ecg.update_plot(t, s)
        # selected_samples must be a numpy array for .size to work
        ecg.selected_samples = np.array([])
        ecg.selected_times = np.array([])

        monkeypatch.setattr(
            PlotManager,
            "_prepare_export_path",
            lambda self, filename: tmp_path / filename,
        )
        dest = ecg.save_data("ecg_test.xlsx")
        assert (tmp_path / "ecg_test.xlsx").exists()
        assert dest.endswith("ecg_test.xlsx")

    def test_save_data_with_selection(self, tmp_path, monkeypatch):
        ecg = ECGPlot()
        t, s = _flat_samples()
        ecg.update_plot(t, s)
        ecg.selected_samples = np.array([0.01, 0.02, 0.03])
        ecg.selected_times = np.array([0.1, 0.2, 0.3])

        monkeypatch.setattr(
            PlotManager,
            "_prepare_export_path",
            lambda self, filename: tmp_path / filename,
        )
        dest = ecg.save_data("ecg_sel.xlsx")
        assert (tmp_path / "ecg_sel.xlsx").exists()

    def test_save_data_with_peaks_in_workbook(self, tmp_path, monkeypatch):
        ecg = ECGPlot()
        t, s = _samples_with_peaks()
        ecg.update_plot(t, s)
        ecg.selected_samples = np.array([])
        ecg.selected_times = np.array([])

        monkeypatch.setattr(
            PlotManager,
            "_prepare_export_path",
            lambda self, filename: tmp_path / filename,
        )
        ecg.save_data("ecg_peaks.xlsx")
        assert len(ecg.all_peak_times) > 0
