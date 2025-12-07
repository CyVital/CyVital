from PlotManager import PlotManager
import matplotlib.pyplot as plt
import numpy as np
from collections import deque
try:
    from scipy.signal import butter, filtfilt, find_peaks
except ImportError:  # fallback when SciPy missing
    butter = None
    filtfilt = None
    find_peaks = None
from matplotlib.widgets import Cursor
from mpl_interactions import ioff, panhandler
import matplotlib.ticker as plticker

class PulseOxPlot(PlotManager):
    def __init__(self):
        super().__init__()
        self.fs = 10  # sampling rate (Hz)
        self.window_size = int(self.fs * 5)  # 5-second window
        self.min_peak_distance = int(0.5 * self.fs)  
        self.bpm_hist = deque(maxlen=5) 
        self._scipy_warned = False

        # --- Buffers ---
        self.red_values = deque(maxlen=self.window_size)
        self.ir_values  = deque(maxlen=self.window_size)
        self.all_red_values = []
        self.all_ir_values = []
        self.window_times = deque(maxlen=self.window_size)
        self.all_times = []
        self.sample_index = 0

        self.all_bits = []


        # --- Band-pass filter design ---
        self.lowcut, self.highcut = 0.7, 4.0  # Hz
        self.nyq = self.fs / 2.0
        if butter is not None:
            self.b, self.a = butter(2, [self.lowcut/self.nyq, self.highcut/self.nyq], btype='band')
        else:
            self.b, self.a = None, None

        self.configure_history_window(window_seconds=self.window_size / self.fs)
        self._setup_plot()
        self.register_history_channel(
            channel="pulse_ir",
            axis=self.ax,
            line=self.line_ir,
            relative_to_window=False,
            max_points=self.window_size,
        )

    def _setup_plot(self):
        self.fig, (self.ax_dig, self.ax) = plt.subplots(2, 1, figsize=(10,8))
        
        self.line_red_dig, = self.ax_dig.step([], [], where='mid', label='Red Bits')
        self.ax_dig.set_title("Digital Signal")
        self.ax_dig.set_xlabel("Time step")
        self.ax_dig.set_ylabel("Bit Value")
        self.ax_dig.set_xlim(0, self.window_size)
        self.ax_dig.set_ylim(0, 1.1)
        self.ax_dig.xaxis.set_major_locator(plticker.MultipleLocator(base=8))
        self.ax_dig.yaxis.set_major_locator(plticker.MultipleLocator(base=1))
        self.ax_dig.grid(which='major', axis='both', linestyle='-', linewidth=0.5, color='gray')
        
        self.line_red, = self.ax.plot([], [], label='Red')
        self.line_ir,  = self.ax.plot([], [], label='IR')
        self.ax.set_title("MAX30101 Pulse Sensor Readings")
        self.ax.set_xlabel("Sample")
        self.ax.set_ylabel("Value")
        self.ax.set_xlim(0, self.window_size)
        self.ax.set_ylim(0, 100000)
        self.ax.legend(loc='upper right')
        self.ax.grid(True)

        self.cursor = Cursor(self.ax, useblit=True, color='red', linewidth=1)
        self.zoom = self.zoom_around_cursor(self.ax_dig)
        self.zoom2 = self.zoom_around_cursor(self.ax)
        self.pan_handler = panhandler(self.fig)

        # self.fig.canvas.mpl_connect('button_press_event', self.on_press)
        # self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        # self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)
    
    def update_plot(self, time_axis, samples):
        red = ((samples[0]<<16)|(samples[1]<<8)|samples[2]) & 0x03FFFF
        ir  = ((samples[3]<<16)|(samples[4]<<8)|samples[5]) & 0x03FFFF
        self.red_values.append(red)
        self.ir_values.append(ir)
        self.all_red_values.append(red)
        self.all_ir_values.append(ir)
        timestamp = self.sample_index / self.fs
        self.sample_index += 1
        self.window_times.append(timestamp)
        self.all_times.append(timestamp)
        self.record_history_samples("pulse_ir", [timestamp], [ir])

        #convert to binary
        bits = [(samples[0] >> i) & 1 for i in range(7, -1, -1)] + [(samples[1] >> i) & 1 for i in range(7, -1, -1)] +  [(samples[2] >> i) & 1 for i in range(7, -1, -1)] + [(samples[3] >> i) & 1 for i in range(7, -1, -1)] + [(samples[4] >> i) & 1 for i in range(7, -1, -1)] +  [(samples[5] >> i) & 1 for i in range(7, -1, -1)]
        self.all_bits.extend(bits)

        #set binary data
        self.line_red_dig.set_data(range(len(self.all_bits)), self.all_bits)
        start_idx = max(0, len(self.all_bits) - len(bits))
        self.ax_dig.set_xlim(start_idx, len(self.all_bits))

        # set data
        window_times = list(self.window_times)
        self.line_red.set_data(window_times, list(self.red_values))
        self.line_ir.set_data(window_times, list(self.ir_values))

        # compute vitals
        raw_bpm = self.estimate_bpm(self.ir_values)
        self.bpm     = self.smooth_bpm(raw_bpm)
        self.spo2    = self.estimate_spo2(self.red_values, self.ir_values)

        # rescale y
        current_max = max(max(self.red_values), max(self.ir_values))
        self.ax.set_ylim(0, current_max * 1.1)

        #rescale x
        if window_times:
            window_duration = self.window_size / self.fs
            latest_time = window_times[-1]
            self.ax.set_xlim(max(0.0, latest_time - window_duration), latest_time if latest_time > 0 else window_duration)

        return self.line_red, self.line_ir, self.line_red_dig
    
    def filtered_ir(self, buf):
        if self.b is None or self.a is None or filtfilt is None:
            if not self._scipy_warned:
                print("[PulseOxPlot] SciPy not installed; running without filtering or BPM estimation.")
                self._scipy_warned = True
            return np.asarray(buf, dtype=float)
        return filtfilt(self.b, self.a, np.array(buf))
    
    def estimate_bpm(self, ir_buf):
        if find_peaks is None or butter is None or filtfilt is None:
            return None
        x = self.filtered_ir(ir_buf)
        # require peaks with some prominence to avoid noise
        prom = np.std(x) * 0.5
        peaks, _ = find_peaks(x, distance=self.min_peak_distance, prominence=prom)
        if len(peaks) >= 5:
            # use last 4 intervals (5 peaks → 4 intervals)
            intervals = np.diff(peaks[-5:])
            avg_period = np.mean(intervals)
            return 60.0 * self.fs / avg_period
        return None
    
    def smooth_bpm(self, raw_bpm):
        if raw_bpm is not None:
            self.bpm_hist.append(raw_bpm)
        if self.bpm_hist:
            return np.mean(self.bpm_hist)
        return None
    
    def estimate_spo2(self, red_buf, ir_buf):
        r = np.array(red_buf)
        i = np.array(ir_buf)
        dc_r, dc_i = r.mean(), i.mean()
        ac_r, ac_i = r.max() - r.min(), i.max() - i.min()
        if ac_i > 0 and dc_r > 0 and dc_i > 0:
            R = (ac_r/dc_r) / (ac_i/dc_i)
            return 110.0 - 25.0 * R
        return None
    
    def on_press(self, event):
        PlotManager.on_press(self, event, self.ax)

    def on_release(self, event):
        PlotManager.on_release(self, event, self.ax, self.time, self.red_values)
        self.fig.canvas.draw()
    
    def _close_plot(self):
        plt.close(self.fig)
