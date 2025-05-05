"""
Heart Rate Monitor with DWF Python and Real-time Plotting
Filtered ECG + peak detection for BPM estimation
"""
import time
import numpy as np
import dwfpy as dwf
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy.signal import find_peaks, butter, filtfilt

print(f"DWF Version: {dwf.Application.get_version()}")

# ── Globals ───────────────────────────────────────────────────────────────
sample_rate = 10000
window_duration = 10  # BPM averaging window (seconds)
signal_time = 0.0     # Logical time (accumulated sample time)
bpm_values, time_values, peak_times = [], [], []

# ── Filter Functions ───────────────────────────────────────────────────────
def butter_bandpass(lowcut, highcut, fs, order=2):
    nyq = 0.5 * fs
    return butter(order, [lowcut / nyq, highcut / nyq], btype='band')

def apply_bandpass_filter(data, lowcut=0.5, highcut=40.0, fs=10000, order=2):
    b, a = butter_bandpass(lowcut, highcut, fs, order)
    return filtfilt(b, a, data)

# ── Peak Detection ─────────────────────────────────────────────────────────
def detect_ecg_peaks(signal, sample_rate, min_prominence=0.1, min_height=0.05):
    min_distance = int(sample_rate * 0.4)  # ~150 BPM max
    peaks, _ = find_peaks(signal, distance=min_distance, prominence=min_prominence, height=min_height)
    return peaks

def calculate_bpm(peak_times, current_time, window_duration=10):
    peak_times = [t for t in peak_times if t > current_time - window_duration]
    if len(peak_times) > 1:
        rr_intervals = np.diff(peak_times)
        avg_rr = np.mean(rr_intervals)
        bpm = 60 / avg_rr if avg_rr > 0 else 0
        return bpm, peak_times
    return 0, peak_times

# ── Plot Setup ─────────────────────────────────────────────────────────────
fig, (ax1, ax3) = plt.subplots(2, 1, figsize=(10, 8))
fig.suptitle('Heart Rate Monitor')

line1, = ax1.plot([], [], 'r-', label='Heart Signal')
peaks_plot, = ax1.plot([], [], 'bo', label='Peaks')
ax1.set_ylabel('Voltage (V)')
ax1.set_xlabel('Sample Index')
ax1.set_ylim(-0.15, 0.15)
ax1.grid(True)
ax1.legend()
ax1.minorticks_on()
ax1.grid(which='minor', linestyle=':', alpha=0.5)

line3_bpm, = ax3.plot([], [], 'g-', linewidth=2, label='Heart Rate (BPM)')
ax3.set_ylabel('BPM')
ax3.set_xlabel('Time (s)')
ax3.set_ylim(40, 200)
ax3.grid(True)
ax3.legend()
ax3.minorticks_on()
ax3.grid(which='minor', linestyle=':', alpha=0.5)
bpm_text = ax3.text(0.02, 0.9, 'BPM: --', transform=ax3.transAxes, 
                    fontsize=14, fontweight='bold', color='green',
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

# ── Update Function ─────────────────────────────────────────────────────────
def update(frame):
    global time_values, bpm_values, peak_times, signal_time

    scope.read_status(read_data=True)
    channel = scope.channels[0]
    raw_samples = np.array(channel.get_data())

    if len(raw_samples) > 60:
        filtered_samples = apply_bandpass_filter(raw_samples, fs=sample_rate)
    else:
        filtered_samples = raw_samples

    signal_time += len(filtered_samples) / sample_rate

    x = np.arange(len(filtered_samples))
    line1.set_data(x, filtered_samples)
    ax1.set_xlim(0, len(filtered_samples))

    peaks = detect_ecg_peaks(filtered_samples, sample_rate)

    if len(peaks) > 0:
        peaks_plot.set_data(peaks, filtered_samples[peaks])
    else:
        peaks_plot.set_data([], [])

    current_time = time.time() - start_time
    time_values.append(current_time)

    for peak_idx in peaks:
        peak_time = signal_time - (len(filtered_samples) - peak_idx) / sample_rate
        peak_times.append(peak_time)

    bpm, peak_times = calculate_bpm(peak_times, signal_time, window_duration)
    bpm_values.append(bpm)
    bpm_text.set_text(f'BPM: {bpm:.1f}' if bpm > 0 else 'BPM: --')

    if len(time_values) > 100:
        time_values = time_values[-100:]
        bpm_values = bpm_values[-100:]

    line3_bpm.set_data(time_values, bpm_values)
    if time_values:
        ax3.set_xlim(min(time_values), max(time_values))

    return line1, peaks_plot, line3_bpm, bpm_text

# ── Main Execution ──────────────────────────────────────────────────────────
try:
    with dwf.Device() as device:
        print(f"Found device: {device.name} ({device.serial_number})")
        print("Connect heart rate sensor to Oscilloscope input 1: Signal to 1+, GND to 1-")

        wavegen = device.analog_output
        wavegen[0].setup(function="sine", frequency=1.25, amplitude=0.05, offset=0.0)
        wavegen[0].setup_am(function="triangle", frequency=0.1, amplitude=20)
        wavegen[0].configure(start=True)

        device.analog_io[0][1].value = 3.3
        device.analog_io[0][0].value = True
        device.analog_io.master_enable = True

        device.digital_io.reset()
        for i in range(4):
            device.digital_io.channels[i].enabled = True
            device.digital_io.channels[i].output_state = bool((0 >> i) & 1)
        device.digital_io.configure()

        scope = device.analog_input
        scope[0].setup(range=0.1)
        scope[1].setup(range=0.3)
        scope.scan_shift(sample_rate=sample_rate, buffer_size=4096, configure=True, start=True)

        def on_key(event):
            if event.key == 'a':
                for ax in [ax1, ax3]:
                    ymin, ymax = ax.get_ylim()
                    center = (ymax + ymin) / 2
                    range_val = (ymax - ymin) * 0.8
                    ax.set_ylim(center - range_val/2, center + range_val/2)
                fig.canvas.draw_idle()
            elif event.key == 'z':
                for ax in [ax1, ax3]:
                    ymin, ymax = ax.get_ylim()
                    center = (ymax + ymin) / 2
                    range_val = (ymax - ymin) * 1.2
                    ax.set_ylim(center - range_val/2, center + range_val/2)
                fig.canvas.draw_idle()

        fig.canvas.mpl_connect('key_press_event', on_key)

        start_time = time.time()
        ani = FuncAnimation(fig, update, frames=None, interval=100, blit=True, cache_frame_data=False)

        plt.tight_layout()
        plt.show()

except KeyboardInterrupt:
    print("\nHeart rate monitoring stopped by user.")
finally:
    if device and device.digital_io:
        device.digital_io.reset()
        device.digital_io.configure()
    plt.close()
