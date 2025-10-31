import time
import random
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Cursor
from mpl_interactions import ioff, panhandler
from PlotManager import PlotManager

class ReactionPlot(PlotManager):
    def __init__(self):
        self.sample_rate = 10000
        self.buffer_size = 512
        self.threshold_voltage = 2

        self.reaction_times = []
        self.cue_active = False
        self.reaction_start = None
        self.last_cue_time = time.time()
        self.random_delay = random.uniform(2, 5)
        self.full_time = []
        self.full_samples = []


        self._setup_plot()

    def _setup_plot(self):
        self.fig, (self.ax_signal, self.ax_reaction) = plt.subplots(2, 1, figsize=(15, 8))
        self.fig.suptitle("Reaction Time Tracker")

        self.line_signal, = self.ax_signal.plot([], [], lw=1)
        self.ax_signal.set_ylim(0, 3.5)
        self.ax_signal.set_ylabel("Button Voltage (V)")
        self.ax_signal.set_xlim(0)
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

        # self.ax_signal.set_autoscalex_on(True)

    def update_plot(self, t_axis, samples):

        if self.full_time:
            t_axis = t_axis + self.full_time[-1] + (1 / self.sample_rate)
        self.full_time.extend(t_axis)
        self.full_samples.extend(samples)

        self.line_signal.set_data(self.full_time, self.full_samples)
        self.ax_signal.set_xlim(0, self.full_time[-1])

        now = time.time()
        if not self.cue_active and (now - self.last_cue_time > self.random_delay):
            self.cue_active = True
            self.reaction_start = now
            self.cue_text.set_text("GO!")

        if self.cue_active and np.any(samples > self.threshold_voltage):
            rt_ms = (time.time() - self.reaction_start) * 1000
            self.reaction_times.append(rt_ms)
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
        PlotManager.on_release(self, event, self.ax_signal, self.full_time, self.full_samples)
        self.fig.canvas.draw()

    def _close_plot(self):
        plt.close(self.fig)
