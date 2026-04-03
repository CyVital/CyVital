import random
import time
from typing import Dict, Optional

import numpy as np


class FakeScope:
    """Synthetic stand-in for the hardware-backed Scope.

    Generates continuous samples that emulate button presses so the GUI can be
    exercised without a physical device.
    """

    def __init__(
        self,
        sample_rate: int = 10_000,
        buffer_size: int = 512,
        threshold_voltage: float = 2.0,
        noise_level: float = 0.05,
        pulse_voltage: float = 3.0,
        rng_seed: Optional[int] = None,
        *,
        emg_sample_rate: int = 4000,
        emg_buffer_size: int = 2048,
        ecg_sample_rate: int = 8192,
        ecg_buffer_size: int = 4096,
        ecg_bpm: float = 72.0,
        ecg_noise_level: float = 0.02,
        pulse_ox_sample_rate: int = 10,
        blood_pressure_sample_rate: int = 200,
        blood_pressure_buffer_size: int = 200,
        resp_sample_rate: int = 50,
        resp_buffer_size: int = 15,
        resp_rate_bpm: float = 12.0,
        resp_noise_level: float = 0.01,
        resp_amplitude: float = 0.4,
    ) -> None:
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.threshold_voltage = threshold_voltage
        self.noise_level = noise_level
        self.pulse_voltage = pulse_voltage
        self.signal_time = 0.0

        self.ecg_sample_rate = ecg_sample_rate
        self.ecg_buffer_size = ecg_buffer_size
        self.ecg_bpm = ecg_bpm
        self.ecg_noise_level = ecg_noise_level
        self.ecg_signal_time = 0.0
        self.emg_sample_rate = emg_sample_rate
        self.emg_buffer_size = emg_buffer_size
        self.emg_sample_count = 0
        self.pulse_ox_sample_rate = pulse_ox_sample_rate
        self.pulse_ox_sample_count = 0
        self.blood_pressure_sample_rate = blood_pressure_sample_rate
        self.blood_pressure_buffer_size = blood_pressure_buffer_size
        self.blood_pressure_sample_count = 0
        self.resp_sample_rate = resp_sample_rate
        self.resp_buffer_size = resp_buffer_size
        self.resp_rate_bpm = resp_rate_bpm
        self.resp_noise_level = resp_noise_level
        self.resp_amplitude = resp_amplitude
        self.resp_signal_time = 0.0

        self._rng = random.Random(rng_seed)
        self._np_rng = np.random.default_rng(rng_seed)
        self._pulse_samples_remaining = 0
        self._samples_until_next_pulse = self._choose_gap()
        self._ecg_template = self._generate_ecg_template()
        self._ecg_index = 0
        self._stream_clock: Dict[str, float] = {}

    # --- Scope-style setup API (no-ops for fake data) ---
    def setup_device_reaction(self) -> None:
        self.signal_time = 0.0

    def setup_device_emg(self) -> None:
        self.emg_sample_count = 0

    def setup_device_ecg(self) -> None:
        self.ecg_signal_time = 0.0

    def setup_device_pulse_ox(self) -> None:
        self.pulse_ox_sample_count = 0

    def setup_device_blood_pressure(self) -> None:
        self.blood_pressure_sample_count = 0

    def setup_device_respiratory(self) -> None:
        self.resp_signal_time = 0.0

    def _choose_gap(self) -> int:
        # Aim for 1-3 second gaps between pulses to mimic reaction trials.
        seconds = self._rng.uniform(1.0, 3.0)
        return max(1, int(seconds * self.sample_rate))

    def _choose_pulse_width(self) -> int:
        # Keep pulses short (20-60 ms) so they register as discrete button hits.
        seconds = self._rng.uniform(0.02, 0.06)
        return max(1, int(seconds * self.sample_rate))

    def get_samples(self) -> np.ndarray:
        self._throttle_stream("reaction", self.buffer_size, self.sample_rate)
        baseline = 0.4 + self.noise_level * self._rng.gauss(0, 1)
        samples = baseline + self.noise_level * self._np_rng.normal(size=self.buffer_size)

        for i in range(self.buffer_size):
            if self._pulse_samples_remaining > 0:
                samples[i] = self.pulse_voltage + self.noise_level * self._np_rng.normal()
                self._pulse_samples_remaining -= 1
                if self._pulse_samples_remaining == 0:
                    self._samples_until_next_pulse = self._choose_gap()
            elif self._samples_until_next_pulse <= 0:
                self._pulse_samples_remaining = self._choose_pulse_width()
                samples[i] = self.pulse_voltage + self.noise_level * self._np_rng.normal()
                self._pulse_samples_remaining -= 1
            else:
                self._samples_until_next_pulse -= 1

        self.signal_time += len(samples) / self.sample_rate
        return samples.astype(np.float32)

    def _generate_ecg_template(self) -> np.ndarray:
        """Create a reusable ECG waveform so simulations look repeatable."""
        beats_per_second = self.ecg_bpm / 60.0
        samples_per_beat = max(1, int(self.ecg_sample_rate / beats_per_second))
        t = np.linspace(0.0, 1.0, samples_per_beat, endpoint=False)

        def gaussian(center: float, width: float, amplitude: float) -> np.ndarray:
            return amplitude * np.exp(-0.5 * ((t - center) / width) ** 2)

        p_wave = gaussian(0.18, 0.02, 0.08)
        q_wave = gaussian(0.36, 0.01, -0.35)
        r_wave = gaussian(0.38, 0.004, 2.4)
        s_wave = gaussian(0.41, 0.012, -0.45)
        t_wave = gaussian(0.65, 0.05, 0.25)
        baseline = 0.05 * np.sin(2 * np.pi * 1.2 * t)

        template = baseline + p_wave + q_wave + r_wave + s_wave + t_wave
        template -= template.min()
        return template.astype(np.float32)

    def get_ecg_samples(self) -> np.ndarray:
        self._throttle_stream("ecg", self.ecg_buffer_size, self.ecg_sample_rate)
        """Return ECG-like samples that loop over a prerecorded waveform."""
        template = self._ecg_template
        template_len = len(template)
        samples = np.empty(self.ecg_buffer_size, dtype=np.float32)

        idx = self._ecg_index
        for i in range(self.ecg_buffer_size):
            samples[i] = template[idx] + self.ecg_noise_level * self._np_rng.normal()
            idx += 1
            if idx >= template_len:
                idx = 0

        self._ecg_index = idx
        self.ecg_signal_time += len(samples) / self.ecg_sample_rate
        return samples

    def get_emg_samples(self) -> np.ndarray:
        self._throttle_stream("emg", self.emg_buffer_size, self.emg_sample_rate)
        t = (
            np.arange(self.emg_buffer_size, dtype=float) / self.emg_sample_rate
            + (self.emg_sample_count / self.emg_sample_rate)
        )
        # Simple EMG-like signal: noisy rectified sine with baseline noise
        carrier = np.sin(2 * np.pi * 50.0 * t)
        envelope = 0.5 + 0.5 * np.sin(2 * np.pi * 1.0 * t)
        signal = np.abs(carrier) * envelope
        noise = 0.05 * self._np_rng.normal(size=self.emg_buffer_size)
        self.emg_sample_count += self.emg_buffer_size
        return (signal + noise).astype(np.float32)

    def get_pulse_ox_samples(self):
        # Return 6 bytes (red[3], ir[3]) like the MAX30101 FIFO.
        self._throttle_stream("pulse_ox", 1, self.pulse_ox_sample_rate, max_interval=0.1)
        t = self.pulse_ox_sample_count / max(self.pulse_ox_sample_rate, 1)
        base = 50000
        red = int(base + 8000 * np.sin(2 * np.pi * 1.2 * t) + 500 * self._np_rng.normal())
        ir = int(base + 7000 * np.sin(2 * np.pi * 1.2 * t + 0.2) + 500 * self._np_rng.normal())
        red = max(0, min(red, 0x03FFFF))
        ir = max(0, min(ir, 0x03FFFF))
        self.pulse_ox_sample_count += 1
        return [
            (red >> 16) & 0xFF, (red >> 8) & 0xFF, red & 0xFF,
            (ir >> 16) & 0xFF, (ir >> 8) & 0xFF, ir & 0xFF,
        ]

    def get_blood_pressure_samples(self) -> np.ndarray:
        self._throttle_stream(
            "blood_pressure",
            self.blood_pressure_buffer_size,
            self.blood_pressure_sample_rate,
            max_interval=0.1,
        )
        t = (
            np.arange(self.blood_pressure_buffer_size, dtype=float) / self.blood_pressure_sample_rate
            + (self.blood_pressure_sample_count / self.blood_pressure_sample_rate)
        )
        waveform = 0.5 + 0.3 * np.sin(2 * np.pi * 1.2 * t)
        noise = 0.02 * self._np_rng.normal(size=self.blood_pressure_buffer_size)
        self.blood_pressure_sample_count += self.blood_pressure_buffer_size
        return (waveform + noise).astype(np.float32)

    def get_respiratory_samples(self) -> np.ndarray:
        self._throttle_stream(
            "resp",
            self.resp_buffer_size,
            self.resp_sample_rate,
            max_interval=0.1,
        )
        """Generate a slow, sinusoidal waveform with light noise to mimic breathing."""
        t = (
            np.arange(self.resp_buffer_size, dtype=float) / self.resp_sample_rate
            + self.resp_signal_time
        )
        breaths_per_second = self.resp_rate_bpm / 60.0
        waveform = self.resp_amplitude * np.sin(2 * np.pi * breaths_per_second * t)
        noise = self.resp_noise_level * self._np_rng.normal(size=self.resp_buffer_size)
        samples = waveform + noise
        self.resp_signal_time += self.resp_buffer_size / self.resp_sample_rate
        return samples.astype(np.float32)

    def get_time_axis(self, samples: np.ndarray) -> np.ndarray:
        return np.linspace(
            self.signal_time - len(samples) / self.sample_rate,
            self.signal_time,
            len(samples),
        )

    def get_ecg_time_axis(self, samples: np.ndarray) -> np.ndarray:
        return np.linspace(
            self.ecg_signal_time - len(samples) / self.ecg_sample_rate,
            self.ecg_signal_time,
            len(samples),
        )

    def get_emg_time_axis(self, samples: np.ndarray) -> np.ndarray:
        t_start = (self.emg_sample_count - len(samples)) / self.emg_sample_rate
        return np.arange(len(samples)) / self.emg_sample_rate + t_start

    def get_respiratory_time_axis(self, samples: np.ndarray) -> np.ndarray:
        return np.linspace(
            self.resp_signal_time - len(samples) / self.resp_sample_rate,
            self.resp_signal_time,
            len(samples),
        )

    def get_pulse_ox_time_axis(self):
        return np.linspace(0, self.pulse_ox_sample_count, self.pulse_ox_sample_count)

    def get_blood_pressure_time_axis(self, samples: np.ndarray) -> np.ndarray:
        t_start = (self.blood_pressure_sample_count - len(samples)) / self.blood_pressure_sample_rate
        return np.arange(len(samples)) / self.blood_pressure_sample_rate + t_start

    # Provide the Scope-style API so the GUI can swap between implementations.
    def get_reaction_samples(self) -> np.ndarray:
        return self.get_samples()

    def get_reaction_time_axis(self, samples: np.ndarray) -> np.ndarray:
        return self.get_time_axis(samples)

    def reset(self) -> None:
        self._pulse_samples_remaining = 0
        self._samples_until_next_pulse = self._choose_gap()
        self._ecg_index = 0
        self.signal_time = 0.0
        self.ecg_signal_time = 0.0
        self.resp_signal_time = 0.0
        self.emg_sample_count = 0
        self.pulse_ox_sample_count = 0
        self.blood_pressure_sample_count = 0
        self._stream_clock.clear()

    def set_reaction_led(self, active: bool) -> None:
        # GUI-only fallback for now; no external hardware LED to toggle.
        return None

    def _throttle_stream(
        self,
        stream_key: str,
        buffer_size: int,
        sample_rate: int,
        *,
        max_interval: Optional[float] = None,
    ) -> None:
        """Sleep just enough so generated samples advance in (approximate) real time."""
        expected_interval = buffer_size / max(sample_rate, 1)
        if max_interval is not None:
            expected_interval = min(expected_interval, max_interval)
        last_time = self._stream_clock.get(stream_key)
        now = time.perf_counter()
        if last_time is not None:
            elapsed = now - last_time
            remaining = expected_interval - elapsed
            if remaining > 0:
                time.sleep(remaining)
                now = time.perf_counter()
        self._stream_clock[stream_key] = now

    def close(self) -> None:
        # Nothing to release for the fake scope.
        pass
    
