"""
EMG Monitor with DWF Python — envelope only

• Band-pass filter (20–450 Hz)
• Full-wave rectify + moving-average envelope
• Displays only the envelope on a scrolling time axis
"""

import time
import numpy as np
import dwfpy as dwf
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy.signal import butter, lfilter

# ── FILTER HELPERS ────────────────────────────────────────────────────────────
def butter_bandpass(lowcut, highcut, fs, order=4):
    nyq = 0.5 * fs
    return butter(order, [lowcut/nyq, highcut/nyq], btype="band")

def bandpass_filter(data, lowcut, highcut, fs, order=4):
    b, a = butter_bandpass(lowcut, highcut, fs, order)
    return lfilter(b, a, data)

def moving_average(data, window_size):
    return np.convolve(data, np.ones(window_size)/window_size, mode="same")

# ── PLOT SETUP ────────────────────────────────────────────────────────────────
fig, ax_env = plt.subplots(figsize=(10, 4))
fig.suptitle("Real-time EMG Envelope")

line_env, = ax_env.plot([], [], lw=2)
ax_env.set_ylabel("EMG Envelope (V)")
ax_env.set_ylim(0, 0.1)
ax_env.set_xlabel("Time (s)")
ax_env.grid(True)

# ── GLOBALS ──────────────────────────────────────────────────────────────────
sample_rate        = 4000
buffer_size        = 2048
lowcut, highcut    = 20.0, 450.0
env_window_samples = int(0.15 * sample_rate)

env_time_vals, env_vals = [], []
sample_count = 0

# ── UPDATE FUNCTION ──────────────────────────────────────────────────────────
def update(_):
    global env_time_vals, env_vals, sample_count

    scope.read_status(read_data=True)
    raw = np.array(scope.channels[0].get_data())

    filt = bandpass_filter(raw, lowcut, highcut, sample_rate)
    rect = np.abs(filt)
    env  = moving_average(rect, env_window_samples)

    t_start = sample_count / sample_rate
    t_axis  = np.arange(buffer_size) / sample_rate + t_start
    sample_count += buffer_size

    # --- Accumulate and scroll envelope ---
    env_time_vals.append(t_axis[-1])
    env_vals.append(env[-1])

    if len(env_time_vals) > 200:
        env_time_vals = env_time_vals[-200:]
        env_vals      = env_vals[-200:]

    line_env.set_data(env_time_vals, env_vals)
    ax_env.set_xlim(env_time_vals[0], env_time_vals[-1])

    return line_env,

# ── RUN ───────────────────────────────────────────────────────────────────────
try:
    with dwf.Device() as device:
        print(f"Connected to {device.name} ({device.serial_number})")
        print("Connect EMG sensor to Oscilloscope IN1 (signal -> 1+, GND -> 1-)")

        # Enable analog IO power
        device.analog_io[0][1].value = 3.3
        device.analog_io[0][0].value = True
        device.analog_io.master_enable = True

        # Optional DIO setup
        device.digital_io.reset()
        for i in range(4):
            device.digital_io.channels[i].enabled = True
            device.digital_io.channels[i].output_state = bool((2 >> i) & 1)
        device.digital_io.configure()

        # Oscilloscope setup
        scope = device.analog_input
        scope[0].setup(range=0.01)
        scope.scan_shift(sample_rate=sample_rate,
                         buffer_size=buffer_size,
                         configure=True,
                         start=True)

        ani = FuncAnimation(fig, update, interval=50, blit=True)
        plt.tight_layout()
        plt.show()

except KeyboardInterrupt:
    print("\nEMG monitoring stopped by user.")
finally:
    plt.close()
