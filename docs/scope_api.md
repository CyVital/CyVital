## `src/oscilloscope/Scope.py`

### Module: `Scope`
Hardware integration and signal acquisition for all supported modalities (reaction, EMG, ECG, pulse ox, blood pressure, respiratory).

#### Class: `Scope`

**Constructor**
- `Scope()`
  - Connects to the underlying DWF-compatible device for analog/digital IO and hardware signal streaming.
  - Initializes all sample rates, buffer sizes, I2C addresses, and signal counters.
  - Raises a message if device not found.

---

### Device setup methods

- `setup_device_analog(self) -> None`  
  Powers 3.3V analog rails, powers up the analog subsystem, and enables the analog input interface.

- `setup_device_reaction(self) -> None`  
  Sets up analog/digital IO for the reaction-time measurement configuration.  
  - Digital channel 0 set HIGH, others LOW.  
  - Configures analog input for streaming at `reaction_sample_rate` into buffer.

- `setup_device_emg(self) -> None`  
  Prepares analog/digital IO for EMG data.  
  - Digital channel 1 set HIGH, others LOW.  
  - Configures analog input with range and buffer for EMG.

- `setup_device_ecg(self) -> None`  
  Prepares analog and waveform generator IO for ECG data.  
  - Analog output set to sine/triangle, analog input on both channels.

- `setup_device_pulse_ox(self) -> None`  
  Resets digital I/O, powers rails, configures I2C, and initializes pulse oximeter registers (MAX30101 protocol).  
  - Performs soft reset and sensor configuration.

- `setup_device_blood_pressure(self) -> None`  
  Prepares analog input for streaming blood pressure measurements.

- `setup_device_respiratory(self) -> None`  
  Configures analog/digital IO for respiratory effort waveform capture.

---

### Data acquisition methods

Each acquisition method typically raises an `IOError` if the hardware is not attached.

- `get_reaction_samples(self) -> np.ndarray`  
  Reads and returns the latest reaction signal samples, updating `reaction_signal_time`.

- `get_emg_samples(self) -> np.ndarray`  
  Reads and returns EMG signal samples.

- `get_ecg_samples(self) -> np.ndarray`  
  Reads ECG analog input samples.

- `get_pulse_ox_samples(self) -> bytes | None`  
  Reads 6 bytes from the pulse oximeter sensor; returns None on NACK.

- `get_blood_pressure_samples(self) -> np.ndarray`  
  Reads voltage samples for blood pressure.

- `get_respiratory_samples(self) -> np.ndarray`  
  Reads streaming respiratory signal samples, updating `resp_signal_time`.

---

### Time axis methods

These helpers generate a time axis for visualization based on the current buffer, sampling rate, and counters.

- `get_emg_time_axis(self, samples) -> np.ndarray`  
  Returns a time axis for EMG samples, tracking cumulative position.

- `get_ecg_time_axis(self, samples) -> np.ndarray`  
  Returns ECG time axis, cumulative.

- `get_reaction_time_axis(self, samples) -> np.ndarray`  
  Aligned time axis for reaction samples using `reaction_signal_time`.

- `get_respiratory_time_axis(self, samples) -> np.ndarray`  
  Time axis for respiratory samples, tracked via `resp_signal_time`.

- `get_pulse_ox_time_axis(self) -> np.ndarray`  
  Linear time axis for pulse ox sample count.

- `get_blood_pressure_time_axis(self, samples) -> np.ndarray`  
  Blood pressure sample time axis, tracked by internal counter.

---

### Utility methods

- `reset(self) -> None`  
  Resets digital I/O (output state).

- `close(self) -> None`  
  Closes the device connection and releases resources.

---

### Key attributes

- `reaction_sample_rate: int` — Reaction signal sample rate (default 10000)
- `reaction_buffer_size: int` — Buffer size for reaction signal
- `reaction_signal_time: float` — Last position in reaction signal (seconds)
- `emg_sample_rate: int` — Sample rate for EMG (default 4000)
- `emg_buffer_size: int` — Buffer size for EMG samples
- `emg_sample_count: int` — Running EMG sample counter
- `ecg_sample_rate: int` — Sample rate for ECG (default 8192)
- `ecg_sample_count: int`
- `pulse_ox_sample_count: int`
- `blood_pressure_sample_count: int`
- `blood_pressure_sample_rate: int`
- `resp_sample_rate: int`
- `resp_buffer_size: int`
- `resp_signal_time: float`
- `MAX_ADDR_7BIT: int` — Default 7-bit I2C sensor address (`0x57`)
- `MAX_ADDR_8BIT: int` — 8-bit I2C write address (`0xAE`)
- `device: dwf.Device` — Underlying hardware handle

---

### Notes

- **Error handling**: Most data acquisition methods raise `IOError` if hardware is unreachable.
- **Sample tracking**: Internal counters keep time axes in sync for streaming/plotting.

---
