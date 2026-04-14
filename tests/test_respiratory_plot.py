"""Tests for RespiratoryPlot – setup, breath detection, rate calc, update_plot."""

from __future__ import annotations

import numpy as np
import pytest
from collections import deque

from conftest import MockEvent
from plots.RespiratoryPlot import RespiratoryPlot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sine_samples(
    duration: float = 5.0,
    fs: int = 200,
    freq: float = 0.3,
    amplitude: float = 0.5,
    offset: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Sinusoidal respiratory signal containing multiple zero-crossings."""
    t = np.linspace(0.0, duration, int(duration * fs))
    s = offset + amplitude * np.sin(2 * np.pi * freq * t)
    return t, s


def _flat_samples(n: int = 200, value: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    t = np.linspace(0.0, n / 200.0, n)
    s = np.full(n, value, dtype=float)
    return t, s


# ---------------------------------------------------------------------------
# Setup / Initialisation
# ---------------------------------------------------------------------------

class TestSetup:
    def test_axes_created(self):
        rp = RespiratoryPlot()
        assert rp.ax_wave is not None
        assert rp.ax_rate is not None

    def test_lines_created(self):
        rp = RespiratoryPlot()
        assert rp.line_wave is not None
        assert rp.line_rate is not None

    def test_figure_suptitle(self):
        rp = RespiratoryPlot()
        assert "Respiratory" in rp.fig._suptitle.get_text()

    def test_initial_deques_empty(self):
        rp = RespiratoryPlot()
        assert len(rp.display_time) == 0
        assert len(rp.display_samples) == 0
        assert len(rp.recent_breath_times) == 0

    def test_initial_rate_values(self):
        rp = RespiratoryPlot()
        assert rp.latest_rate is None
        assert rp.avg_rate is None
        assert rp.latest_effort_delta is None
        assert rp.window_breath_count == 0


# ---------------------------------------------------------------------------
# update_plot – empty input
# ---------------------------------------------------------------------------

class TestUpdatePlotEmpty:
    def test_empty_input_returns_artists(self):
        rp = RespiratoryPlot()
        result = rp.update_plot([], [])
        assert len(result) == 2

    def test_empty_input_does_not_extend_deques(self):
        rp = RespiratoryPlot()
        rp.update_plot([], [])
        assert len(rp.display_time) == 0


# ---------------------------------------------------------------------------
# update_plot – normal signal
# ---------------------------------------------------------------------------

class TestUpdatePlotNormal:
    def setup_method(self):
        self.rp = RespiratoryPlot()

    def test_returns_two_artists(self):
        t, s = _sine_samples()
        result = self.rp.update_plot(t, s)
        assert len(result) == 2

    def test_display_deques_populated(self):
        t, s = _sine_samples()
        self.rp.update_plot(t, s)
        assert len(self.rp.display_time) > 0

    def test_rate_time_values_appended(self):
        t, s = _sine_samples()
        self.rp.update_plot(t, s)
        assert len(self.rp.rate_time_values) == 1

    def test_rate_values_appended(self):
        t, s = _sine_samples()
        self.rp.update_plot(t, s)
        assert len(self.rp.rate_values) == 1

    def test_wave_line_data_set(self):
        t, s = _sine_samples()
        self.rp.update_plot(t, s)
        xdata, ydata = self.rp.line_wave.get_data()
        assert len(xdata) > 0

    def test_effort_delta_computed(self):
        t, s = _sine_samples()
        self.rp.update_plot(t, s)
        assert self.rp.latest_effort_delta is not None
        assert self.rp.latest_effort_delta > 0

    def test_xlim_updated(self):
        t, s = _sine_samples(duration=10.0)
        self.rp.update_plot(t, s)
        xlim = self.rp.ax_wave.get_xlim()
        assert xlim[1] > xlim[0]

    def test_display_window_pruning(self):
        """Samples older than display_window should be pruned from deques."""
        rp = RespiratoryPlot()
        rp.display_window = 2.0  # shrink window for faster test

        # Push a long signal (30 s) so old data gets pruned
        t, s = _sine_samples(duration=30.0)
        rp.update_plot(t, s)
        time_arr = np.asarray(rp.display_time)
        assert time_arr.max() - time_arr.min() <= rp.display_window + (1 / rp.sample_rate)

    def test_multiple_calls_accumulate_rate(self):
        rp = RespiratoryPlot()
        for i in range(3):
            t = np.linspace(i * 5.0, (i + 1) * 5.0, 1000)
            s = 0.5 * np.sin(2 * np.pi * 0.3 * t)
            rp.update_plot(t, s)
        assert len(rp.rate_values) == 3


# ---------------------------------------------------------------------------
# _detect_breaths
# ---------------------------------------------------------------------------

class TestDetectBreaths:
    def setup_method(self):
        self.rp = RespiratoryPlot()

    def test_single_sample_returns_empty(self):
        t = np.array([0.0])
        s = np.array([0.5])
        result = self.rp._detect_breaths(t, s)
        assert result == []

    def test_flat_signal_returns_empty(self):
        t, s = _flat_samples(200, 1.0)
        result = self.rp._detect_breaths(t, s)
        assert result == []

    def test_sine_wave_produces_crossings(self):
        t, s = _sine_samples(duration=10.0, freq=0.3)
        result = self.rp._detect_breaths(t, s)
        assert len(result) > 0

    def test_crossings_are_timestamps_from_t_axis(self):
        t, s = _sine_samples(duration=5.0, freq=0.5)
        result = self.rp._detect_breaths(t, s)
        for ts in result:
            assert float(t[0]) <= ts <= float(t[-1])

    def test_crossings_are_floats(self):
        t, s = _sine_samples(duration=5.0, freq=0.5)
        result = self.rp._detect_breaths(t, s)
        for ts in result:
            assert isinstance(ts, float)

    def test_monotonically_increasing_crossings(self):
        t, s = _sine_samples(duration=10.0, freq=0.3)
        result = self.rp._detect_breaths(t, s)
        for a, b in zip(result[:-1], result[1:]):
            assert a <= b

    def test_known_crossing_position(self):
        """Manually build a signal with exactly one upward crossing."""
        t = np.linspace(0, 1, 10)
        s = np.array([-1.0, -0.5, -0.1, 0.5, 0.8, -0.5, -1.0, 0.5, 1.0, 0.5])
        result = self.rp._detect_breaths(t, s)
        # Upward crossings at index 3 and 7
        assert len(result) == 2


# ---------------------------------------------------------------------------
# _update_breath_history
# ---------------------------------------------------------------------------

class TestUpdateBreathHistory:
    def setup_method(self):
        self.rp = RespiratoryPlot()

    def test_new_times_appended(self):
        self.rp._update_breath_history([1.0, 2.0, 3.0], current_time=5.0)
        assert 1.0 in self.rp.recent_breath_times
        assert 2.0 in self.rp.recent_breath_times

    def test_old_times_pruned(self):
        self.rp._update_breath_history([1.0, 2.0, 60.0], current_time=70.0)
        # 1.0 and 2.0 are older than rate_window (60 s) from current_time=70
        assert 1.0 not in self.rp.recent_breath_times
        assert 60.0 in self.rp.recent_breath_times

    def test_window_breath_count_updated(self):
        self.rp._update_breath_history([1.0, 2.0, 3.0], current_time=5.0)
        assert self.rp.window_breath_count == 3

    def test_empty_new_times(self):
        self.rp._update_breath_history([], current_time=0.0)
        assert self.rp.window_breath_count == 0


# ---------------------------------------------------------------------------
# _compute_rate
# ---------------------------------------------------------------------------

class TestComputeRate:
    def setup_method(self):
        self.rp = RespiratoryPlot()

    def test_returns_none_with_fewer_than_two_breaths(self):
        self.rp.recent_breath_times.append(1.0)
        result = self.rp._compute_rate()
        assert result is None

    def test_returns_none_with_empty_history(self):
        result = self.rp._compute_rate()
        assert result is None

    def test_returns_float_with_two_breaths(self):
        self.rp.recent_breath_times.extend([0.0, 4.0])  # 4 s interval → 15 BPM
        result = self.rp._compute_rate()
        assert result == pytest.approx(15.0, rel=1e-4)

    def test_uniform_intervals_give_expected_rate(self):
        # 10 breaths, 2 s apart → 30 breaths/min
        for i in range(10):
            self.rp.recent_breath_times.append(float(i * 2))
        result = self.rp._compute_rate()
        assert result == pytest.approx(30.0, rel=1e-4)

    def test_single_zero_interval_filters_out(self):
        """Duplicate timestamps should be ignored (interval == 0)."""
        self.rp.recent_breath_times.extend([0.0, 0.0, 4.0])
        result = self.rp._compute_rate()
        # Only the 4 s interval is finite and > 0 → 15 BPM
        assert result == pytest.approx(15.0, rel=1e-4)

    def test_returns_none_when_all_intervals_zero(self):
        """All-identical timestamps → all diffs are 0 → filtered out → finite is empty → None."""
        self.rp.recent_breath_times.extend([2.0, 2.0, 2.0])
        result = self.rp._compute_rate()
        assert result is None


# ---------------------------------------------------------------------------
# avg_rate accumulation
# ---------------------------------------------------------------------------

class TestAvgRate:
    def test_avg_rate_none_before_any_finite_value(self):
        rp = RespiratoryPlot()
        t, s = _flat_samples()
        rp.update_plot(t, s)
        # No breaths yet → rate is nan → avg_rate should be None
        assert rp.avg_rate is None

    def test_avg_rate_computed_after_breaths(self):
        rp = RespiratoryPlot()
        # Feed enough breathing signal to get finite BPM
        for i in range(5):
            t = np.linspace(i * 10.0, (i + 1) * 10.0, 2000)
            s = 0.5 * np.sin(2 * np.pi * 0.25 * t)
            rp.update_plot(t, s)
        finite = [v for v in rp.rate_values if np.isfinite(v)]
        if finite:
            assert rp.avg_rate == pytest.approx(float(np.mean(finite)), rel=1e-6)

    def test_latest_effort_delta_none_when_display_depleted(self):
        """A negative display_window drains all display samples, hitting the else branch."""
        rp = RespiratoryPlot()
        rp.display_window = -1  # cutoff = t[-1] - (-1) = t[-1]+1 > all timestamps → all trimmed
        rp.update_plot(np.array([1.0]), np.array([0.5]))
        assert rp.latest_effort_delta is None


# ---------------------------------------------------------------------------
# shift_review_window
# ---------------------------------------------------------------------------

class TestShiftReviewWindow:
    def test_shift_right_returns_true(self):
        rp = RespiratoryPlot()
        old_lim = rp.ax_rate.get_xlim()
        result = rp.shift_review_window(1)
        assert result is True
        assert rp.ax_rate.get_xlim()[0] > old_lim[0]

    def test_shift_left(self):
        rp = RespiratoryPlot()
        old_lim = rp.ax_rate.get_xlim()
        rp.shift_review_window(-1)
        assert rp.ax_rate.get_xlim()[0] < old_lim[0]


# ---------------------------------------------------------------------------
# plot_all / _close_plot
# ---------------------------------------------------------------------------

class TestPlotAll:
    def test_plot_all_does_not_raise(self):
        rp = RespiratoryPlot()
        rp.plot_all()  # Should be a no-op / pass


class TestClosePlot:
    def test_close_does_not_raise(self):
        rp = RespiratoryPlot()
        rp._close_plot()
