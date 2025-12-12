import time
import numpy as np
import dwfpy as dwf
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy.signal import butter, lfilter
from PlotManager import PlotManager
from matplotlib.widgets import Cursor
from mpl_interactions import ioff, panhandler

class EMGPlot(PlotManager):
    def __init__(self):
        super().__init__()
        # globals
        self.sample_rate        = 4000
        self.buffer_size        = 2048
        self.lowcut, self.highcut    = 20.0, 450.0
        self.env_window_samples = int(0.15 * self.sample_rate)

        self.env_time_vals, self.raw_time_vals, self.env_vals, self.raw_vals = [], [], [], []
        self.sample_count = 0
        self.window_size = 20

        self._setup_plot()

    def _setup_plot(self):
        # Plot set-up
        self.fig, (self.ax_raw, self.ax_env) = plt.subplots(2, 1, figsize=(15, 8))
        self.fig.suptitle("Real-time EMG Envelope")

        self.line_raw, = self.ax_raw.plot([], [], lw=2)
        self.ax_raw.set_ylabel("Raw EMG (V)")
        self.ax_raw.set_ylim(0, 0.1)
        self.ax_raw.set_xlabel("Time (s)")
        self.ax_raw.grid(True)

        self.line_env, = self.ax_env.plot([], [], lw=2)
        self.ax_env.set_ylabel("EMG Envelope (V)")
        self.ax_env.set_ylim(0, 0.1)
        self.ax_env.set_xlabel("Time (s)")
        self.ax_env.grid(True)

        self.cursor = Cursor(self.ax_raw, useblit=True, color='red', linewidth=1)
        self.cursor2 = Cursor(self.ax_env, useblit=True, color='red', linewidth=1)
        self.zoom = self.zoom_around_cursor(self.ax_raw)
        self.zoom2 = self.zoom_around_cursor(self.ax_env)
        self.pan_handler = panhandler(self.fig)

        self.fig.canvas.mpl_connect('button_press_event', self.on_press)
        self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)

    def update_plot(self, t_axis, samples):

        self.raw_time_vals.extend(t_axis)
        self.raw_vals.extend(samples)
        
        filt = self._bandpass_filter(samples, self.sample_rate)
        rect = np.abs(filt)
        env  = self._moving_average(rect)
        
        self.env_time_vals.append(t_axis[-1])
        self.env_vals.append(env[-1])

        self.line_raw.set_data(t_axis, samples)
        self.ax_raw.set_xlim(t_axis[0], t_axis[-1])

        self.line_env.set_data(self.env_time_vals[-self.window_size:], self.env_vals[-self.window_size:])

        try:
            self.ax_env.set_xlim(self.env_time_vals[-self.window_size], self.env_time_vals[-1])
        except IndexError:
             self.ax_env.set_xlim(self.env_time_vals[0], self.env_time_vals[-1])

        return self.line_raw, self.line_env
    
    def plot_all(self):
        self.line_raw.set_data(self.raw_time_vals, self.raw_vals)
        self.line_env.set_data(self.env_time_vals, self.env_vals)
    
    def shift_review_window(self, direction):
        self.ax_raw.set_xlim(*(limit + (direction * 10) for limit in self.ax_raw.get_xlim()))
        self.ax_env.set_xlim(*(limit + (direction * 10) for limit in self.ax_env.get_xlim()))
        return True
    
    def on_press(self, event):
        PlotManager.on_press(self, event, self.ax_raw)

    def on_release(self, event):
        PlotManager.on_release(self, event, self.ax_raw, self.raw_time_vals, self.raw_vals)
        self.fig.canvas.draw()
    
    def _close_plot(self):
        plt.close(self.fig)


    # ── FILTER HELPERS ────────────────────────────────────────────────────────────
    def _butter_bandpass(self, fs, order=4):
        nyq = 0.5 * fs
        return butter(order, [self.lowcut/nyq, self.highcut/nyq], btype="band")

    def _bandpass_filter(self, data, fs, order=4):
        b, a = self._butter_bandpass(fs, order)
        return lfilter(b, a, data)

    def _moving_average(self, data):
        return np.convolve(data, np.ones(self.env_window_samples)/self.env_window_samples, mode="same")