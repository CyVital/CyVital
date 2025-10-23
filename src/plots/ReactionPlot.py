import time
import random
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Cursor
from mpl_interactions import ioff, panhandler, zoom_factory
from matplotlib.patches import Rectangle

class ReactionPlot:
    def __init__(self):
        self.sample_rate = 10000
        self.buffer_size = 512
        self.threshold_voltage = 2

        self.reaction_times = []
        self.cue_active = False
        self.reaction_start = None
        self.last_cue_time = time.time()
        self.random_delay = random.uniform(2, 5)

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
        self.zoom = zoom_factory(self.ax_signal)
        self.pan_handler = panhandler(self.fig)

        self.fig.canvas.mpl_connect('button_press_event', self.on_press)
        self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)

        self.selection_start = 0
        self.seleection_rect = None
        self.selection_end = 0

    def update_reaction_plot(self, t_axis, samples):
        self.line_signal.set_data(t_axis, samples)
        self.ax_signal.set_xlim(t_axis[0], t_axis[-1])

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
        if event.button == 1:
            if event.inaxes == self.ax_signal:
                self.selection_start = event.xdata
                print(f"Selection started at x = {self.selection_start}")
                if self.selection_rect:
                    self.selection_rect.remove()
                    self.selection_rect = None
        elif self.selection_rect:
            self.selection_rect.remove()
            self.selection_rect = None

    def on_release(self, event):
        if event.inaxes == self.ax_signal and self.selection_start is not None and event.button == 1:
            self.selection_end = event.xdata
            print(f"Selection ended at x = {self.selection_end}")

            # Get full height of the plot
            y_min, y_max = self.ax_signal.get_ylim()

            # Calculate rectangle position and width
            x0 = min(self.selection_start, self.selection_end)
            width = abs(self.selection_end - self.selection_start)

            # # Extract selected data
            # mask = (time_ms >= x0) & (time_ms <= x0 + width)
            # selected_times = time_ms[mask]
            # selected_ir = ir_values[mask]

            # Draw rectangle spanning full height
            self.selection_rect = Rectangle((x0, y_min), width, y_max - y_min,
                                    linewidth=1, edgecolor='blue', facecolor='lightblue', alpha=0.5)
            self.ax_signal.add_patch(self.selection_rect)
            self.fig.canvas.draw()

    def on_scroll(self, event):
        if self.selection_rect:
            self.selection_rect.remove()
            self.selection_rect = None 

    def _close_plot(self):
        plt.close(self.fig)
