import dwfpy as dwf
import time
import numpy as np
from scipy.signal import find_peaks
import sys

class HeartRateMonitor:
    def __init__(self):
        self.sample_rate = 8192
        self.window_duration = 10  # seconds
        self.running = False
        self.device = None
        self.scope = None
        self.raw_samples = []
        self.time_values = []
        self.bpm_values = []
        self.peak_times = []
        self.current_bpm = 0
        self.start_time = 0
        self._device_info = {}

    @staticmethod
    def discover_devices():
        """Device discovery compatible with all dwfpy versions"""
        devices = []
        try:
            # Try new discovery method
            if hasattr(dwf.Device, 'discover'):
                devices = dwf.Device.discover()
            # Fallback to legacy enumeration
            else:
                devices = dwf.Device.enumerate()
            
        except Exception as e:
            print(f"Device discovery failed: {str(e)}")
            return []

    def start(self, serial_number=None):
        try:
            # Release any existing connections
            self.stop()
            
            # Connect to specified device
            if serial_number:
                print(f"Connecting to device SN: {serial_number}")
                self.device = dwf.Device(serial=serial_number)
            else:
                print("Connecting to first available device")
                self.device = dwf.Device()

            # Verify device connection
            if not self.device:
                raise RuntimeError("No device found")

            # Store device info
            self._device_info = {
                'name': self.device.name,
                'serial': self.device.serial_number,
                'vid': self.device.config.vendor_id,
                'pid': self.device.config.product_id
            }

            # Configure analog output (if available)
            if hasattr(self.device, 'analog_output'):
                ao = self.device.analog_output[0]
                ao.setup(
                    function="sine",
                    frequency=1.25,
                    amplitude=0.05,
                    offset=0.0
                )
                ao.configure(start=True)

            # Configure analog input
            if not hasattr(self.device, 'analog_input'):
                raise RuntimeError("Device missing analog inputs")

            self.scope = self.device.analog_input
            self.scope[0].setup(range=0.5)
            self.scope.scan_shift(
                sample_rate=self.sample_rate,
                buffer_size=4096,
                configure=True,
                start=True
            )

            self.running = True
            self.start_time = time.time()
            return True

        except Exception as e:
            self.stop()
            raise RuntimeError(f"Connection failed: {str(e)}")

    def stop(self):
        self.running = False
        try:
            if self.device:
                self.device.close()
        except Exception as e:
            print(f"Error closing device: {str(e)}")
        finally:
            self.device = None
            self.scope = None
            self._device_info = {}

    def update(self):
        if not self.running or not self.scope:
            return

        try:
            # Read device status
            status = self.scope.read_status(read_data=True)
            
            # Get channel data
            channel = self.scope.channels[0]
            new_samples = np.array(channel.get_data())
            current_time = time.time() - self.start_time

            # Process samples
            self.raw_samples = new_samples.tolist()
            
            # Detect peaks
            peaks, _ = find_peaks(
                new_samples,
                height=1.92,
                distance=200,
                prominence=0.01
            )
            
            # Update peak times
            self.peak_times = [
                current_time - (len(new_samples) - p)/self.sample_rate 
                for p in peaks
            ]
            
            # Remove old peaks
            cutoff = current_time - self.window_duration
            self.peak_times = [t for t in self.peak_times if t > cutoff]
            
            # Calculate BPM
            if len(self.peak_times) > 1:
                rr_intervals = np.diff(self.peak_times)
                avg_rr = np.mean(rr_intervals)
                self.current_bpm = 60 / avg_rr - 270  # Calibration offset
            else:
                self.current_bpm = 0
                
            # Update time series
            self.time_values.append(current_time)
            self.bpm_values.append(self.current_bpm)
            
            # Maintain buffer size
            if len(self.time_values) > 1000:
                self.time_values.pop(0)
                self.bpm_values.pop(0)

        except Exception as e:
            self.stop()
            raise RuntimeError(f"Data acquisition error: {str(e)}")

    @property
    def device_info(self):
        return self._device_info.copy()

    def __del__(self):
        self.stop()