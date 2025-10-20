import time
import random
import matplotlib.pyplot as plt
import numpy as np

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
        self.fig, (self.ax_signal, self.ax_reaction) = plt.subplots(2, 1, figsize=(10, 6))
        self.fig.suptitle("Reaction Time Tracker")

        self.line_signal, = self.ax_signal.plot([], [], lw=1)
        self.ax_signal.set_ylim(0, 3.5)
        self.ax_signal.set_ylabel("Button Voltage (V)")
        self.ax_signal.set_xlim(0, self.buffer_size / self.sample_rate)
        self.ax_signal.grid(True)

        self.ax_reaction.set_ylim(0, 1000)
        self.ax_reaction.set_xlim(0, 10)
        self.ax_reaction.set_ylabel("Reaction Time (ms)")
        self.ax_reaction.set_xlabel("Trial")
        self.ax_reaction.grid(True)

        self.cue_text = self.ax_signal.text(0.02, 0.9, '', transform=self.ax_signal.transAxes, fontsize=14, color='red')

    def update_plot(self, t_axis, samples):
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
            self._update_reaction_plot()

        return self.line_signal, self.cue_text

    def _update_reaction_plot(self):
        self.ax_reaction.clear()
        self.ax_reaction.set_ylim(0, 1000)
        self.ax_reaction.set_xlim(0, max(10, len(self.reaction_times)))
        self.ax_reaction.set_ylabel("Reaction Time (ms)")
        self.ax_reaction.set_xlabel("Trial")
        self.ax_reaction.grid(True)
        self.ax_reaction.scatter(range(1, len(self.reaction_times) + 1), self.reaction_times, color='blue')

    def _close_plot(self):
        plt.close(self.fig)
