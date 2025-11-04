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
    ) -> None:
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.threshold_voltage = threshold_voltage
        self.noise_level = noise_level
        self.pulse_voltage = pulse_voltage
        self.signal_time = 0.0

        self._rng = random.Random(rng_seed)
        self._np_rng = np.random.default_rng(rng_seed)
        self._pulse_samples_remaining = 0
        self._samples_until_next_pulse = self._choose_gap()

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

    def get_time_axis(self, samples: np.ndarray) -> np.ndarray:
        return np.linspace(
            self.signal_time - len(samples) / self.sample_rate,
            self.signal_time,
            len(samples),
        )

    def reset(self) -> None:
        self._pulse_samples_remaining = 0
        self._samples_until_next_pulse = self._choose_gap()

    def close(self) -> None:
        # Nothing to release for the fake scope.
        pass
