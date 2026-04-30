"""Synthetic oscilloscope for headless testing and demos.

Provides the same API as Scope but returns generated data
instead of connecting to Digilent hardware.
"""

from __future__ import annotations

import random
from typing import Optional

import numpy as np


class FakeScope:
    """Stand-in for the hardware-backed Scope.

    Generates continuous samples that emulate real sensor signals so the
    GUI and sensor modules can be exercised without a physical device.
    """

    def __init__(
        self,
        *,
        rng_seed: Optional[int] = None,
    ) -> None:
        self.reaction_sample_rate = 10_000
        self.reaction_buffer_size = 512
        self.reaction_signal_time = 0.0

        self.emg_sample_rate = 4000
        self.emg_buffer_size = 2048
        self.emg_sample_count = 0

        self.ecg_sample_rate = 8192
        self.ecg_buffer_size = 4096
        self.ecg_sample_count = 0

        self.pulse_ox_sample_rate = 10
        self.pulse_ox_sample_count = 0

        self.blood_pressure_sample_rate = 200
        self.blood_pressure_buffer_size = 200
        self.blood_pressure_sample_count = 0

        self.resp_sample_rate = 200
        self.resp_buffer_size = 2048
        self.resp_signal_time = 0.0

        self._rng = random.Random(rng_seed)
        self._np_rng = np.random.default_rng(rng_seed)

    # --- Device setup (no-ops for synthetic data) ---

    def setup_device_reaction(self) -> None:
        self.reaction_signal_time = 0.0

    def setup_device_emg(self) -> None:
        self.emg_sample_count = 0

    def setup_device_ecg(self) -> None:
        self.ecg_sample_count = 0

    def setup_device_pulse_ox(self) -> None:
        self.pulse_ox_sample_count = 0

    def setup_device_blood_pressure(self) -> None:
        self.blood_pressure_sample_count = 0

    def setup_device_respiratory(self) -> None:
        self.resp_signal_time = 0.0

    # --- Sample generators ---

    def get_reaction_samples(self) -> np.ndarray:
        n = self.reaction_buffer_size
        noise = self._np_rng.standard_normal(n) * 0.05
        samples = noise.astype(np.float32)
        self.reaction_signal_time += n / self.reaction_sample_rate
        return samples

    def get_emg_samples(self) -> np.ndarray:
        n = self.emg_buffer_size
        samples = (self._np_rng.standard_normal(n) * 0.01).astype(np.float32)
        return samples

    def get_ecg_samples(self) -> np.ndarray:
        n = self.ecg_buffer_size
        samples = (self._np_rng.standard_normal(n) * 0.02).astype(np.float32)
        return samples

    def get_pulse_ox_samples(self) -> bytes:
        """Return 6 bytes encoding synthetic red and IR sensor counts."""
        self.pulse_ox_sample_count += 1
        red = self._rng.randint(30_000, 70_000)
        ir = self._rng.randint(30_000, 70_000)
        return bytes([
            (red >> 16) & 0xFF,
            (red >> 8) & 0xFF,
            red & 0xFF,
            (ir >> 16) & 0xFF,
            (ir >> 8) & 0xFF,
            ir & 0xFF,
        ])

    def get_blood_pressure_samples(self) -> np.ndarray:
        n = self.blood_pressure_buffer_size
        samples = (self._np_rng.standard_normal(n) * 0.01).astype(np.float32)
        return samples

    def get_respiratory_samples(self) -> np.ndarray:
        n = self.resp_buffer_size
        t = np.arange(n) / self.resp_sample_rate + self.resp_signal_time
        samples = (
            0.4 * np.sin(2 * np.pi * 0.2 * t)
            + self._np_rng.standard_normal(n) * 0.01
        ).astype(np.float32)
        self.resp_signal_time += n / self.resp_sample_rate
        return samples

    # --- Time-axis helpers ---

    def get_emg_time_axis(self, samples: np.ndarray) -> np.ndarray:
        t_start = self.emg_sample_count / self.emg_sample_rate
        t_axis = np.arange(len(samples)) / self.emg_sample_rate + t_start
        self.emg_sample_count += len(samples)
        return t_axis

    def get_ecg_time_axis(self, samples: np.ndarray) -> np.ndarray:
        t_start = self.ecg_sample_count / self.ecg_sample_rate
        t_axis = np.arange(len(samples)) / self.ecg_sample_rate + t_start
        self.ecg_sample_count += len(samples)
        return t_axis

    def get_reaction_time_axis(self, samples: np.ndarray) -> np.ndarray:
        n = len(samples)
        return np.linspace(
            self.reaction_signal_time - n / self.reaction_sample_rate,
            self.reaction_signal_time,
            n,
        )

    def get_respiratory_time_axis(self, samples: np.ndarray) -> np.ndarray:
        n = len(samples)
        return np.linspace(
            self.resp_signal_time - n / self.resp_sample_rate,
            self.resp_signal_time,
            n,
        )

    def get_pulse_ox_time_axis(self) -> np.ndarray:
        return np.linspace(0, self.pulse_ox_sample_count, self.pulse_ox_sample_count)

    def get_blood_pressure_time_axis(self, samples: np.ndarray) -> np.ndarray:
        t_start = self.blood_pressure_sample_count / self.blood_pressure_sample_rate
        t_axis = np.arange(len(samples)) / self.blood_pressure_sample_rate + t_start
        self.blood_pressure_sample_count += len(samples)
        return t_axis

    # --- Lifecycle helpers ---

    def reset(self) -> None:
        pass

    def close(self) -> None:
        pass
