from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import numpy as np
import xlsxwriter
from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle


@dataclass
class HistoryTarget:
    axis: Axes
    line: Line2D
    channel: str
    relative_to_window: bool = True
    max_points: int = 4000


class HistoryBuffer:
    """Fixed-size buffer storing samples so plots can revisit past windows."""

    def __init__(self, max_samples: int = 120_000) -> None:
        self.times: deque[float] = deque(maxlen=max_samples)
        self.values: deque[float] = deque(maxlen=max_samples)

    def extend(self, times: Iterable[float], values: Iterable[float]) -> None:
        for t_value, sample in zip(times, values):
            self.times.append(float(t_value))
            self.values.append(float(sample))

    def window(self, start: float, end: float, *, max_points: int) -> Tuple[np.ndarray, np.ndarray]:
        if not self.times or start >= end:
            return np.array([], dtype=float), np.array([], dtype=float)
        times = np.fromiter(self.times, dtype=float)
        values = np.fromiter(self.values, dtype=float)
        mask = (times >= start) & (times <= end)
        window_times = times[mask]
        window_values = values[mask]
        if window_times.size == 0:
            return window_times, window_values
        if window_times.size > max_points:
            idx = np.linspace(0, window_times.size - 1, max_points, dtype=int)
            window_times = window_times[idx]
            window_values = window_values[idx]
        return window_times, window_values

    def min_time(self) -> Optional[float]:
        return float(self.times[0]) if self.times else None

    def max_time(self) -> Optional[float]:
        return float(self.times[-1]) if self.times else None


