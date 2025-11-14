import dwfpy as dwf
import numpy as np

class Scope:
    def __init__(self): #reaction initialization, for now
        self.reaction_sample_rate = 10000
        self.reaction_buffer_size = 512
        self.reaction_signal_time = 0.0
        self.emg_sample_rate        = 4000
        self.emg_buffer_size        = 2048
        self.emg_sample_count = 0
        self.ecg_sample_rate = 8192
        self.ecg_signal_time = 0.0
        self.resp_sample_rate = 200
        self.resp_buffer_size = 2048
        self.resp_signal_time = 0.0

        self.device = dwf.Device()
        print(f"Connected to {self.device.name} ({self.device.serial_number})")

        try:
            self.device.open()
        except:
            print("Device not found")

        self.setup_device_reaction()
    
    def setup_device_analog(self):
        try:
            self.device.analog_io[0][1].value = 3.3
            self.device.analog_io[0][0].value = True
            self.device.analog_io.master_enable = True
            self.scope = self.device.analog_input
        except:
            print("Cannot set up analog scope")
    
    def setup_device_reaction(self):
        try: 
            self.setup_device_analog()

            self.device.digital_io.reset()
            for i in range(4):
                self.device.digital_io.channels[i].enabled = True
                self.device.digital_io.channels[i].output_state = bool((1 >> i) & 1) #this is setting channel 0 true, and the others false
            self.device.digital_io.configure()
            
            self.scope[0].setup(range=3.3)
            self.scope.scan_shift(sample_rate=self.reaction_sample_rate, buffer_size=self.reaction_buffer_size, configure=True, start=True)
        except:
            print("Cannot setup reaction scope")

    # Maybe the get_{sensor}_samples should all be the same get_analog_samples function since they're the same???
    def get_reaction_samples(self):
        self.scope.read_status(read_data=True)
        samples = np.array(self.scope.channels[0].get_data())
        self.reaction_signal_time += len(samples) / self.reaction_sample_rate
        return samples
    
    def get_emg_samples(self):
        self.scope.read_status(read_data=True)
        raw = np.array(self.scope.channels[0].get_data())
        return raw
    
    def get_ecg_samples(self):
        self.scope.read_status(read_data=True)
        new_samples = np.array(self.scope.channels[0].get_data())
        self.ecg_signal_time += len(new_samples) / self.ecg_sample_rate
        return new_samples

    def get_ecg_time_axis(self, samples):
        return np.linspace(
            self.ecg_signal_time - len(samples) / self.ecg_sample_rate,
            self.ecg_signal_time,
            len(samples),
        )

    def get_respiratory_samples(self):
        self.scope.read_status(read_data=True)
        samples = np.array(self.scope.channels[0].get_data())
        self.resp_signal_time += len(samples) / self.resp_sample_rate
        return samples

    def get_respiratory_time_axis(self, samples):
        return np.linspace(
            self.resp_signal_time - len(samples) / self.resp_sample_rate,
            self.resp_signal_time,
            len(samples),
        )
    
    def get_emg_time_axis(self, samples):
        t_start = self.emg_sample_count / self.emg_sample_rate
        t_axis  = np.arange(len(samples)) / self.emg_sample_rate + t_start
        self.emg_sample_count += len(samples)
        return t_axis


    def get_reaction_time_axis(self, samples):
        return np.linspace(self.reaction_signal_time - len(samples) / self.reaction_sample_rate, self.reaction_signal_time, len(samples))
    
    def setup_device_emg(self):

        self.setup_device_analog()

        # Optional DIO setup
        self.device.digital_io.reset()
        for i in range(4):
            self.device.digital_io.channels[i].enabled = True
            self.device.digital_io.channels[i].output_state = bool((2 >> i) & 1)
        self.device.digital_io.configure()

        # Oscilloscope setup
        self.scope = self.device.analog_input
        self.scope[0].setup(range=0.01)
        self.scope.scan_shift(sample_rate=self.emg_sample_rate,
                         buffer_size=self.emg_buffer_size,
                         configure=True,
                         start=True)

    def setup_device_ecg(self):
        self.setup_device_analog()

        self.wavegen = self.device.analog_output
        self.wavegen[0].setup(function="sine", frequency=1.25, amplitude=0.05, offset=0.0)
        self.wavegen[0].setup_am(function="triangle", frequency=0.1, amplitude=20)
        self.wavegen[0].configure(start=True)

        self.scope = self.device.analog_input
        self.scope[0].setup(range=0.5)
        self.scope[1].setup(range=0.5)
        self.scope.scan_shift(sample_rate=self.ecg_sample_rate, buffer_size=4096, configure=True, start=True)

    def setup_device_respiratory(self):
        self.setup_device_analog()
        self.device.digital_io.reset()
        self.device.digital_io.configure()

        self.scope = self.device.analog_input
        self.scope[0].setup(range=5.0)
        self.scope.scan_shift(
            sample_rate=self.resp_sample_rate,
            buffer_size=self.resp_buffer_size,
            configure=True,
            start=True,
        )

    def reset(self):
        self.device.digital_io.reset()
        self.device.digital_io.configure()

    def close(self):
        self.device.close()
