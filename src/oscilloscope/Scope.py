import dwfpy as dwf
import numpy as np

class Scope:
    def __init__(self): #reaction initialization, for now
        self.sample_rate = 10000
        self.buffer_size = 512
        self.threshold_voltage = 2
        self.signal_time = 0.0

        self.device = dwf.Device()
        print(f"Connected to {self.device.name} ({self.device.serial_number})")

        self._setup_device()

    def _setup_device(self):
        self.device.analog_io[0][1].value = 3.3
        self.device.analog_io[0][0].value = True
        self.device.analog_io.master_enable = True

        self.device.digital_io.reset()
        for i in range(4):
            self.device.digital_io.channels[i].enabled = True
            self.device.digital_io.channels[i].output_state = bool((1 >> i) & 1)
        self.device.digital_io.configure()

        self.scope = self.device.analog_input
        self.scope[0].setup(range=3.3)
        self.scope.scan_shift(sample_rate=self.sample_rate, buffer_size=self.buffer_size, configure=True, start=True)

    def get_samples(self):
        self.scope.read_status(read_data=True)
        samples = np.array(self.scope.channels[0].get_data())
        self.signal_time += len(samples) / self.sample_rate
        return samples

    def get_time_axis(self, samples):
        return np.linspace(self.signal_time - len(samples) / self.sample_rate, self.signal_time, len(samples))

    def reset(self):
        self.device.digital_io.reset()
        self.device.digital_io.configure()

    def close(self):
        self.device.close()