import random
from typing import Optional

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
        ecg_sample_rate: int = 8192,
        ecg_buffer_size: int = 4096,
        ecg_bpm: float = 72.0,
        ecg_noise_level: float = 0.02,
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

        self._rng = random.Random(rng_seed)
        self._np_rng = np.random.default_rng(rng_seed)
        self._pulse_samples_remaining = 0
        self._samples_until_next_pulse = self._choose_gap()
        self._ecg_template = self._generate_ecg_template()
        self._ecg_index = 0

    def _choose_gap(self) -> int:
        # Aim for 1-3 second gaps between pulses to mimic reaction trials.
        seconds = self._rng.uniform(1.0, 3.0)
        return max(1, int(seconds * self.sample_rate))

    def _choose_pulse_width(self) -> int:
        # Keep pulses short (20-60 ms) so they register as discrete button hits.
        seconds = self._rng.uniform(0.02, 0.06)
        return max(1, int(seconds * self.sample_rate))

    def get_samples(self) -> np.ndarray:
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

    def close(self) -> None:
        # Nothing to release for the fake scope.
        pass
    
