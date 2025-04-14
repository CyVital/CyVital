# Ecg.py
import dwfpy as dwf
import numpy as np
import scipy.signal as signal
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Optional

@dataclass
class EcgData:
    heart_rate: Optional[int] = None
    waveform_buffer: Deque[float] = field(
        default_factory=lambda: deque(maxlen=1000)
    )

class EcgMonitor:
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.data = EcgData()
        self.lock = threading.Lock()
        
        # Initialize device
        devices = dwf.Device.enumerate()
        if not devices:
            raise RuntimeError("No Digilent WaveForms device found")
            
        self.device = dwf.Device()
        if not self.device.analog_input:
            raise RuntimeError("Analog input not available")
            
        self.ecg_channel = self.device.analog_input[1]
        self.ecg_channel.setup(range=5.0, frequency=1000)
        
        # Filter parameters
        self.sampling_rate = 1000
        lowcut, highcut = 0.5, 40.0
        self.b, self.a = signal.butter(2, [lowcut / (self.sampling_rate / 2), 
                                         highcut / (self.sampling_rate / 2)], 
                                      btype='band')
        
    def _estimate_heart_rate(self, ecg_signal):
        """Detects R-peaks and estimates heart rate."""
        filtered_ecg = signal.filtfilt(self.b, self.a, ecg_signal)
        peaks, _ = signal.find_peaks(filtered_ecg, 
                                    distance=self.sampling_rate//2.5, 
                                    height=np.mean(filtered_ecg) + 0.5*np.std(filtered_ecg))
        
        if len(peaks) > 1:
            rr_intervals = np.diff(peaks) / self.sampling_rate
            return int(60.0 / np.mean(rr_intervals))
        return None

    def _run(self):
        heart_rates = deque(maxlen=5)
        
        while self._running:
            ecg_data = self.ecg_channel.record(100)
            with self.lock:
                self.data.waveform_buffer.extend(ecg_data)
                
                if len(self.data.waveform_buffer) >= 1000:
                    hr = self._estimate_heart_rate(np.array(self.data.waveform_buffer))
                    if hr:
                        heart_rates.append(hr)
                        self.data.heart_rate = int(np.mean(heart_rates))

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
                waveform_buffer=deque(self.data.waveform_buffer)
            )