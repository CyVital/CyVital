
import time
import numpy as np
import dwfpy as dwf
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy.signal import find_peaks

print(f"DWF Version: {dwf.Application.get_version()}")

fig, (ax1, ax3) = plt.subplots(2, 1, figsize=(10, 8))
fig.suptitle('Heart Rate Monitor')

# Initialize empty data
bpm_values = []
time_values = []
peak_times = []
window_duration = 10  

# Store the sample rate as a global variable
sample_rate = 8192  # This should match the value used in scope.scan_shift()

# Set up the waveform plot
line1, = ax1.plot([], [], 'r-', label='Heart Signal')
peaks_plot, = ax1.plot([], [], 'bo', label='Peaks')
ax1.set_ylabel('Voltage (V)')
ax1.set_xlabel('Sample Index')
ax1.set_ylim(-0.15, 0.15)
ax1.grid(True)
ax1.legend()

# For the BPM plot
line3_bpm, = ax3.plot([], [], 'g-', linewidth=2, label='Heart Rate (BPM)')
ax3.set_ylabel('BPM')
ax3.set_xlabel('Time (s)')
ax3.set_ylim(40, 200)  # Typical heart rate range
ax3.grid(True)
ax3.legend()

# Add minor grid lines for more precise readings
ax1.grid(which='minor', linestyle=':', alpha=0.5)
ax3.grid(which='minor', linestyle=':', alpha=0.5)
ax1.minorticks_on()
ax3.minorticks_on()

# Add BPM text display
bpm_text = ax3.text(0.02, 0.9, 'BPM: --', transform=ax3.transAxes, 
                    fontsize=14, fontweight='bold', color='green',
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

# Update function for the animation
def update(frame):
    global time_values, bpm_values, peak_times
    
    status = scope.read_status(read_data=True)
    
    # Get data for channel 1 only (index 0)
    channel = scope.channels[0]  # Channel 1
    new_samples = np.array(channel.get_data())
    
    # Calculate metrics (still need these for debug output)
    dc = np.average(new_samples)
    dcrms = np.sqrt(np.average(new_samples**2))
    acrms = np.sqrt(np.average((new_samples - dc) ** 2))
    
    print(f"CH{channel.index + 1}: DC:{dc:.3f}V DCRMS:{dcrms:.3f}V ACRMS:{acrms:.3f}V")
    
    # Update waveform plot
    x = np.arange(len(new_samples))
    line1.set_data(x, new_samples)
    
    # Detect peaks (heartbeats)
    peaks, _ = find_peaks(new_samples, height=1.92, distance=200, prominence=0.01)
    
    # Plot detected peaks
    if len(peaks) > 0:
        peaks_plot.set_data(peaks, new_samples[peaks])
    else:
        peaks_plot.set_data([], [])
    
    # Calculate heart rate (BPM)
    current_time = time.time() - start_time
    time_values.append(current_time)
    
    # Add newly detected peaks to peak_times
    for peak_idx in peaks:
        peak_time = current_time - (len(new_samples) - peak_idx) / sample_rate
        peak_times.append(peak_time)
    
    # Keep only peaks within the last window_duration seconds
    cutoff_time = current_time - window_duration
    peak_times = [t for t in peak_times if t > cutoff_time]
    
    # Calculate BPM using RR intervals
    if len(peak_times) > 1:
        rr_intervals = np.diff(peak_times)  # Time differences between consecutive peaks
        avg_rr = np.mean(rr_intervals) if len(rr_intervals) > 0 else None
        
        if avg_rr and avg_rr > 0:
            bpm = 60 / avg_rr -270  # BPM = 60 / Average RR interval (seconds)
        else:
            bpm = 0
        
        bpm_values.append(bpm)
        bpm_text.set_text(f'BPM: {bpm:.1f}')
    else:
        bpm_values.append(0)
        bpm_text.set_text('BPM: --')
    
    ax1.set_xlim(0, len(new_samples))
    
    # Keep only the most recent data points
    if len(time_values) > 100:
        time_values = time_values[-100:]
        bpm_values = bpm_values[-100:]
    
    line3_bpm.set_data(time_values, bpm_values)
    
    if time_values:
        ax3.set_xlim(min(time_values), max(time_values))
    
    return line1, peaks_plot, line3_bpm, bpm_text

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
        
        scope = device.analog_input
        scope[0].setup(range=0.5)
        scope[1].setup(range=0.5)
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
    print("\nHeart rate monitoring stopped by user")
finally:
    plt.close()