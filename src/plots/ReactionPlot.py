import time
import random
from collections import deque

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Cursor
from mpl_interactions import ioff, panhandler
from .PlotManager import PlotManager

class ReactionPlot(PlotManager):
    def __init__(self):
        super().__init__()
        self.sample_rate = 10000
        self.threshold_voltage = 2

        self.reaction_times = []
        self.cue_active = False
        self.reaction_start = None
        self.last_cue_time = time.time()
        self.random_delay = random.uniform(2, 5)
        self.raw_time = []
        self.raw_samples = []
        self.trial_timestamps = []

        self.display_window = 5.0  # seconds shown on screen
        self.max_display_points = 4000
        self.display_time = deque()
        self.display_samples = deque()
        self._current_xlim = None
        self.configure_history_window(window_seconds=self.display_window, step_seconds=self.display_window / 2)
        self._setup_plot()
        self.register_history_channel(
            channel="signal",
            axis=self.ax_signal,
            line=self.line_signal,
            relative_to_window=False,
            max_points=self.max_display_points,
        )

    def _setup_plot(self):
        self.fig, (self.ax_signal, self.ax_reaction) = plt.subplots(2, 1, figsize=(15, 8))
        self.fig.suptitle("Reaction Time Tracker")

        self.line_signal, = self.ax_signal.plot([], [], lw=1)
        self.ax_signal.set_ylim(0, 3.5)
        self.ax_signal.set_ylabel("Button Voltage (V)")
        self.ax_signal.set_xlabel("Time (ms)")
        self.ax_signal.set_xlim(0, self.display_window)
        self.ax_signal.grid(True)

        self.ax_reaction.set_ylim(0, 1000)
        self.ax_reaction.set_xlim(0, 10)
        self.ax_reaction.set_ylabel("Reaction Time (ms)")
        self.ax_reaction.set_xlabel("Trial")
        self.ax_reaction.grid(True)

        self.cue_text = self.ax_signal.text(0.02, 0.9, '', transform=self.ax_signal.transAxes, fontsize=14, color='red')

        self.cursor = Cursor(self.ax_signal, useblit=True, color='red', linewidth=1)
        self.zoom = self.zoom_around_cursor(self.ax_signal)
        self.pan_handler = panhandler(self.fig)

        self.fig.canvas.mpl_connect('button_press_event', self.on_press)
        self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)

        self.selection_start = 0
        self.selection_rect = None
        self.selection_end = 0

    def update_plot(self, t_axis, samples):
        t_axis = np.asarray(t_axis, dtype=float)
        samples = np.asarray(samples, dtype=float)
        if t_axis.size == 0 or samples.size == 0:
            return self.line_signal, self.cue_text

        if self.raw_time:
            last_time = self.raw_time[-1]
            if t_axis[0] <= last_time:
                offset = last_time - t_axis[0] + (1 / self.sample_rate)
                t_axis = t_axis + offset
        self.record_history_samples("signal", t_axis, samples)

        self.raw_time.extend(t_axis.tolist())
        self.raw_samples.extend(samples.tolist())

        newest_time = t_axis[-1]
        cutoff = max(0.0, newest_time - self.display_window)
        for t_val, sample_val in zip(t_axis.tolist(), samples.tolist()):
            self.display_time.append(t_val)
            self.display_samples.append(sample_val)
        while self.display_time and self.display_time[0] < cutoff:
            self.display_time.popleft()
            self.display_samples.popleft()

        visible_time = np.fromiter(self.display_time, dtype=float)
        visible_samples = np.fromiter(self.display_samples, dtype=float)
        if visible_time.size:
            visible_time, visible_samples = self._downsample_series(visible_time, visible_samples)
            self.line_signal.set_data(visible_time, visible_samples)
            self._update_signal_axes(visible_time, visible_samples)

        # Start cue if delay has passed
        now = time.time()
        if not self.cue_active and (now - self.last_cue_time > self.random_delay):
            self.cue_active = True
            self.reaction_start = now
            self.cue_text.set_text("GO!")

        # Detect button press
        if self.cue_active and np.any(samples > self.threshold_voltage):
            rt_ms = (time.time() - self.reaction_start) * 1000
            self.reaction_times.append(rt_ms)
            self.trial_timestamps.append(self.raw_time[-1] if self.raw_time else 0.0)
            self.cue_active = False
            self.last_cue_time = time.time()
            self.random_delay = random.uniform(2, 5)

            self.cue_text.set_text(f"Reaction: {rt_ms:.1f} ms (Avg: {np.mean(self.reaction_times):.1f} ms)")
            self.ax_reaction.clear()
            self.ax_reaction.set_ylim(0, 1000)
            self.ax_reaction.set_xlim(0, max(10, len(self.reaction_times)))
            self.ax_reaction.set_ylabel("Reaction Time (ms)")
            self.ax_reaction.set_xlabel("Trial")
            self.ax_reaction.grid(True)
            self.ax_reaction.scatter(range(1, len(self.reaction_times) + 1), self.reaction_times, color='blue')

        return self.line_signal, self.cue_text
    
    
    def on_press(self, event):
        PlotManager.on_press(self, event, self.ax_signal)

    def on_release(self, event):
        PlotManager.on_release(self, event, self.ax_signal, self.raw_time, self.raw_samples)
        self.fig.canvas.draw()

    def _close_plot(self):
        plt.close(self.fig)

    def save_data(self, filename):
        workbook, destination = self._create_workbook(filename)

        guide = workbook.add_worksheet("Read Me")
        guide.set_column(0, 0, 22)
        guide.set_column(1, 1, 90)
        guide.write(0, 0, "Worksheet")
        guide.write(0, 1, "How to use it - SWITCH BETWEEN TABS AT BOTTOM")
        guide.write(1, 0, "Reaction Trials")
        guide.write(
            1,
            1,
            "Each row is a full trial. Use 'Reaction Time (ms)' to compare attempts "
            "and 'Running Avg (ms)' to see overall progress.",
        )
        guide.write(2, 0, "Raw Signal")
        guide.write(
            2,
            1,
            "Time-series voltage trace for every captured sample. Plot columns A/B to "
            "inspect button behavior or recreate the graph.",
        )
        if self.selected_samples:
            guide.write(3, 0, "Selected Window")
            guide.write(
                3,
                1,
                "Only present when you drag-select a region in the GUI. Focused view "
                "of the highlighted time span for closer study.",
            )

        trials_ws = workbook.add_worksheet("Reaction Trials")
        trials_ws.write_row(0, 0, ["Trial #", "Reaction Time (ms)", "Running Avg (ms)", "Timestamp (s)"])
        running_total = 0.0
        for idx, rt in enumerate(self.reaction_times, start=1):
            running_total += rt
            avg = running_total / idx
            timestamp = self.trial_timestamps[idx - 1] if idx - 1 < len(self.trial_timestamps) else ""
            trials_ws.write_row(idx, 0, [idx, rt, avg, timestamp])

        raw_ws = workbook.add_worksheet("Raw Signal")
        raw_ws.write_row(0, 0, ["Time (s)", "Button Voltage (V)"])
        for idx, (t_value, sample) in enumerate(zip(self.raw_time, self.raw_samples), start=1):
            raw_ws.write_row(idx, 0, [t_value, sample])

        if self.selected_samples:
            sel_ws = workbook.add_worksheet("Selected Window")
            sel_ws.write_row(0, 0, ["Time (s)", "Button Voltage (V)"])
            for idx, (t_value, sample) in enumerate(zip(self.selected_times, self.selected_samples), start=1):
                sel_ws.write_row(idx, 0, [float(t_value), float(sample)])

        workbook.close()
        return str(destination)

    def _downsample_series(self, time_data, sample_data):
        if time_data.size <= self.max_display_points:
            return time_data, sample_data
        indices = np.linspace(0, time_data.size - 1, self.max_display_points, dtype=int)
        return time_data[indices], sample_data[indices]

    def _update_signal_axes(self, time_data, sample_data):
        if time_data.size == 0:
            return

        x_max = float(time_data[-1])
        x_min = max(0.0, x_max - self.display_window)
        if self._current_xlim != (x_min, x_max):
            if x_max <= x_min:
                x_max = x_min + (1 / self.sample_rate)
            self.ax_signal.set_xlim(x_min, x_max)
            self._current_xlim = (x_min, x_max)
