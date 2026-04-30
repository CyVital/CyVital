"""Tests for src/oscilloscope/FakeScope.py."""

from __future__ import annotations

import numpy as np
import pytest

from oscilloscope.FakeScope import FakeScope


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scope(seed: int = 0) -> FakeScope:
    return FakeScope(rng_seed=seed)


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------

class TestFakeScopeInit:
    def test_reaction_sample_rate(self):
        assert _make_scope().reaction_sample_rate == 10_000

    def test_reaction_buffer_size(self):
        assert _make_scope().reaction_buffer_size == 512

    def test_reaction_signal_time_starts_at_zero(self):
        assert _make_scope().reaction_signal_time == 0.0

    def test_emg_sample_rate(self):
        assert _make_scope().emg_sample_rate == 4000

    def test_emg_buffer_size(self):
        assert _make_scope().emg_buffer_size == 2048

    def test_emg_sample_count_starts_at_zero(self):
        assert _make_scope().emg_sample_count == 0

    def test_ecg_sample_rate(self):
        assert _make_scope().ecg_sample_rate == 8192

    def test_ecg_buffer_size(self):
        assert _make_scope().ecg_buffer_size == 4096

    def test_ecg_sample_count_starts_at_zero(self):
        assert _make_scope().ecg_sample_count == 0

    def test_pulse_ox_sample_count_starts_at_zero(self):
        assert _make_scope().pulse_ox_sample_count == 0

    def test_blood_pressure_sample_rate(self):
        assert _make_scope().blood_pressure_sample_rate == 200

    def test_blood_pressure_sample_count_starts_at_zero(self):
        assert _make_scope().blood_pressure_sample_count == 0

    def test_resp_sample_rate(self):
        assert _make_scope().resp_sample_rate == 200

    def test_resp_buffer_size(self):
        assert _make_scope().resp_buffer_size == 2048

    def test_resp_signal_time_starts_at_zero(self):
        assert _make_scope().resp_signal_time == 0.0

    def test_no_seed_creates_scope(self):
        scope = FakeScope()
        assert scope.reaction_sample_rate == 10_000

    def test_seed_produces_reproducible_samples(self):
        s1 = FakeScope(rng_seed=42).get_reaction_samples()
        s2 = FakeScope(rng_seed=42).get_reaction_samples()
        np.testing.assert_array_equal(s1, s2)

    def test_different_seeds_produce_different_samples(self):
        s1 = FakeScope(rng_seed=1).get_reaction_samples()
        s2 = FakeScope(rng_seed=2).get_reaction_samples()
        assert not np.array_equal(s1, s2)


# ---------------------------------------------------------------------------
# Device setup methods (no-ops that reset counters)
# ---------------------------------------------------------------------------

class TestFakeScopeSetup:
    def test_setup_device_reaction_resets_signal_time(self):
        scope = _make_scope()
        scope.get_reaction_samples()
        assert scope.reaction_signal_time > 0.0
        scope.setup_device_reaction()
        assert scope.reaction_signal_time == 0.0

    def test_setup_device_emg_resets_sample_count(self):
        scope = _make_scope()
        scope.get_emg_time_axis(scope.get_emg_samples())
        assert scope.emg_sample_count > 0
        scope.setup_device_emg()
        assert scope.emg_sample_count == 0

    def test_setup_device_ecg_resets_sample_count(self):
        scope = _make_scope()
        scope.get_ecg_time_axis(scope.get_ecg_samples())
        assert scope.ecg_sample_count > 0
        scope.setup_device_ecg()
        assert scope.ecg_sample_count == 0

    def test_setup_device_pulse_ox_resets_sample_count(self):
        scope = _make_scope()
        scope.get_pulse_ox_samples()
        assert scope.pulse_ox_sample_count > 0
        scope.setup_device_pulse_ox()
        assert scope.pulse_ox_sample_count == 0

    def test_setup_device_blood_pressure_resets_sample_count(self):
        scope = _make_scope()
        scope.get_blood_pressure_time_axis(scope.get_blood_pressure_samples())
        assert scope.blood_pressure_sample_count > 0
        scope.setup_device_blood_pressure()
        assert scope.blood_pressure_sample_count == 0

    def test_setup_device_respiratory_resets_signal_time(self):
        scope = _make_scope()
        scope.get_respiratory_samples()
        assert scope.resp_signal_time > 0.0
        scope.setup_device_respiratory()
        assert scope.resp_signal_time == 0.0


# ---------------------------------------------------------------------------
# Sample generators
# ---------------------------------------------------------------------------

