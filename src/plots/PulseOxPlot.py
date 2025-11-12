from PlotManager import PlotManager
from collections import deque
import numpy as np
from scipy.signal import butter, filtfilt, find_peaks

class PulseOxPlot(PlotManager):
    def __init__(self):
        self.MAX_ADDR_7BIT = 0x57
        self.MAX_ADDR_8BIT = self.MAX_ADDR_7BIT << 1  # 0xAE
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