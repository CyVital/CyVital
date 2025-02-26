import dwfpy as dwf

import numpy as np

import scipy.signal as signal

import matplotlib.pyplot as plt

from collections import deque

# Get the list of available devices

devices = dwf.Device.enumerate()



# Ensure at least one device is available

if not devices:

    raise RuntimeError("No Digilent WaveForms device found. Please check the connection.")



# Open the first available device

device = dwf.Device()  # Explicitly open the first detected device



# Debug: Print device info

print(f"Opened Device: {device}")

print(f"Analog Input: {device.analog_input}")

print(f"Analog Output: {device.analog_output}")

print(f"Digital IO: {device.digital_io}")

# Ensure analog_input is available

if device.analog_input is None:

    raise RuntimeError("Analog input not available. Check if the device supports it.")

# Setup device

# device = dwf.Device()

print(device)

print(device.analog_input)

ecg_channel = device.analog_input[1]  # ECG

ecg_channel.setup(range=5.0, frequency=1000)  #1 kHz sampling rate



# Processing parameters

buffer_size = 1000  # 1 second of data at 1 kHz

data_buffer = deque(maxlen=buffer_size)

sampling_rate = 1000  # Hz

heart_rates = deque(maxlen=5)  # Store last 5 HR readings for smoothing



lowcut, highcut = 0.5, 40.0

b, a = signal.butter(2, [lowcut / (sampling_rate / 2), highcut / (sampling_rate / 2)], btype='band')



def estimate_heart_rate(ecg_signal, sampling_rate):

    """Detects R-peaks and estimates heart rate."""

    filtered_ecg = signal.filtfilt(b, a, ecg_signal)

    peaks, _ = signal.find_peaks(filtered_ecg, distance=sampling_rate//2.5, height=np.mean(filtered_ecg) + 0.5*np.std(filtered_ecg))

    

    if len(peaks) > 1:

        rr_intervals = np.diff(peaks) / sampling_rate  # Convert to seconds

        heart_rate = 60.0 / np.mean(rr_intervals)  # BPM

        return int(heart_rate)

    return None



print("Recording ECG... Press Ctrl+C to stop.")



try:

    while True:

        ecg_data = ecg_channel.record(buffer_size)  

        data_buffer.extend(ecg_data)  # Append to buffer



        if len(data_buffer) == buffer_size:

            hr = estimate_heart_rate(np.array(data_buffer), sampling_rate)

            if hr:

                heart_rates.append(hr)

                avg_hr = int(np.mean(heart_rates))

                print(f"Heart Rate: {avg_hr} BPM")

except KeyboardInterrupt:

    print("\nStopping ECG recording.")