class TestFakeScopeGetSamples:
    def setup_method(self):
        self.scope = _make_scope()

    def test_reaction_samples_shape(self):
        s = self.scope.get_reaction_samples()
        assert len(s) == self.scope.reaction_buffer_size

    def test_reaction_samples_dtype(self):
        s = self.scope.get_reaction_samples()
        assert s.dtype == np.float32

    def test_reaction_samples_advances_signal_time(self):
        self.scope.get_reaction_samples()
        expected = self.scope.reaction_buffer_size / self.scope.reaction_sample_rate
        assert self.scope.reaction_signal_time == pytest.approx(expected)

    def test_emg_samples_shape(self):
        s = self.scope.get_emg_samples()
        assert len(s) == self.scope.emg_buffer_size

    def test_emg_samples_dtype(self):
        s = self.scope.get_emg_samples()
        assert s.dtype == np.float32

    def test_ecg_samples_shape(self):
        s = self.scope.get_ecg_samples()
        assert len(s) == self.scope.ecg_buffer_size

    def test_ecg_samples_dtype(self):
        s = self.scope.get_ecg_samples()
        assert s.dtype == np.float32

    def test_pulse_ox_samples_length(self):
        raw = self.scope.get_pulse_ox_samples()
        assert len(raw) == 6

    def test_pulse_ox_samples_increments_count(self):
        self.scope.get_pulse_ox_samples()
        assert self.scope.pulse_ox_sample_count == 1

    def test_pulse_ox_samples_are_bytes(self):
        raw = self.scope.get_pulse_ox_samples()
        assert isinstance(raw, (bytes, bytearray))

    def test_pulse_ox_samples_byte_values_in_range(self):
        raw = self.scope.get_pulse_ox_samples()
        assert all(0 <= b <= 255 for b in raw)

    def test_blood_pressure_samples_shape(self):
        s = self.scope.get_blood_pressure_samples()
        assert len(s) == self.scope.blood_pressure_buffer_size

    def test_blood_pressure_samples_dtype(self):
        s = self.scope.get_blood_pressure_samples()
        assert s.dtype == np.float32

    def test_respiratory_samples_shape(self):
        s = self.scope.get_respiratory_samples()
        assert len(s) == self.scope.resp_buffer_size

    def test_respiratory_samples_dtype(self):
        s = self.scope.get_respiratory_samples()
        assert s.dtype == np.float32

    def test_respiratory_samples_advances_signal_time(self):
        self.scope.get_respiratory_samples()
        expected = self.scope.resp_buffer_size / self.scope.resp_sample_rate
        assert self.scope.resp_signal_time == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Time-axis helpers
# ---------------------------------------------------------------------------

class TestFakeScopeTimeAxes:
    def setup_method(self):
        self.scope = _make_scope()

    def test_emg_time_axis_length(self):
        s = self.scope.get_emg_samples()
        t = self.scope.get_emg_time_axis(s)
        assert len(t) == len(s)

    def test_emg_time_axis_starts_at_zero_initially(self):
        s = self.scope.get_emg_samples()
        t = self.scope.get_emg_time_axis(s)
        assert t[0] == pytest.approx(0.0)

    def test_emg_time_axis_advances_on_successive_calls(self):
        s = self.scope.get_emg_samples()
        t1 = self.scope.get_emg_time_axis(s)
        s2 = self.scope.get_emg_samples()
        t2 = self.scope.get_emg_time_axis(s2)
        assert t2[0] > t1[-1] - 1e-9  # second window starts where first ended

    def test_emg_time_axis_advances_sample_count(self):
        s = self.scope.get_emg_samples()
        self.scope.get_emg_time_axis(s)
        assert self.scope.emg_sample_count == len(s)

    def test_ecg_time_axis_length(self):
        s = self.scope.get_ecg_samples()
        t = self.scope.get_ecg_time_axis(s)
        assert len(t) == len(s)

    def test_ecg_time_axis_starts_at_zero_initially(self):
        s = self.scope.get_ecg_samples()
        t = self.scope.get_ecg_time_axis(s)
        assert t[0] == pytest.approx(0.0)

    def test_ecg_time_axis_advances_sample_count(self):
        s = self.scope.get_ecg_samples()
        self.scope.get_ecg_time_axis(s)
        assert self.scope.ecg_sample_count == len(s)

    def test_reaction_time_axis_length(self):
        s = self.scope.get_reaction_samples()
        t = self.scope.get_reaction_time_axis(s)
        assert len(t) == len(s)

    def test_reaction_time_axis_ends_at_signal_time(self):
        s = self.scope.get_reaction_samples()
        t = self.scope.get_reaction_time_axis(s)
        assert t[-1] == pytest.approx(self.scope.reaction_signal_time)

    def test_respiratory_time_axis_length(self):
        s = self.scope.get_respiratory_samples()
        t = self.scope.get_respiratory_time_axis(s)
        assert len(t) == len(s)

    def test_respiratory_time_axis_ends_at_signal_time(self):
        s = self.scope.get_respiratory_samples()
        t = self.scope.get_respiratory_time_axis(s)
        assert t[-1] == pytest.approx(self.scope.resp_signal_time)

    def test_pulse_ox_time_axis_length_matches_count(self):
        self.scope.get_pulse_ox_samples()
        self.scope.get_pulse_ox_samples()
        t = self.scope.get_pulse_ox_time_axis()
        assert len(t) == self.scope.pulse_ox_sample_count

    def test_pulse_ox_time_axis_empty_initially(self):
        t = self.scope.get_pulse_ox_time_axis()
        assert len(t) == 0

    def test_blood_pressure_time_axis_length(self):
        s = self.scope.get_blood_pressure_samples()
        t = self.scope.get_blood_pressure_time_axis(s)
        assert len(t) == len(s)

    def test_blood_pressure_time_axis_starts_at_zero_initially(self):
        s = self.scope.get_blood_pressure_samples()
        t = self.scope.get_blood_pressure_time_axis(s)
        assert t[0] == pytest.approx(0.0)

    def test_blood_pressure_time_axis_advances_sample_count(self):
        s = self.scope.get_blood_pressure_samples()
        self.scope.get_blood_pressure_time_axis(s)
        assert self.scope.blood_pressure_sample_count == len(s)


# ---------------------------------------------------------------------------
# Lifecycle helpers
# ---------------------------------------------------------------------------

class TestFakeScopeLifecycle:
    def test_reset_does_not_raise(self):
        _make_scope().reset()

    def test_close_does_not_raise(self):
        _make_scope().close()

    def test_reset_and_close_sequence(self):
        scope = _make_scope()
        scope.reset()
        scope.close()
