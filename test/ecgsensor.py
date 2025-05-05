import dwfpy as dwf
import numpy as np
import scipy.signal as signal
import matplotlib.pyplot as plt
from collections import deque
import time

# Create a simple ECG monitoring solution using basic dwfpy 1.0 features
print("Starting ECG Monitor")

try:
    # Initialize the device using the basic approach
    print("Opening AD2 device...")
    device = dwf.Device()
    print(f"Device opened: {device.name}")
    
    # With dwfpy 1.0, we need to reset the device first
    device.reset()
    print("Device reset")
    
    # Now let's initialize the analog input module explicitly
    # This approach uses the dwfpy internals which should work with v1.0
    print("Initializing analog input module...")
    
    # Check if the device has the _analog_input attribute (internal)
    if hasattr(device, '_analog_input') and device._analog_input is None:
        from dwfpy import analog_in
        
        # Create the analog input module explicitly
        device._analog_input = analog_in.AnalogIn(device)
        print("Created analog input module manually")
    
    # Now try to access the analog input
    if device.analog_input is not None:
        print("Analog input module is now available")
        ecg_channel = 1  # Use channel 1 for ECG
        
        # Configure the channel
        device.analog_input.channels[ecg_channel].range = 5.0
        device.analog_input.channels[ecg_channel].enabled = True
        device.analog_input.acquisition_mode = analog_in.AcquisitionMode.SINGLE
        device.analog_input.frequency = 1000  # 1kHz sampling
        
        print(f"Configured channel {ecg_channel} for ECG monitoring")
        
        # Processing parameters
        buffer_size = 1000
        data_buffer = deque(maxlen=buffer_size)
        sampling_rate = 1000
        
        # Bandpass filter for ECG
        lowcut, highcut = 0.5, 40.0
        b, a = signal.butter(2, [lowcut / (sampling_rate / 2), highcut / (sampling_rate / 2)], btype='band')
        
        # Setup visualization
        plt.ion()
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))
        line1, = ax1.plot(np.zeros(buffer_size))
        line2, = ax2.plot(np.zeros(buffer_size))
        ax1.set_title('Raw ECG Signal')
        ax2.set_title('Filtered ECG Signal')
        plt.tight_layout()
        
        # Main loop
        print("Recording ECG... Press Ctrl+C to stop")
        try:
            while True:
                # Acquire data
                device.analog_input.single_acquisition()
                status = device.analog_input.wait_for_acquisition_complete()
                
                if status:
                    # Get data from the channel
                    ecg_data = device.analog_input.get_data(ecg_channel)
                    
                    # Add to buffer
                    data_buffer.extend(ecg_data)
                    
                    if len(data_buffer) == buffer_size:
                        # Process data
                        data_array = np.array(data_buffer)
                        filtered_data = signal.filtfilt(b, a, data_array)
                        
                        # Update plots
                        line1.set_ydata(data_array)
                        line2.set_ydata(filtered_data)
                        ax1.relim()
                        ax1.autoscale_view()
                        ax2.relim()
                        ax2.autoscale_view()
                        plt.pause(0.1)
                        
                        # Find peaks for heart rate
                        threshold = np.mean(filtered_data) + 0.3 * np.std(filtered_data)
                        peaks, _ = signal.find_peaks(filtered_data, distance=sampling_rate//3, height=threshold)
                        
                        if len(peaks) > 1:
                            # Calculate heart rate
                            rr_intervals = np.diff(peaks) / sampling_rate
                            heart_rate = 60.0 / np.mean(rr_intervals)
                            print(f"Heart Rate: {int(heart_rate)} BPM")
                
                time.sleep(0.2)
                
        except KeyboardInterrupt:
            print("\nStopping ECG recording")
    else:
        # Fallback to direct API approach if analog_input is still None
        print("Analog input module still not available, trying direct API approach")
        
        # This approach requires the ctypes module and direct access to the DWF API
        import ctypes
        from ctypes import c_int, c_double, byref
        
        # Load the DWF library directly
        if sys.platform.startswith("win"):
            dwf_lib = ctypes.cdll.dwf
        elif sys.platform.startswith("darwin"):
            dwf_lib = ctypes.cdll.LoadLibrary("/Library/Frameworks/dwf.framework/dwf")
        else:
            dwf_lib = ctypes.cdll.LoadLibrary("libdwf.so")
        
        # Reset analog in
        dwf_lib.FDwfAnalogInReset(device.handle)
        
        # Configure
        dwf_lib.FDwfAnalogInFrequencySet(device.handle, c_double(1000.0))
        
        # Channel 0
        channel = 0
        dwf_lib.FDwfAnalogInChannelRangeSet(device.handle, c_int(channel), c_double(5.0))
        dwf_lib.FDwfAnalogInChannelEnableSet(device.handle, c_int(channel), c_int(1))
        
        # Configure acquisition mode (Single)
        dwf_lib.FDwfAnalogInAcquisitionModeSet(device.handle, c_int(1))  # acqmodeSingle
        
        # Configure sampling
        buffer_size = 1000
        dwf_lib.FDwfAnalogInBufferSizeSet(device.handle, c_int(buffer_size))
        
        print("Configured analog input directly through API")
        
        # Main loop
        print("Recording ECG... Press Ctrl+C to stop")
        try:
            while True:
                # Start acquisition
                dwf_lib.FDwfAnalogInConfigure(device.handle, c_int(0), c_int(1))
                
                # Wait for completion
                status = c_int()
                while True:
                    dwf_lib.FDwfAnalogInStatus(device.handle, c_int(1), byref(status))
                    if status.value == 2:  # DwfStateDone
                        break
                    time.sleep(0.1)
                
                # Read data
                buffer = (c_double * buffer_size)()
                dwf_lib.FDwfAnalogInStatusData(device.handle, c_int(channel), byref(buffer), c_int(buffer_size))
                
                # Convert to numpy
                data = np.array([buffer[i] for i in range(buffer_size)])
                
                # Process and display
                print(f"Data acquired: min={min(data):.3f}V, max={max(data):.3f}V")
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\nStopping ECG recording")

except Exception as e:
    print(f"Error: {e}")
finally:
    # Always make sure to close the device
    try:
        if 'device' in locals() and device is not None:
            device.close()
            print("Device closed")
    except:
        print("Error closing device")