from collections import deque
from typing import Iterable, List

import matplotlib.pyplot as plt
import numpy as np

from .PlotManager import PlotManager


class RespiratoryPlot(PlotManager):
    """Streaming visualization and lightweight analytics for respiratory effort."""

    def __init__(self) -> None:
        super().__init__()
        self.sample_rate = 200  # Hz, matches the FakeScope default
        self.display_window = 20  # seconds of waveform to keep on screen
        self.rate_window = 60  # seconds used for breaths-per-minute averaging

        self.display_time: deque[float] = deque()
        self.display_samples: deque[float] = deque()
        self.recent_breath_times: deque[float] = deque()

        self.rate_time_values: List[float] = []
        self.rate_values: List[float] = []

        self.latest_rate: float | None = None
        self.avg_rate: float | None = None
        self.latest_effort_delta: float | None = None
        self.window_breath_count: int = 0

        self.fig, (self.ax_wave, self.ax_rate) = plt.subplots(2, 1, figsize=(15, 8))
        self.fig.suptitle("Respiratory Effort Monitor")

        self.line_wave, = self.ax_wave.plot([], [], color="#1f77b4", linewidth=1.5)
        self.ax_wave.set_ylabel("Signal (V)")
        self.ax_wave.set_xlabel("Time (s)")
        self.ax_wave.grid(True)

        self.line_rate, = self.ax_rate.plot([], [], color="#ff7f0e", linewidth=2)
        self.ax_rate.set_ylabel("Breaths/min")
        self.ax_rate.set_xlabel("Time (s)")
        self.ax_rate.set_ylim(0, 40)
        self.ax_rate.grid(True)

    def update_plot(self, t_axis: Iterable[float], samples: Iterable[float]):
        t_axis = np.asarray(list(t_axis), dtype=float)
        samples = np.asarray(list(samples), dtype=float)
        if t_axis.size == 0 or samples.size == 0:
            return self.line_wave, self.line_rate

        self.display_time.extend(t_axis.tolist())
        self.display_samples.extend(samples.tolist())

        latest_time = self.display_time[-1]
        cutoff = latest_time - self.display_window
        while self.display_time and self.display_time[0] < cutoff:
            self.display_time.popleft()
            self.display_samples.popleft()

        time_data = np.fromiter(self.display_time, dtype=float)
        sample_data = np.fromiter(self.display_samples, dtype=float)

        self.line_wave.set_data(time_data, sample_data)
        if time_data.size > 0:
            self.ax_wave.set_xlim(max(0.0, time_data[-1] - self.display_window), time_data[-1])
            ymin, ymax = float(sample_data.min()), float(sample_data.max())
            padding = max(0.01, 0.2 * (ymax - ymin)) if ymax > ymin else 0.05
            self.ax_wave.set_ylim(ymin - padding, ymax + padding)

        current_time = float(time_data[-1]) if time_data.size else 0.0
        breath_times = self._detect_breaths(t_axis, samples)
        self._update_breath_history(breath_times, current_time)

        rate = self._compute_rate()
        self.latest_rate = rate
        self.rate_time_values.append(current_time)
        self.rate_values.append(rate if rate is not None else np.nan)

        finite_rates = [value for value in self.rate_values if np.isfinite(value)]
        self.avg_rate = float(np.mean(finite_rates)) if finite_rates else None

        rate_time = np.asarray(self.rate_time_values, dtype=float)
        rate_values = np.asarray(self.rate_values, dtype=float)
        self.line_rate.set_data(rate_time, rate_values)
        if rate_time.size:
            min_time = max(0.0, rate_time[-1] - self.rate_window)
            max_time = rate_time[-1] if rate_time[-1] > min_time else min_time + 1.0
            self.ax_rate.set_xlim(min_time, max_time)

        if sample_data.size:
            self.latest_effort_delta = float(sample_data.max() - sample_data.min())
        else:
            self.latest_effort_delta = None

        return self.line_wave, self.line_rate

    def _detect_breaths(self, t_axis: np.ndarray, samples: np.ndarray) -> List[float]:
        """Identify rising zero crossings as proxies for inhalation peaks."""
        if samples.size < 2:
            return []
        threshold = np.median(samples)
        centered = samples - threshold
        above = centered >= 0
        crossings = np.where((~above[:-1]) & (above[1:]))[0]
        if crossings.size == 0:
            return []
        return t_axis[crossings + 1].astype(float).tolist()

    def _update_breath_history(self, new_times: List[float], current_time: float) -> None:
        for timestamp in new_times:
            self.recent_breath_times.append(float(timestamp))
        cutoff = current_time - self.rate_window
        while self.recent_breath_times and self.recent_breath_times[0] < cutoff:
            self.recent_breath_times.popleft()
        self.window_breath_count = len(self.recent_breath_times)

    def _compute_rate(self) -> float | None:
        if len(self.recent_breath_times) < 2:
            return None
        times = np.asarray(self.recent_breath_times, dtype=float)
        intervals = np.diff(times)
        finite = intervals[np.isfinite(intervals) & (intervals > 0)]
        if finite.size == 0:
            return None
        avg_interval = float(np.mean(finite))
        return 60.0 / avg_interval
    
    def shift_review_window(self, direction):
        self.ax_rate.set_xlim(*(limit + (direction * 10) for limit in self.ax_rate.get_xlim()))
        return True
    
    def plot_all(self):
        pass
    
    def _close_plot(self):
        plt.close(self.fig)

