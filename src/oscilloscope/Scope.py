import dwfpy as dwf
from dwfpy.protocols import Protocols
import numpy as np
import time

class Scope:
    def __init__(self): #reaction initialization, for now
        self.reaction_sample_rate = 10000
        self.reaction_buffer_size = 512
        self.reaction_signal_time = 0.0
        self.emg_sample_rate        = 4000
        self.emg_buffer_size        = 2048
        self.emg_sample_count = 0
        self.ecg_sample_rate = 8192
        self.pulse_ox_sample_count = 0

        self.MAX_ADDR_7BIT = 0x57
        self.MAX_ADDR_8BIT = self.MAX_ADDR_7BIT << 1  # 0xAE

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
        return new_samples
    
    def get_emg_time_axis(self, samples):
        t_start = self.emg_sample_count / self.emg_sample_rate
        t_axis  = np.arange(len(samples)) / self.emg_sample_rate + t_start
        self.emg_sample_count += len(samples)
        return t_axis
    
    def get_ecg_time_axis(self, samples):
        print(samples)
        return np.linspace(0, len(samples) / self.ecg_sample_rate, len(samples))

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

    def setup_device_pulse_ox(self):

        self.reset()

        # Power
        self.device.analog_io[0][1].value = 3.3
        self.device.analog_io[0][0].value = True
        self.device.analog_io.master_enable = True

        # I2C
        self.i2c = Protocols.I2C(self.device)
        self.i2c.setup(pin_scl=6, pin_sda=7, rate=100_000)

        # Soft reset + mode check
        self.i2c.write(self.MAX_ADDR_8BIT, bytes([0x09, 0x40]))
        time.sleep(0.1)
        self.i2c.write(self.MAX_ADDR_8BIT, bytes([0x09]))
        mode, nak = self.i2c.read(self.MAX_ADDR_8BIT, 1)
        print(f"I2C NACK at index {nak}")
        print(f"MODE_CONFIG readback: 0x{mode[0]:02X}")

        # Configure sensor & FIFO
        cfg = [
            (0x09, 0x03), (0x0A, 0x27),
            (0x0C, 0x24), (0x0D, 0x24),
            (0x08, 0x00), (0x06, 0x00),
            (0x07, 0x00), (0x05, 0x00),
        ]
        for reg, val in cfg:
            self.i2c.write(self.MAX_ADDR_8BIT, bytes([reg, val]))
        time.sleep(0.2)
    
    def get_pulse_ox_samples(self):
        samples, nak = self.i2c.write_read(self.MAX_ADDR_8BIT, bytes([0x07]), 6)
        if nak == 0:
            self.pulse_ox_sample_count += 1
        else:
            print(f"I2C NACK at index {nak}")
            return None

        return samples
    
    def get_pulse_ox_time_axis(self):
        return np.linspace(0, self.pulse_ox_sample_count, self.pulse_ox_sample_count)
    
    def reset(self):
        self.device.digital_io.reset()
        self.device.digital_io.configure()

    def close(self):
        self.device.close()