from PlotManager import PlotManager
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import find_peaks
import time
from matplotlib.widgets import Cursor
from mpl_interactions import ioff, panhandler

class BloodPressurePlot(PlotManager):\

    def __init__(self):
        super().__init__()

        self.full_times = []
        self.raw_volts = []
        self.pressures = []

        self.m = 1
        self.window_size = 200

        self._setup_plot()

    def _setup_plot(self):
        self.fig, (self.ax_raw, self.ax_pressure) = plt.subplots(2, 1, figsize=(15, 8))

        self.line_raw, = self.ax_raw.plot([], [], lw=1)
        self.ax_raw.set_ylim(0, 1)
        self.ax_raw.set_ylabel("Voltage")
        self.ax_raw.set_xlabel("Time")
        self.ax_raw.grid(True)

        self.line_pressure = self.ax_pressure.plot([], [], lw=1)
        self.ax_pressure.set_ylim(0, 200)
        self.ax_pressure.set_ylabel("Pressure")
        self.ax_pressure.set_xlabel("Time")
        self.ax_pressure.grid(True)

        self.cursor = Cursor(self.ax_raw, useblit=True, color='red', linewidth=1)
        self.zoom = self.zoom_around_cursor(self.ax_raw)
        self.cursor2 = Cursor(self.ax_pressure, useblit=True, color='red', linewidth=1)
        self.zoom2 = self.zoom_around_cursor(self.ax_pressure)
        self.pan_handler = panhandler(self.fig)

        self.fig.canvas.mpl_connect('button_press_event', self.on_press)
        self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)

    def update_plot(self, t_axis, samples):
        self.full_times.extend(t_axis)
        self.raw_volts.extend(samples)
        new_pressures = self._calc_pressure(samples)
        self.pressures.extend(new_pressures)

        self.line_raw.set_data(self.full_times[-self.window_size:], self.raw_volts[-self.window_size:])
        self.line_pressure.set_data(self.full_times[-self.window_size:], self.pressures[-self.window_size:])

        return self.line_raw, self.line_pressure
    
    def _calc_pressure(self, samples):
        pressure_samples = []
        for sample in samples:
            pressure_samples.append(sample * self.m)
        return pressure_samples
    
    def plot_all(self, event):
        self.line_raw.set_data(self.full_times, self.raw_volts)
        self.line_pressure.set_data(self.full_times, self.pressures)
    
    def shift_review_window(self, direction):
        self.ax_raw.set_xlim(*(limit + (direction * 50) for limit in self.ax_raw.get_xlim()))
        self.ax_pressure.set_xlim(*(limit + (direction * 50) for limit in self.ax_pressure.get_xlim()))
        return True
    
    def on_press(self, event):
        PlotManager.on_press(self, event, self.ax_raw)

    def on_release(self, event):
        PlotManager.on_release(self, event, self.ax_raw, self.full_times, self.raw_volts)
        self.fig.canvas.draw()

    def _close_plot(self):
        plt.close(self.fig)