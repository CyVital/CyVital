from collections import deque

from .PlotManager import PlotManager
import matplotlib.pyplot as plt
import numpy as np

try:
    from scipy.signal import find_peaks as scipy_find_peaks
except ImportError:  # pragma: no cover
    scipy_find_peaks = None


class ECGPlot(PlotManager):
    def __init__(self):
        super().__init__()
        # Initialize empty data
        self.bpm_values = []
        self.time_values = []
        self.all_peak_times = []
        self.recent_peak_times = []
        self.window_duration = 10
        self.display_window = 10
        self.raw_time = []
        self.raw_samples = []
        self.display_time = deque()
        self.display_samples = deque()
        self.max_display_points = 1200
        self.max_rate_points = 400
        self.latest_bpm = None
        self.avg_bpm = None

        # Store the sample rate as a global variable
        self.sample_rate = 8192  # This should match the value used in scope.scan_shift()
        self._setup_plot()

    def _setup_plot(self):
        self.fig, (self.ax1, self.ax3) = plt.subplots(2, 1, figsize=(10, 8))
        self.fig.suptitle('Heart Rate Monitor')

        # Set up the waveform plot
        self.line1, = self.ax1.plot([], [], 'r-', label='Heart Signal')
        self.peaks_plot, = self.ax1.plot([], [], 'bo', label='Peaks')
        self.ax1.set_ylabel('Voltage (V)')
        self.ax1.set_xlabel('Time (s)')
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

        # Add BPM text display (to be transitioned to tkinter gui?)
        self.bpm_text = self.ax3.text(0.02, 0.9, 'BPM: --', transform=self.ax3.transAxes, 
                    fontsize=14, fontweight='bold', color='green',
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
        

    def update_plot(self, t_axis, samples):

        if len(t_axis) == 0:
            return self.line1, self.peaks_plot, self.line3_bpm, self.bpm_text

        t_axis = np.asarray(t_axis, dtype=float)
        samples = np.asarray(samples, dtype=float)

        self.raw_time.extend(t_axis.tolist())
        self.raw_samples.extend(samples.tolist())
        self.display_time.extend(t_axis.tolist())
        self.display_samples.extend(samples.tolist())

        if self.display_time:
            cutoff = self.display_time[-1] - self.display_window
            while self.display_time and self.display_time[0] < cutoff:
                self.display_time.popleft()
                self.display_samples.popleft()

        # Update waveform plot with time axis
        time_data = np.array(self.display_time, dtype=float)
        sample_data = np.array(self.display_samples, dtype=float)
        time_plot = time_data
        sample_plot = sample_data
        if time_plot.size > self.max_display_points:
            time_plot, sample_plot = self._downsample_series(
                time_plot, sample_plot, self.max_display_points
            )
        if time_data.size > 0:
            self.line1.set_data(time_plot, sample_plot)
            self.ax1.set_xlim(max(0.0, time_data[-1] - self.display_window), time_data[-1])
            ymin, ymax = np.min(sample_data), np.max(sample_data)
            padding = max(0.02, 0.1 * (ymax - ymin)) if ymax > ymin else 0.05
            self.ax1.set_ylim(ymin - padding, ymax + padding)

        # Detect peaks (heartbeats) using dynamic thresholds
        baseline = float(np.median(samples))
        dynamic_range = float(np.ptp(samples))
        height = baseline + max(0.02, 0.45 * dynamic_range)
        prominence = max(0.01, 0.1 * dynamic_range)
        min_rr_seconds = 0.25
        distance = max(1, int(self.sample_rate * min_rr_seconds))

        peaks, _ = self._find_peaks(samples, height=height, distance=distance, prominence=prominence)

        if len(peaks) > 0:
            peak_times = t_axis[peaks]
            peak_values = samples[peaks]
            self.peaks_plot.set_data(peak_times, peak_values)
        else:
            peak_times = np.array([], dtype=float)
            self.peaks_plot.set_data([], [])

        for peak_time in peak_times:
            self.all_peak_times.append(float(peak_time))

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

        times = np.array(self.time_values, dtype=float)
        bpms = np.array(self.bpm_values, dtype=float)
        time_rate_plot = times
        bpm_rate_plot = bpms
        if time_rate_plot.size > self.max_rate_points:
            time_rate_plot, bpm_rate_plot = self._downsample_series(
                time_rate_plot, bpm_rate_plot, self.max_rate_points
            )
        self.line3_bpm.set_data(time_rate_plot, bpm_rate_plot)
        if times.size > 0:
            min_time = max(0.0, times[-1] - 60)
            max_time = times[-1] if times[-1] > min_time else min_time + 1
            self.ax3.set_xlim(min_time, max_time)

        return self.line1, self.peaks_plot, self.line3_bpm, self.bpm_text
    
    def _close_plot(self):
        plt.close(self.fig)

    def _find_peaks(self, samples, height=0.0, distance=1, prominence=0.0):
        """Use SciPy's find_peaks when available, otherwise fall back to a simple detector."""
        if scipy_find_peaks:
            return scipy_find_peaks(samples, height=height, distance=distance, prominence=prominence)

        # Basic fallback: detect local maxima above height and spaced by `distance` samples.
        samples = np.asarray(samples)
        candidate_indices = []
        last_idx = -distance
        for idx in range(1, len(samples) - 1):
            if samples[idx] < height:
                continue
            if samples[idx] <= samples[idx - 1] or samples[idx] <= samples[idx + 1]:
                continue
            if samples[idx] - samples[idx - 1] < prominence or samples[idx] - samples[idx + 1] < prominence:
                continue
            if idx - last_idx < distance:
                continue
            candidate_indices.append(idx)
            last_idx = idx
        return np.array(candidate_indices, dtype=int), {}

    def _downsample_series(self, time_data, sample_data, limit):
        if time_data.size <= limit:
            return time_data, sample_data
        idx = np.linspace(0, time_data.size - 1, limit, dtype=int)
        return time_data[idx], sample_data[idx]

#Save data in a readable way for users
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
        if self.selected_samples:
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

        if self.selected_samples:
            sel_ws = workbook.add_worksheet("Selected Window")
            sel_ws.write_row(0, 0, ["Time (s)", "ECG Voltage (V)"])
            for idx, (t_value, sample) in enumerate(zip(self.selected_times, self.selected_samples), start=1):
                sel_ws.write_row(idx, 0, [float(t_value), float(sample)])

        workbook.close()
        return str(destination)
