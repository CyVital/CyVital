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

        self._setup_plot()

    def _setup_plot(self):
        self.fig, (self.ax_raw, self.ax_pressure) = plt.subplots(2, 1, figsize=(15, 8))

        self.line_raw, = self.ax_raw.plot([], [], lw=1)
        self.ax_raw.set_ylim(0, 1)
        self.ax_raw.set_ylabel("Voltage")
        self.ax_raw.set_xlabel("Time")
        self.ax_raw.grid(True)

        self.line_pressure = self.ax_pressure.plot([], [], lw=1)
        self.ax_pressure.setylim(0, 200)
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


    def on_press(self, event):
        PlotManager.on_press(self, event, self.ax_raw)

    def on_release(self, event):
        PlotManager.on_release(self, event, self.ax_raw, self.full_times, self.raw_volts)
        self.fig.canvas.draw()

    def _close_plot(self):
        plt.close(self.fig)