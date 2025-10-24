import time
import numpy as np
import dwfpy as dwf
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy.signal import butter, lfilter
from PlotManager import PlotManager

class EMGPlot(PlotManager):
    def __init__(self):
        # Plot set-up
        fig, ax_env = plt.subplots(figsize=(10, 4))
        fig.suptitle("Real-time EMG Envelope")

        line_env, = ax_env.plot([], [], lw=2)
        ax_env.set_ylabel("EMG Envelope (V)")
        ax_env.set_ylim(0, 0.1)
        ax_env.set_xlabel("Time (s)")
        ax_env.grid(True)

        # globals
        self.sample_rate        = 4000
        self.buffer_size        = 2048
        self.lowcut, self.highcut    = 20.0, 450.0
        self.env_window_samples = int(0.15 * self.sample_rate)

        self.env_time_vals, self.env_vals = [], []
        self.sample_count = 0