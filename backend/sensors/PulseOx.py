import dwfpy as dwf
from dwfpy.protocols import Protocols
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from scipy.signal import butter, filtfilt, find_peaks
from collections import deque
# import Emg as ps

MAX_ADDR_7BIT = 0x57
MAX_ADDR_8BIT = MAX_ADDR_7BIT << 1  # 0xAE

window_size = 100
fs = 10  # sampling rate (Hz)
min_peak_distance = int(0.5 * fs)  
bpm_hist = deque(maxlen=5)       

# --- Buffers ---
red_values = deque([0]*window_size, maxlen=window_size)
ir_values  = deque([0]*window_size, maxlen=window_size)

# --- Band‑pass filter design ---
lowcut, highcut = 0.7, 4.0  # Hz
nyq = fs / 2.0
b, a = butter(2, [lowcut/nyq, highcut/nyq], btype='band')

def filtered_ir(buf):
    return filtfilt(b, a, np.array(buf))

def estimate_bpm(ir_buf):
    x = filtered_ir(ir_buf)
    # require peaks with some prominence to avoid noise
    prom = np.std(x) * 0.5
    peaks, _ = find_peaks(x, distance=min_peak_distance, prominence=prom)
    if len(peaks) >= 5:
        # use last 4 intervals (5 peaks → 4 intervals)
        intervals = np.diff(peaks[-5:])
        avg_period = np.mean(intervals)
        return 60.0 * fs / avg_period
    return None

def smooth_bpm(raw_bpm):
    if raw_bpm is not None:
        bpm_hist.append(raw_bpm)
    if bpm_hist:
        return np.mean(bpm_hist)
    return None

def estimate_spo2(red_buf, ir_buf):
    r = np.array(red_buf)
    i = np.array(ir_buf)
    dc_r, dc_i = r.mean(), i.mean()
    ac_r, ac_i = r.max() - r.min(), i.max() - i.min()
    if ac_i > 0 and dc_r > 0 and dc_i > 0:
        R = (ac_r/dc_r) / (ac_i/dc_i)
        return 110.0 - 25.0 * R
    return None

# --- Plot setup ---
fig, ax = plt.subplots(figsize=(8,5))
line_red, = ax.plot([], [], label='Red')
line_ir,  = ax.plot([], [], label='IR')
ax.set_title("MAX30101 Pulse Sensor Readings")
ax.set_xlabel("Sample")
ax.set_ylabel("Value")
ax.set_xlim(0, window_size)
ax.set_ylim(0, 100000)
ax.legend(loc='upper right')

# Text placeholders
hr_text   = ax.text(0.02, 0.95, "", transform=ax.transAxes)
spo2_text = ax.text(0.02, 0.90, "", transform=ax.transAxes)

def update(frame):
    samples, nak = i2c.write_read(MAX_ADDR_8BIT, bytes([0x07]), 6)
    if nak == 0:
        red = ((samples[0]<<16)|(samples[1]<<8)|samples[2]) & 0x03FFFF
        ir  = ((samples[3]<<16)|(samples[4]<<8)|samples[5]) & 0x03FFFF
        red_values.append(red)
        ir_values.append(ir)

        xs = range(len(red_values))
        line_red.set_data(xs, red_values)
        line_ir.set_data(xs, ir_values)

        # compute vitals
        raw_bpm = estimate_bpm(ir_values)
        bpm     = smooth_bpm(raw_bpm)
        spo2    = estimate_spo2(red_values, ir_values)

        hr_text.set_text(f"HR: {bpm:.0f} bpm" if bpm else "HR: -- bpm")
        spo2_text.set_text(f"SpO₂: {spo2:.1f} %" if spo2 else "SpO₂: -- %")

        # rescale y
        current_max = max(max(red_values), max(ir_values))
        ax.set_ylim(0, current_max * 1.1)
    else:
        print(f"I2C NACK at index {nak}")

    return line_red, line_ir, hr_text, spo2_text

# --- Device & I2C setup ---
with dwf.Device() as device:
    print(f"Found device: {device.name} ({device.serial_number})")

    # Power
    device.analog_io[0][1].value = 3.3
    device.analog_io[0][0].value = True
    device.analog_io.master_enable = True

    # I2C
    i2c = Protocols.I2C(device)
    i2c.setup(pin_scl=6, pin_sda=7, rate=100_000)

    # Soft reset + mode check
    i2c.write(MAX_ADDR_8BIT, bytes([0x09, 0x40]))
    time.sleep(0.1)
    i2c.write(MAX_ADDR_8BIT, bytes([0x09]))
    mode, nak = i2c.read(MAX_ADDR_8BIT, 1)
    print(f"MODE_CONFIG readback: 0x{mode[0]:02X}")

    # Configure sensor & FIFO
    cfg = [
        (0x09, 0x03), (0x0A, 0x27),
        (0x0C, 0x24), (0x0D, 0x24),
        (0x08, 0x00), (0x06, 0x00),
        (0x07, 0x00), (0x05, 0x00),
    ]
    for reg, val in cfg:
        i2c.write(MAX_ADDR_8BIT, bytes([reg, val]))
    time.sleep(0.2)

    # Start animation
    ani = FuncAnimation(fig, update, interval=100)
    plt.tight_layout()
    plt.show()