class PlotManager:
    """Shared helpers for Matplotlib interaction + export tooling."""

    def __init__(self) -> None:
        self.selected_samples = []
        self.selected_times = []
        self.selection_start = None
        self.selection_rect = None

        self._history_window_seconds = 5.0
        self._history_step_seconds = 2.5
        self._history_targets: Dict[str, HistoryTarget] = {}
        self._history_buffers: Dict[str, HistoryBuffer] = {}
        self._history_review_active = False
        self._history_center_time: Optional[float] = None

    # ── Selection helpers ───────────────────────────────────────────────────────
    def zoom_around_cursor(self, ax: Axes) -> None:
        def on_scroll(event):
            if event.inaxes != ax:
                return

            base_scale = 1.1
            cur_xlim = ax.get_xlim()
            xdata = event.xdata

            if event.button == "up":
                scale_factor = 1 / base_scale
            elif event.button == "down":
                scale_factor = base_scale
            else:
                scale_factor = 1

            left = xdata - (xdata - cur_xlim[0]) * scale_factor
            right = xdata + (cur_xlim[1] - xdata) * scale_factor
            ax.set_xlim([left, right])
            ax.figure.canvas.draw_idle()

        ax.figure.canvas.mpl_connect("scroll_event", on_scroll)

    def _prepare_export_path(self, filename: str) -> Path:
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        return downloads_dir / filename

    def _create_workbook(self, filename: str):
        destination = self._prepare_export_path(filename)
        workbook = xlsxwriter.Workbook(str(destination))
        return workbook, destination

    def save_data(self, filename: str) -> str:
        workbook, destination = self._create_workbook(filename)
        worksheet = workbook.add_worksheet("Selected Data")
        worksheet.write(0, 0, "Time (s)")
        worksheet.write(0, 1, "Sample Value")
        for i in range(len(self.selected_samples)):
            worksheet.write(i + 1, 0, self.selected_times[i])
            worksheet.write(i + 1, 1, self.selected_samples[i])
        workbook.close()
        return str(destination)

    def on_press(self, event, ax: Axes) -> None:
        if event.button == 1:
            if event.inaxes == ax:
                self.selection_start = event.xdata
                if self.selection_rect:
                    self.selection_rect.remove()
                    self.selection_rect = None
        elif self.selection_rect:
            self.selection_rect.remove()
            self.selection_rect = None

    def on_release(self, event, ax: Axes, time, samples) -> None:
        if event.inaxes == ax and self.selection_start and event.button == 1:
            self.selection_end = event.xdata
            y_min, y_max = ax.get_ylim()
            x0 = min(self.selection_start, self.selection_end)
            width = abs(self.selection_end - self.selection_start)

            full_time_array = np.array(time)
            full_samples_array = np.array(samples)
            mask = (time >= x0) & (time <= x0 + width)
            self.selected_times = full_time_array[mask]
            self.selected_samples = full_samples_array[mask]

            self.selection_rect = Rectangle(
                (x0, y_min),
                width,
                y_max - y_min,
                linewidth=1,
                edgecolor="blue",
                facecolor="lightblue",
                alpha=0.5,
            )
            ax.add_patch(self.selection_rect)

    def on_scroll(self, _event) -> None:
        if self.selection_rect:
            self.selection_rect.remove()
            self.selection_rect = None

    # ── History navigation helpers ──────────────────────────────────────────────
    def configure_history_window(self, *, window_seconds: float, step_seconds: Optional[float] = None) -> None:
        self._history_window_seconds = window_seconds
        self._history_step_seconds = step_seconds or max(0.1, window_seconds / 2)

    def register_history_channel(
        self,
        *,
        channel: str,
        axis: Axes,
        line: Line2D,
        relative_to_window: bool = True,
        max_points: int = 4000,
        max_samples: int = 120_000,
    ) -> None:
        self._history_targets[channel] = HistoryTarget(
            axis=axis,
            line=line,
            channel=channel,
            relative_to_window=relative_to_window,
            max_points=max_points,
        )
        self._history_buffers.setdefault(channel, HistoryBuffer(max_samples))

    def record_history_samples(self, channel: str, times: Iterable[float], values: Iterable[float]) -> None:
        buffer = self._history_buffers.get(channel)
        if buffer is None:
            return
        buffer.extend(times, values)

    def supports_history_navigation(self) -> bool:
        return bool(self._history_targets)

    def enter_review_mode(self) -> bool:
        if not self.supports_history_navigation():
            return False
        bounds = self._history_bounds()
        if not bounds:
            return False
        self._history_review_active = True
        self._history_center_time = bounds[1]
        self._render_history_view()
        return True

    def exit_review_mode(self) -> None:
        self._history_review_active = False
        self._history_center_time = None

    def shift_review_window(self, direction: int) -> bool:
        if not self._history_review_active:
            return False
        bounds = self._history_bounds()
        if not bounds:
            return False
        min_time, max_time = bounds
        half_window = self._history_window_seconds / 2
        center = self._history_center_time or max_time
        center += direction * self._history_step_seconds
        center = max(min_time + half_window, min(center, max_time))
        self._history_center_time = center
        self._render_history_view()
        return True

    def _history_bounds(self) -> Optional[Tuple[float, float]]:
        mins = []
        maxs = []
        for buffer in self._history_buffers.values():
            min_time = buffer.min_time()
            max_time = buffer.max_time()
            if min_time is not None:
                mins.append(min_time)
            if max_time is not None:
                maxs.append(max_time)
        if not mins or not maxs:
            return None
        return min(mins), max(maxs)

    def _render_history_view(self) -> None:
        if not self._history_review_active:
            return
        bounds = self._history_bounds()
        if not bounds:
            return
        min_time, max_time = bounds
        window = self._history_window_seconds
        half_window = window / 2
        center = self._history_center_time or max_time
        start = max(min_time, center - half_window)
        end = min(max_time, center + half_window)
        if end - start < window:
            start = max(min_time, end - window)
            end = start + window
        start = max(min_time, start)
        end = min(max_time, end)
        self._history_center_time = (start + end) / 2

        for channel, target in self._history_targets.items():
            buffer = self._history_buffers.get(channel)
            if buffer is None:
                continue
            times, values = buffer.window(start, end, max_points=target.max_points)
            if times.size == 0:
                continue
            x_vals = times - (start if target.relative_to_window else 0.0)
            target.line.set_data(x_vals, values)
            if target.relative_to_window:
                target.axis.set_xlim(0, max(1e-6, end - start))
            else:
                target.axis.set_xlim(start, end)
