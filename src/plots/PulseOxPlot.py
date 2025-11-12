from PlotManager import PlotManager
import matplotlib.pyplot as plt
import numpy as np
from collections import deque
from scipy.signal import butter, filtfilt, find_peaks

class PulseOxPlot(PlotManager):
    def __init__(self):
        self.window_size = 100
        self.fs = 10  # sampling rate (Hz)
        self.min_peak_distance = int(0.5 * self.fs)  
        self.bpm_hist = deque(maxlen=5) 

        # --- Buffers ---
        self.red_values = deque([0]*self.window_size, maxlen=self.window_size)
        self.ir_values  = deque([0]*self.window_size, maxlen=self.window_size)

        # --- Band‑pass filter design ---
        self.lowcut, self.highcut = 0.7, 4.0  # Hz
        self.nyq = self.fs / 2.0
        self.b, self.a = butter(2, [self.lowcut/self.nyq, self.highcut/self.nyq], btype='band')

        self._setup_plot()

    def _setup_plot(self):
        self.fig, self.ax = plt.subplots(figsize=(8,5))
        self.line_red, = self.ax.plot([], [], label='Red')
        self.line_ir,  = self.ax.plot([], [], label='IR')
        self.ax.set_title("MAX30101 Pulse Sensor Readings")
        self.ax.set_xlabel("Sample")
        self.ax.set_ylabel("Value")
        self.ax.set_xlim(0, self.window_size)
        self.ax.set_ylim(0, 100000)
        self.ax.legend(loc='upper right')

        # Text placeholders (to be put in base gui)
        self.hr_text   = self.ax.text(0.02, 0.95, "", transform=self.ax.transAxes)
        self.spo2_text = self.ax.text(0.02, 0.90, "", transform=self.ax.transAxes)
    
    def update_plot(self, red, ir):
        self.red_values.append(red)
        self.ir_values.append(ir)

        xs = range(len(self.red_values))
        self.line_red.set_data(xs, self.red_values)
        self.line_ir.set_data(xs, self.ir_values)

        # compute vitals
        raw_bpm = self.estimate_bpm(self.ir_values)
        bpm     = self.smooth_bpm(raw_bpm)
        spo2    = self.estimate_spo2(self.red_values, self.ir_values)

        self.hr_text.set_text(f"HR: {bpm:.0f} bpm" if bpm else "HR: -- bpm")
        self.spo2_text.set_text(f"SpO₂: {spo2:.1f} %" if spo2 else "SpO₂: -- %")

        # rescale y
        current_max = max(max(self.red_values), max(self.ir_values))
        self.ax.set_ylim(0, current_max * 1.1)

        return self.line_red, self.line_ir, self.hr_text, self.spo2_text
    
    def filtered_ir(self, buf):
        return filtfilt(self.b, self.a, np.array(buf))
    
    def estimate_bpm(self, ir_buf):
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
        PlotManager.on_release(self, event, self.ax, self.full_time, self.full_samples)
        self.fig.canvas.draw()
    
    def _close_plot(self):
        plt.close(self.fig)