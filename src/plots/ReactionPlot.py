import time
import random
from pathlib import Path
from typing import Callable, Optional

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle
from matplotlib.widgets import Cursor
from mpl_interactions import ioff, panhandler
from PlotManager import PlotManager

class ReactionPlot(PlotManager):
    def __init__(self, cue_output: Optional[Callable[[bool], None]] = None):
        super().__init__()
        self.sample_rate = 10000
        self.threshold_voltage = 2
        self.cue_output = cue_output

        self.reaction_times = []
        self.cue_active = False
        self.reaction_start = None
        self.last_cue_time = time.time()
        self.random_delay = random.uniform(2, 5)
        self.full_time = []
        self.full_samples = []

        self.raw_time = []
        self.raw_samples = []
        self.trial_timestamps = []

        self.window_size = 30000


        self._setup_plot()

    def _setup_plot(self):
        self.fig, (self.ax_signal, self.ax_reaction) = plt.subplots(2, 1, figsize=(15, 8))
        self.fig.suptitle("Reaction Time Tracker")

        self.line_signal, = self.ax_signal.plot([], [], lw=1)
        self.ax_signal.set_ylim(0, 3.5)
        self.ax_signal.set_ylabel("Button Voltage (V)")
        self.ax_signal.set_xlabel("Time (ms)")
        self.ax_signal.set_xlim(0)
        self.ax_signal.grid(True)
        self.ax_signal.set_title("Press the hardware button after the LED turns on")

        self.ax_reaction.set_ylim(0, 1000)
        self.ax_reaction.set_xlim(0, 10)
        self.ax_reaction.set_ylabel("Reaction Time (ms)")
        self.ax_reaction.set_xlabel("Trial")
        self.ax_reaction.grid(True)

        self.cue_text = self.ax_signal.text(
            0.02,
            0.9,
            "Waiting for LED cue...",
            transform=self.ax_signal.transAxes,
            fontsize=14,
            color="red",
        )
        self.led_label = self.ax_signal.text(
            0.87,
            0.9,
            "LED",
            transform=self.ax_signal.transAxes,
            fontsize=11,
            color="#444444",
            ha="right",
            va="center",
        )
        self.led_indicator = Circle(
            (0.93, 0.9),
            radius=0.025,
            transform=self.ax_signal.transAxes,
            facecolor="#C7CBD1",
            edgecolor="#6B6D71",
            linewidth=1.5,
            alpha=0.95,
        )
        self.ax_signal.add_patch(self.led_indicator)

        self.cursor = Cursor(self.ax_signal, useblit=True, color='red', linewidth=1)
        self.zoom = self.zoom_around_cursor(self.ax_signal)
        self.pan_handler = panhandler(self.fig)

        self.fig.canvas.mpl_connect('button_press_event', self.on_press)
        self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)

        self.selection_start = 0
        self.selection_rect = None
        self.selection_end = 0
        self._set_cue_state(False, "Waiting for LED cue...")

    def _set_cue_state(self, active, message=None):
        self.cue_active = active
        self.led_indicator.set_facecolor("#FF453A" if active else "#C7CBD1")
        self.led_indicator.set_edgecolor("#7A1C16" if active else "#6B6D71")
        if message is not None:
            self.cue_text.set_text(message)
            self.cue_text.set_color("#C62828" if active else "#555555")
        if self.cue_output is not None:
            try:
                self.cue_output(active)
            except Exception:
                pass

    def update_plot(self, t_axis, samples):

        if self.full_time:
            t_axis = t_axis + self.full_time[-1] + (1 / self.sample_rate)
        self.full_time.extend(t_axis)
        self.full_samples.extend(samples)

        if self.raw_time:
            last_time = self.raw_time[-1]
            if t_axis[0] <= last_time:
                offset = last_time - t_axis[0] + (1 / self.sample_rate)
                t_axis = t_axis + offset

        self.raw_time.extend(t_axis.tolist())
        self.raw_samples.extend(samples.tolist())

        try:
            self.line_signal.set_data(self.full_time[-self.window_size:], self.full_samples[-self.window_size:])
        except IndexError:
            self.line_signal.set_data(self.full_time, self.full_samples)

        try:
            self.ax_signal.set_xlim(self.full_time[-self.window_size], self.full_time[-1])
        except IndexError:
            self.ax_signal.set_xlim(0, self.full_time[-1])

        # Start cue if delay has passed
        now = time.time()
        if not self.cue_active and (now - self.last_cue_time > self.random_delay):
            self.reaction_start = now
            self._set_cue_state(True, "LED ON! Press the button now")

        # Detect button press
        if self.cue_active and np.any(samples > self.threshold_voltage):
            rt_ms = (time.time() - self.reaction_start) * 1000
            self.reaction_times.append(rt_ms)
            self.trial_timestamps.append(self.raw_time[-1] if self.raw_time else 0.0)
            self.last_cue_time = time.time()
            self.random_delay = random.uniform(2, 5)

            self._set_cue_state(
                False,
                f"Reaction: {rt_ms:.1f} ms (Avg: {np.mean(self.reaction_times):.1f} ms)",
            )
            self.ax_reaction.clear()
            self.ax_reaction.set_ylim(0, 1000)
            self.ax_reaction.set_xlim(0, max(10, len(self.reaction_times)))
            self.ax_reaction.set_ylabel("Reaction Time (ms)")
            self.ax_reaction.set_xlabel("Trial")
            self.ax_reaction.grid(True)
            self.ax_reaction.scatter(range(1, len(self.reaction_times) + 1), self.reaction_times, color='blue')

        return self.line_signal, self.cue_text, self.led_label, self.led_indicator
    
    def shift_review_window(self, direction):
        self.ax_signal.set_xlim(*(limit + (direction * 20) for limit in self.ax_signal.get_xlim()))
        return True
    
    def plot_all(self):
        self.line_signal.set_data(self.full_time, self.full_samples)
    
    def on_press(self, event):
        PlotManager.on_press(self, event, self.ax_signal)

    def on_release(self, event):
        PlotManager.on_release(self, event, self.ax_signal, self.full_time, self.full_samples)
        self.fig.canvas.draw()

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
        if self.selected_samples.size > 0:
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

        if self.selected_samples.size > 0:
            sel_ws = workbook.add_worksheet("Selected Window")
            sel_ws.write_row(0, 0, ["Time (s)", "Button Voltage (V)"])
            for idx, (t_value, sample) in enumerate(zip(self.selected_times, self.selected_samples), start=1):
                sel_ws.write_row(idx, 0, [float(t_value), float(sample)])

        workbook.close()
        return str(destination)
    
    def _close_plot(self):
        self._set_cue_state(False)
        plt.close(self.fig)

