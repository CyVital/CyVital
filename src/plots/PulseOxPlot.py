from PlotManager import PlotManager
import matplotlib.pyplot as plt
import numpy as np
from collections import deque
from scipy.signal import butter, filtfilt, find_peaks
from matplotlib.widgets import Cursor
from mpl_interactions import ioff, panhandler
import matplotlib.ticker as plticker

class PulseOxPlot(PlotManager):
    def __init__(self):
        super().__init__()
        self.window_size = 100
        self.fs = 10  # sampling rate (Hz)
        self.min_peak_distance = int(0.5 * self.fs)  
        self.bpm_hist = deque(maxlen=5) 

        # --- Buffers ---
        self.red_values = deque([0]*self.window_size, maxlen=self.window_size)
        self.ir_values  = deque([0]*self.window_size, maxlen=self.window_size)
        self.all_red_values = []
        self.all_ir_values = []
        self.all_time = []

        self.all_bits = []

        self.selected_ir = [] #selected_samples of PlotManager is selected red


        # --- Band‑pass filter design ---
        self.lowcut, self.highcut = 0.7, 4.0  # Hz
        self.nyq = self.fs / 2.0
        self.b, self.a = butter(2, [self.lowcut/self.nyq, self.highcut/self.nyq], btype='band')

        self._setup_plot()

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

        self.fig.canvas.mpl_connect('button_press_event', self.on_press)
        self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)
    
    def update_plot(self, time_axis, samples):
        red = ((samples[0]<<16)|(samples[1]<<8)|samples[2]) & 0x03FFFF
        ir  = ((samples[3]<<16)|(samples[4]<<8)|samples[5]) & 0x03FFFF
        self.red_values.append(red)
        self.ir_values.append(ir)
        self.all_red_values.append(red)
        self.all_ir_values.append(ir)
        self.all_time = time_axis

        #convert to binary
        bits = [(samples[0] >> i) & 1 for i in range(7, -1, -1)] + [(samples[1] >> i) & 1 for i in range(7, -1, -1)] +  [(samples[2] >> i) & 1 for i in range(7, -1, -1)] + [(samples[3] >> i) & 1 for i in range(7, -1, -1)] + [(samples[4] >> i) & 1 for i in range(7, -1, -1)] +  [(samples[5] >> i) & 1 for i in range(7, -1, -1)]
        self.all_bits.extend(bits)

        #set binary data
        self.line_red_dig.set_data(range(len(self.all_bits) - self.window_size, len(self.all_bits)), self.all_bits[-self.window_size:])
        self.ax_dig.set_xlim(len(self.all_bits) - len(bits), len(self.all_bits))

        # set data
        # xs = range(len(self.red_values))
        self.line_red.set_data(time_axis[-self.window_size:], self.all_red_values[-self.window_size:])
        self.line_ir.set_data(time_axis[-self.window_size:], self.all_ir_values[-self.window_size:])

        # compute vitals
        raw_bpm = self.estimate_bpm(self.ir_values)
        self.bpm     = self.smooth_bpm(raw_bpm)
        self.spo2    = self.estimate_spo2(self.red_values, self.ir_values)

        # rescale y
        current_max = max(max(self.red_values), max(self.ir_values))
        self.ax.set_ylim(0, current_max * 1.1)

        #rescale x
        self.ax.set_xlim(time_axis[-1] - self.window_size, time_axis[-1])

        return self.line_red, self.line_ir, self.line_red_dig
    
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
    
    def plot_all(self):
        self.line_red_dig.set_data(range(len(self.all_bits)), self.all_bits)
        self.line_red.set_data(self.all_time, self.all_red_values)
        self.line_ir.set_data(self.all_time, self.all_ir_values)
    
    def on_press(self, event):
        PlotManager.on_press(self, event, self.ax)

    def on_release(self, event):
        mask = PlotManager.on_release(self, event, self.ax, self.all_time, self.all_red_values)
        ir_array = np.array(self.all_ir_values)
        self.selected_ir = ir_array[mask]
        self.fig.canvas.draw()

    def save_data(self, filename):
        workbook, destination = self._create_workbook(filename)
        worksheet = workbook.add_worksheet()
        worksheet.write(0, 0, "Times")
        worksheet.write(0, 1, "Red")
        worksheet.write(0, 2, "IR")
        for i in range(1, len(self.selected_samples)):
            worksheet.write(i, 0, self.selected_times[i])
            worksheet.write(i, 1, self.selected_samples[i])
            worksheet.write(i, 2, self.selected_ir[i])
        workbook.close()
        return str(destination)
    
    def _close_plot(self):
        plt.close(self.fig)