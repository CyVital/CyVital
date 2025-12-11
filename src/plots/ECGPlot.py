from PlotManager import PlotManager
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import find_peaks
import time
from matplotlib.widgets import Cursor
from mpl_interactions import ioff, panhandler
from collections import deque

class ECGPlot(PlotManager):
    def __init__(self):
        super().__init__()
        # Initialize empty data
        self.bpm_values = []
        self.time_values = []
        self.peak_times = []
        self.raw_time_vals = []
        self.raw_vals = []
        self.window_duration = 10 
        self.start_time = None 

        self.raw_time = []
        self.raw_samples = []
        self.all_peak_times = []
        self.display_time = deque()
        self.recent_peak_times = []

        # Store the sample rate as a global variable
        self.sample_rate = 8192  # This should match the value used in scope.scan_shift()
        self._setup_plot()

    def _setup_plot(self):
        self.fig, (self.ax1, self.ax3) = plt.subplots(2, 1, figsize=(15, 8))
        self.fig.suptitle('Heart Rate Monitor')

        # Set up the waveform plot
        self.line1, = self.ax1.plot([], [], 'r-', label='Heart Signal')
        self.peaks_plot, = self.ax1.plot([], [], 'bo', label='Peaks')
        self.ax1.set_ylabel('Voltage (V)')
        self.ax1.set_xlabel('Sample Index')
        self.ax1.set_ylim(-0.15, 0.15)
        self.ax1.grid(True)
        self.ax1.legend()

        # For the BPM plot
        self.line3_bpm, = self.ax3.plot([], [], 'g-', linewidth=2, label='Heart Rate (BPM)')
        self.ax3.set_ylabel('BPM')
        self.ax3.set_xlabel('Time (s)')
        self.ax3.set_ylim(40, 200)  # Typical heart rate range
        self.ax3.grid(True)
        self.ax3.legend()

        # Add minor grid lines for more precise readings
        self.ax1.grid(which='minor', linestyle=':', alpha=0.5)
        self.ax3.grid(which='minor', linestyle=':', alpha=0.5)
        self.ax1.minorticks_on()
        self.ax3.minorticks_on()

        #Graph interactions
        self.cursor = Cursor(self.ax1, useblit=True, color='red', linewidth=1)
        self.cursor2 = Cursor(self.ax3, useblit=True, color='red', linewidth=1)
        self.zoom = self.zoom_around_cursor(self.ax1)
        self.zoom = self.zoom_around_cursor(self.ax3)
        self.pan_handler = panhandler(self.fig)

        self.fig.canvas.mpl_connect('button_press_event', self.on_press)
        self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)

        # Add BPM text display (to be transitioned to tkinter gui?)
        self.bpm_text = self.ax3.text(0.02, 0.9, 'BPM: --', transform=self.ax3.transAxes, 
                    fontsize=14, fontweight='bold', color='green',
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
        

    def update_plot(self, t_axis, samples):

        self.raw_time_vals.extend(t_axis)
        self.raw_vals.extend(samples)
        
        if self.start_time is None:
            self.start_time = time.time()

        self.raw_time.extend(t_axis.tolist())
        self.raw_samples.extend(samples.tolist())
        self.display_time.extend(t_axis.tolist())

        # Calculate metrics (still need these for debug output)
        dc = np.average(samples)
        dcrms = np.sqrt(np.average(samples**2))
        acrms = np.sqrt(np.average((samples - dc) ** 2))

        # Update waveform plot
        x = np.arange(len(samples))
        self.line1.set_data(t_axis, samples)

        # Detect peaks (heartbeats)
        peaks, _ = find_peaks(samples, height=1.92, distance=200, prominence=0.01)
    
        if len(peaks) > 0:
            peak_times = t_axis[peaks]
            peak_values = samples[peaks]
            self.peaks_plot.set_data(peak_times, peak_values)
        else:
            peak_times = np.array([], dtype=float)
            self.peaks_plot.set_data([], [])

        for peak_time in peak_times:
            self.all_peak_times.append(float(peak_time))

        time_data = np.array(self.display_time, dtype=float)

        current_time = time_data[-1] if time_data.size else 0.0
        cutoff_time = current_time - self.window_duration
        recent = [t for t in self.recent_peak_times if t >= cutoff_time]
        recent.extend(peak_times.tolist())
        self.recent_peak_times = recent

        if current_time is not None:
            self.time_values.append(current_time)

        bpm = None
        if len(self.recent_peak_times) > 1:
            rr_intervals = np.diff(self.recent_peak_times)
            avg_rr = float(np.mean(rr_intervals)) if len(rr_intervals) > 0 else None
            if avg_rr and avg_rr > 0:
                bpm = 60.0 / avg_rr
                self.bpm_values.append(bpm)
            else:
                self.bpm_values.append(np.nan)
        else:
            self.bpm_values.append(np.nan)

        finite_bpms = [value for value in self.bpm_values if np.isfinite(value)]
        if bpm is not None:
            self.latest_bpm = bpm
            self.bpm_text.set_text(f'BPM: {bpm:.1f}')
        else:
            self.latest_bpm = None
            self.bpm_text.set_text('BPM: --')

        self.avg_bpm = float(np.mean(finite_bpms)) if finite_bpms else None

        self.ax1.set_xlim(t_axis[0], t_axis[-1])
        self.line3_bpm.set_data(self.time_values, self.bpm_values)

        return self.line1, self.peaks_plot, self.line3_bpm, self.bpm_text
    
    def on_press(self, event):
        PlotManager.on_press(self, event, self.ax1)

    def on_release(self, event):
        PlotManager.on_release(self, event, self.ax1, self.raw_time_vals, self.raw_vals)
        self.fig.canvas.draw()
    
    def _close_plot(self):
        plt.close(self.fig)

    def plot_all(self):
        self.line1.set_data(self.raw_time_vals, self.raw_vals)
        self.line3_bpm.set_data(self.time_values, self.bpm_values)
        self.fig.canvas.draw()

    def save_data(self, filename):
        workbook, destination = self._create_workbook(filename)

        guide = workbook.add_worksheet("Read Me")
        guide.set_column(0, 0, 22)
        guide.set_column(1, 1, 95)
        guide.write(0, 0, "Worksheet")
        guide.write(0, 1, "How to use it")
        guide.write(1, 0, "Heart Rate Trend")
        guide.write(
            1,
            1,
            "Primary BPM estimate sampled once per refresh. Filter the column to focus on "
            "steady-state segments or copy into analysis tools.",
        )
        guide.write(2, 0, "Detected Peaks")
        guide.write(
            2,
            1,
            "Timestamps (in seconds) where a peak was located. Count intervals between rows "
            "to validate BPM calculations manually.",
        )
        guide.write(3, 0, "Raw Signal")
        guide.write(
            3,
            1,
            "Voltage data for every ECG sample with its time axis. Plot these columns to re-create "
            "the waveform or examine noise.",
        )
        if self.selected_samples.size > 0:
            guide.write(4, 0, "Selected Window")
            guide.write(
                4,
                1,
                "Appears when you drag-select a region in the GUI. Use it for zoomed-in analysis of "
                "interesting beats.",
            )

        trend_ws = workbook.add_worksheet("Heart Rate Trend")
        trend_ws.write_row(0, 0, ["Time (s)", "Heart Rate (BPM)"])
        for idx, (t_value, bpm) in enumerate(zip(self.time_values, self.bpm_values), start=1):
            trend_ws.write_row(idx, 0, [t_value, bpm])

        peaks_ws = workbook.add_worksheet("Detected Peaks")
        peaks_ws.write_row(0, 0, ["Peak Timestamp (s)"])
        for idx, peak_time in enumerate(self.all_peak_times, start=1):
            peaks_ws.write(idx, 0, peak_time)

        raw_ws = workbook.add_worksheet("Raw Signal")
        raw_ws.write_row(0, 0, ["Time (s)", "ECG Voltage (V)"])
        for idx, (t_value, sample) in enumerate(zip(self.raw_time, self.raw_samples), start=1):
            raw_ws.write_row(idx, 0, [t_value, sample])

        if self.selected_samples.size > 0:
            sel_ws = workbook.add_worksheet("Selected Window")
            sel_ws.write_row(0, 0, ["Time (s)", "ECG Voltage (V)"])
            for idx, (t_value, sample) in enumerate(zip(self.selected_times, self.selected_samples), start=1):
                sel_ws.write_row(idx, 0, [float(t_value), float(sample)])

        workbook.close()
        return str(destination)