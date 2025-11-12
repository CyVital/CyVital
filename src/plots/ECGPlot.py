from PlotManager import PlotManager
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import find_peaks
import time

class ECGPlot(PlotManager):
    def __init__(self):
        # Initialize empty data
        self.bpm_values = []
        self.time_values = []
        self.peak_times = []
        self.window_duration = 10 
        self.start_time = None 

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

        # Add BPM text display (to be transitioned to tkinter gui?)
        self.bpm_text = self.ax3.text(0.02, 0.9, 'BPM: --', transform=self.ax3.transAxes, 
                    fontsize=14, fontweight='bold', color='green',
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))
        

    def update_plot(self, t_axis, samples):

        if self.start_time is None:
            self.start_time = time.time()

        # Calculate metrics (still need these for debug output)
        dc = np.average(samples)
        dcrms = np.sqrt(np.average(samples**2))
        acrms = np.sqrt(np.average((samples - dc) ** 2))

        # Update waveform plot
        x = np.arange(len(samples))
        self.line1.set_data(x, samples)

        # Detect peaks (heartbeats)
        peaks, _ = find_peaks(samples, height=1.92, distance=200, prominence=0.01)
    
        # Plot detected peaks
        if len(peaks) > 0:
            self.peaks_plot.set_data(peaks, samples[peaks])
        else:
            self.peaks_plot.set_data([], [])

        # Calculate heart rate (BPM)
        current_time = time.time() - self.start_time
        self.time_values.append(current_time)

        # Add newly detected peaks to peak_times
        for peak_idx in peaks:
            peak_time = current_time - (len(samples) - peak_idx) / self.sample_rate
            self.peak_times.append(peak_time)

        # Keep only peaks within the last window_duration seconds
        cutoff_time = current_time - self.window_duration
        self.peak_times = [t for t in self.peak_times if t > cutoff_time]

        # Calculate BPM using RR intervals
        if len(self.peak_times) > 1:
            rr_intervals = np.diff(self.peak_times)  # Time differences between consecutive peaks
            avg_rr = np.mean(rr_intervals) if len(rr_intervals) > 0 else None
            
            if avg_rr and avg_rr > 0:
                bpm = 60 / avg_rr -270  # BPM = 60 / Average RR interval (seconds)
            else:
                bpm = 0
            
            self.bpm_values.append(bpm)
            self.bpm_text.set_text(f'BPM: {bpm:.1f}')
        else:
            self.bpm_values.append(0)
            self.bpm_text.set_text('BPM: --')

        self.ax1.set_xlim(0, len(samples))
        self.line3_bpm.set_data(self.time_values, self.bpm_values)

        return self.line1, self.peaks_plot, self.line3_bpm, self.bpm_text
    
    def on_press(self, event):
        PlotManager.on_press(self, event, self.ax1)

    def on_release(self, event):
        PlotManager.on_release(self, event, self.ax1, self.full_time, self.full_samples)
        self.fig.canvas.draw()
    
    def _close_plot(self):
        plt.close(self.fig)
