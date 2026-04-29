"""Tests for synthetic and hardware-adapter oscilloscope modules."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from oscilloscope import FakeScope as fake_scope_module
from oscilloscope.FakeScope import FakeScope
from oscilloscope import Scope as scope_module
from oscilloscope.Scope import Scope


def test_fake_scope_setup_methods_reset_stream_counters(monkeypatch):
    monkeypatch.setattr(FakeScope, "_throttle_stream", lambda *args, **kwargs: None)
    scope = FakeScope(rng_seed=1, buffer_size=4, emg_buffer_size=4, ecg_buffer_size=4)
    scope.signal_time = 2.0
    scope.ecg_signal_time = 2.0
    scope.emg_sample_count = 5
    scope.pulse_ox_sample_count = 5
    scope.blood_pressure_sample_count = 5
    scope.resp_signal_time = 2.0

    scope.setup_device_reaction()
    scope.setup_device_ecg()
    scope.setup_device_emg()
    scope.setup_device_pulse_ox()
    scope.setup_device_blood_pressure()
    scope.setup_device_respiratory()

    assert scope.signal_time == 0.0
    assert scope.ecg_signal_time == 0.0
    assert scope.emg_sample_count == 0
    assert scope.pulse_ox_sample_count == 0
    assert scope.blood_pressure_sample_count == 0
    assert scope.resp_signal_time == 0.0


def test_fake_scope_generates_samples_and_time_axes(monkeypatch):
    monkeypatch.setattr(FakeScope, "_throttle_stream", lambda *args, **kwargs: None)
    scope = FakeScope(
        rng_seed=2,
        sample_rate=10,
        buffer_size=5,
        emg_sample_rate=10,
        emg_buffer_size=5,
        ecg_sample_rate=10,
        ecg_buffer_size=5,
        pulse_ox_sample_rate=10,
        blood_pressure_sample_rate=10,
        blood_pressure_buffer_size=5,
        resp_sample_rate=10,
        resp_buffer_size=5,
    )

    reaction = scope.get_reaction_samples()
    ecg = scope.get_ecg_samples()
    emg = scope.get_emg_samples()
    pulse = scope.get_pulse_ox_samples()
    pressure = scope.get_blood_pressure_samples()
    respiratory = scope.get_respiratory_samples()

    assert reaction.shape == (5,)
    assert ecg.shape == (5,)
    assert emg.shape == (5,)
    assert len(pulse) == 6
    assert pressure.shape == (5,)
    assert respiratory.shape == (5,)
    assert len(scope.get_reaction_time_axis(reaction)) == 5
    assert len(scope.get_ecg_time_axis(ecg)) == 5
    assert len(scope.get_emg_time_axis(emg)) == 5
    assert len(scope.get_pulse_ox_time_axis()) == scope.pulse_ox_sample_count
    assert len(scope.get_blood_pressure_time_axis(pressure)) == 5
    assert len(scope.get_respiratory_time_axis(respiratory)) == 5


def test_fake_scope_reset_led_close_and_throttle(monkeypatch):
    sleeps = []
    times = iter([0.0, 0.01, 0.20])
    monkeypatch.setattr(fake_scope_module.time, "perf_counter", lambda: next(times))
    monkeypatch.setattr(fake_scope_module.time, "sleep", sleeps.append)

    scope = FakeScope(rng_seed=3, buffer_size=10, sample_rate=100)
    scope._throttle_stream("reaction", 10, 100)
    scope._throttle_stream("reaction", 10, 100)
    scope.reset()

    assert sleeps == [pytest.approx(0.09)]
    assert scope.set_reaction_led(True) is None
    assert scope.close() is None
    assert scope.signal_time == 0.0
    assert scope._stream_clock == {}


class DummyChannel:
    def __init__(self, data=None):
        self.data = data if data is not None else [0.1, 0.2, 0.3]
        self.setup_calls = []
        self.enabled = False
        self.output_state = False

    def setup(self, **kwargs):
        self.setup_calls.append(kwargs)

    def get_data(self):
        return self.data


class DummyAnalogInput:
    def __init__(self, fail_read=False):
        self.channels = [DummyChannel(), DummyChannel()]
        self.fail_read = fail_read
        self.scan_calls = []

    def __getitem__(self, index):
        return self.channels[index]

    def scan_shift(self, **kwargs):
        self.scan_calls.append(kwargs)

    def read_status(self, read_data=True):
        if self.fail_read:
            raise RuntimeError("detached")


class DummyAnalogOutputChannel:
    def __init__(self):
        self.setup_calls = []
        self.setup_am_calls = []
        self.configure_calls = []

    def setup(self, **kwargs):
        self.setup_calls.append(kwargs)

    def setup_am(self, **kwargs):
        self.setup_am_calls.append(kwargs)

    def configure(self, **kwargs):
        self.configure_calls.append(kwargs)


class DummyAnalogIO:
    def __init__(self):
        self.rows = [[MagicMock(value=False), MagicMock(value=0.0)]]
        self.master_enable = False

    def __getitem__(self, index):
        return self.rows[index]


class DummyDigitalIO:
    def __init__(self):
        self.channels = [DummyChannel() for _ in range(4)]
        self.reset_called = False
        self.configure_called = False

    def reset(self):
        self.reset_called = True

    def configure(self):
        self.configure_called = True


class DummyDevice:
    def __init__(self, fail_read=False):
        self.name = "Dummy"
        self.serial_number = "123"
        self.analog_io = DummyAnalogIO()
        self.analog_input = DummyAnalogInput(fail_read=fail_read)
        self.analog_output = [DummyAnalogOutputChannel()]
        self.digital_io = DummyDigitalIO()
        self.open_called = False
        self.close_called = False

    def open(self):
        self.open_called = True

    def close(self):
        self.close_called = True


class DummyI2C:
    def __init__(self, device):
        self.device = device
        self.writes = []
        self.setup_kwargs = None
        self.nak = 0

    def setup(self, **kwargs):
        self.setup_kwargs = kwargs

    def write(self, address, payload):
        self.writes.append((address, payload))

    def read(self, address, count):
        return [0], self.nak

    def write_read(self, address, payload, count):
        return [1, 2, 3, 4, 5, 6], self.nak


def make_scope(monkeypatch, device=None, i2c=None):
    device = device or DummyDevice()
    i2c_factory = i2c or DummyI2C
    monkeypatch.setattr(scope_module.dwf, "Device", lambda: device)
    monkeypatch.setattr(scope_module.Protocols, "I2C", i2c_factory)
    monkeypatch.setattr(scope_module.time, "sleep", lambda seconds: None)
    return Scope(), device


def test_scope_setup_methods_configure_device(monkeypatch):
    scope, device = make_scope(monkeypatch)

    scope.setup_device_reaction()
    scope.setup_device_emg()
    scope.setup_device_ecg()
    scope.setup_device_pulse_ox()
    scope.setup_device_blood_pressure()
    scope.setup_device_respiratory()

    assert device.open_called is True
    assert device.analog_io.master_enable is True
    assert device.digital_io.reset_called is True
    assert device.digital_io.configure_called is True
    assert len(device.analog_input.scan_calls) >= 4
    assert scope.i2c.setup_kwargs["rate"] == 100_000


def test_scope_sample_methods_and_time_axes(monkeypatch):
    scope, _ = make_scope(monkeypatch)
    scope.setup_device_pulse_ox()

    reaction = scope.get_reaction_samples()
    emg = scope.get_emg_samples()
    ecg = scope.get_ecg_samples()
    pulse = scope.get_pulse_ox_samples()
    pressure = scope.get_blood_pressure_samples()
    respiratory = scope.get_respiratory_samples()

    assert np.array_equal(reaction, np.array([0.1, 0.2, 0.3]))
    assert np.array_equal(emg, np.array([0.1, 0.2, 0.3]))
    assert np.array_equal(ecg, np.array([0.1, 0.2, 0.3]))
    assert pulse == [1, 2, 3, 4, 5, 6]
    assert np.array_equal(pressure, np.array([0.1, 0.2, 0.3]))
    assert np.array_equal(respiratory, np.array([0.1, 0.2, 0.3]))
    assert len(scope.get_reaction_time_axis(reaction)) == 3
    assert len(scope.get_emg_time_axis(emg)) == 3
    assert len(scope.get_ecg_time_axis(ecg)) == 3
    assert len(scope.get_pulse_ox_time_axis()) == scope.pulse_ox_sample_count
    assert len(scope.get_blood_pressure_time_axis(pressure)) == 3
    assert len(scope.get_respiratory_time_axis(respiratory)) == 3


def test_scope_error_paths_and_helpers(monkeypatch):
    scope, device = make_scope(monkeypatch, DummyDevice(fail_read=True))

    with pytest.raises(IOError):
        scope.get_reaction_samples()
    with pytest.raises(IOError):
        scope.get_emg_samples()
    with pytest.raises(IOError):
        scope.get_ecg_samples()
    with pytest.raises(IOError):
        scope.get_blood_pressure_samples()
    with pytest.raises(IOError):
        scope.get_respiratory_samples()

    scope.i2c = DummyI2C(device)
    scope.i2c.nak = 1
    assert scope.get_pulse_ox_samples() is None
    assert scope.set_reaction_led(True) is None
    scope.reset()
    scope.close()
    assert device.close_called is True
