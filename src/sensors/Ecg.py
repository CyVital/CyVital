# Ecg.py
import dwfpy as dwf
import numpy as np
import scipy.signal as signal
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Optional, List
import imgui

@dataclass
class EcgData:
    heart_rate: Optional[int] = None
    waveform_buffer: Deque[float] = field(default_factory=lambda: deque(maxlen=4096))
    raw_samples: List[float] = field(default_factory=list)
    sample_rate: int = 8192

class EcgMonitor:
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.data = EcgData()
        self.lock = threading.Lock()
        self.device = None
        self.scope = None
        self.start_time = time.time()
        self.peaks = []
        
        # Filter parameters
        lowcut, highcut = 0.5, 40.0
        self.b, self.a = signal.butter(2, [lowcut / (self.data.sample_rate / 2), 
                                      highcut / (self.data.sample_rate / 2)], 
                                      btype='band')

    def _initialize_device(self):
        devices = dwf.Device.enumerate()
        if not devices:
            raise RuntimeError("No Digilent WaveForms device found")
            
        self.device = dwf.Device()
        if not self.device.analog_input:
            raise RuntimeError("Analog input not available")
            
        # Configure waveform generator
        wavegen = self.device.analog_output
        wavegen[0].setup(function="sine", frequency=1.25, amplitude=0.05, offset=0.0)
        wavegen[0].setup_am(function="triangle", frequency=0.1, amplitude=20)
        wavegen[0].configure(start=True)

        # Configure analog input
        self.device.analog_io[0][1].value = 3.3
        self.device.analog_io[0][0].value = True
        self.device.analog_io.master_enable = True
        
        self.scope = self.device.analog_input
        self.scope[0].setup(range=0.5)
        self.scope.scan_shift(sample_rate=self.data.sample_rate, buffer_size=4096, 
                            configure=True, start=True)

    def _estimate_heart_rate(self, ecg_signal):
        """Detects R-peaks and estimates heart rate."""
        filtered_ecg = signal.filtfilt(self.b, self.a, ecg_signal)
        peaks, _ = signal.find_peaks(filtered_ecg, 
                                   distance=self.data.sample_rate//2.5, 
                                   height=np.mean(filtered_ecg) + 0.5*np.std(filtered_ecg))
        
        if len(peaks) > 1:
            rr_intervals = np.diff(peaks) / self.data.sample_rate
            return int(60.0 / np.mean(rr_intervals))
        return None

    def _run(self):
        heart_rates = deque(maxlen=5)
        
        try:
            self._initialize_device()
            
            while self._running:
                status = self.scope.read_status(read_data=True)
                channel = self.scope.channels[0]
                new_samples = np.array(channel.get_data())
                
                with self.lock:
                    self.data.raw_samples = new_samples.tolist()
                    self.data.waveform_buffer.extend(new_samples)
                    
                    if len(self.data.waveform_buffer) >= 1000:
                        hr = self._estimate_heart_rate(np.array(self.data.waveform_buffer))
                        if hr is not None:
                            heart_rates.append(hr)
                            self.data.heart_rate = int(np.mean(heart_rates))
                            self.peaks = signal.find_peaks(self.data.waveform_buffer, 
                                                         height=1.92, distance=200)[0]
        except Exception as e:
            print(f"ECG monitoring error: {e}")
            self._running = False

    def start(self):
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()

    def get_data(self) -> EcgData:
        with self.lock:
            return EcgData(
                heart_rate=self.data.heart_rate,
                waveform_buffer=deque(self.data.waveform_buffer),
                raw_samples=list(self.data.raw_samples),
                sample_rate=self.data.sample_rate
            )