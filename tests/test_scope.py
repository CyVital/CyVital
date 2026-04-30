"""Tests for src/oscilloscope/Scope.py.

All hardware access (dwfpy) is intercepted by the MagicMock registered in
conftest.py, so the entire Scope class can be exercised without a physical
device.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch, call

import numpy as np
import pytest

from oscilloscope.Scope import Scope


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scope() -> Scope:
    """Construct a Scope instance using the mocked dwfpy from conftest."""
    return Scope()


def _get_dwfpy_mock() -> MagicMock:
    return sys.modules["dwfpy"]


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------

class TestScopeInit:
    def test_reaction_sample_rate(self):
        assert _make_scope().reaction_sample_rate == 10000

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

    def test_ecg_sample_count_starts_at_zero(self):
        assert _make_scope().ecg_sample_count == 0

    def test_pulse_ox_sample_count_starts_at_zero(self):
        assert _make_scope().pulse_ox_sample_count == 0

    def test_blood_pressure_sample_count_starts_at_zero(self):
        assert _make_scope().blood_pressure_sample_count == 0

    def test_blood_pressure_sample_rate(self):
        assert _make_scope().blood_pressure_sample_rate == 200

    def test_resp_sample_rate(self):
        assert _make_scope().resp_sample_rate == 200

    def test_resp_buffer_size(self):
        assert _make_scope().resp_buffer_size == 2048

    def test_resp_signal_time_starts_at_zero(self):
        assert _make_scope().resp_signal_time == 0.0

    def test_max_addr_7bit(self):
        assert _make_scope().MAX_ADDR_7BIT == 0x57

    def test_max_addr_8bit_is_double_7bit(self):
        scope = _make_scope()
        assert scope.MAX_ADDR_8BIT == scope.MAX_ADDR_7BIT << 1

    def test_device_is_created(self):
        scope = _make_scope()
        assert scope.device is not None

    def test_scope_attribute_set_by_setup_reaction(self):
        # setup_device_reaction() sets self.scope via setup_device_analog()
        scope = _make_scope()
        assert hasattr(scope, "scope")

    def test_init_catches_device_open_error(self, capsys):
        """Lines 33-34: bare except in __init__ prints 'Device not found'."""
        device_mock = _get_dwfpy_mock().Device.return_value
        with patch.object(device_mock, "open", side_effect=RuntimeError("no hw")):
            scope = Scope()  # must not raise
        out = capsys.readouterr().out
        assert "Device not found" in out


# ---------------------------------------------------------------------------
# setup_device_analog
# ---------------------------------------------------------------------------

class TestSetupDeviceAnalog:
    def test_sets_scope_to_analog_input(self):
        scope = _make_scope()
        scope.setup_device_analog()
        assert scope.scope is scope.device.analog_input

    def test_enables_power_supply(self):
        scope = _make_scope()
        scope.setup_device_analog()
        assert scope.device.analog_io.master_enable is True


# ---------------------------------------------------------------------------
# setup_device_reaction
# ---------------------------------------------------------------------------

class TestSetupDeviceReaction:
    def test_resets_digital_io(self):
        scope = _make_scope()
        scope.device.digital_io.reset.reset_mock()
        scope.setup_device_reaction()
        scope.device.digital_io.reset.assert_called()

    def test_configures_digital_io(self):
        scope = _make_scope()
        scope.device.digital_io.configure.reset_mock()
        scope.setup_device_reaction()
        scope.device.digital_io.configure.assert_called()

    def test_enables_four_channels(self):
        scope = _make_scope()
        scope.setup_device_reaction()
        for i in range(4):
            assert scope.device.digital_io.channels[i].enabled is True

    def test_calls_scan_shift(self):
        scope = _make_scope()
        scope.scope.scan_shift.reset_mock()
        scope.setup_device_reaction()
        scope.scope.scan_shift.assert_called()


# ---------------------------------------------------------------------------
# setup_device_emg
# ---------------------------------------------------------------------------

class TestSetupDeviceEmg:
    def test_resets_emg_sample_count(self):
        scope = _make_scope()
        scope.emg_sample_count = 99
        scope.setup_device_emg()
        assert scope.emg_sample_count == 0

    def test_resets_digital_io(self):
        scope = _make_scope()
        scope.device.digital_io.reset.reset_mock()
        scope.setup_device_emg()
        scope.device.digital_io.reset.assert_called()

    def test_calls_scan_shift(self):
        scope = _make_scope()
        scope.setup_device_emg()
        scope.scope.scan_shift.assert_called()

    def test_sets_up_channel_range(self):
        scope = _make_scope()
        scope.setup_device_emg()
        scope.scope[0].setup.assert_called_with(range=0.01)


# ---------------------------------------------------------------------------
# setup_device_ecg
# ---------------------------------------------------------------------------

class TestSetupDeviceEcg:
    def test_resets_ecg_sample_count(self):
        scope = _make_scope()
        scope.ecg_sample_count = 50
        scope.setup_device_ecg()
        assert scope.ecg_sample_count == 0

    def test_creates_wavegen_attribute(self):
        scope = _make_scope()
        scope.setup_device_ecg()
        assert hasattr(scope, "wavegen")

    def test_configures_wavegen_with_start(self):
        scope = _make_scope()
        scope.setup_device_ecg()
        scope.wavegen[0].configure.assert_called_with(start=True)

    def test_calls_scan_shift(self):
        scope = _make_scope()
        scope.setup_device_ecg()
        scope.scope.scan_shift.assert_called()


# ---------------------------------------------------------------------------
# setup_device_pulse_ox
# ---------------------------------------------------------------------------

class TestSetupDevicePulseOx:
    """setup_device_pulse_ox performs I2C initialisation.

    The Protocols.I2C mock is accessed via the dwfpy mock chain and must be
    pre-configured so that i2c.read() returns an unpackable (mode, nak) pair.
    """

    def _configure_i2c(self, nak_value=0) -> MagicMock:
        """Wire up the I2C mock and return it so tests can inspect it."""
        i2c_mock = MagicMock()
        i2c_mock.read.return_value = (None, nak_value)
        _get_dwfpy_mock().protocols.Protocols.I2C.return_value = i2c_mock
        return i2c_mock

    def test_resets_pulse_ox_sample_count(self):
        scope = _make_scope()
        scope.pulse_ox_sample_count = 7
        self._configure_i2c(nak_value=0)
        with patch("time.sleep"):
            scope.setup_device_pulse_ox()
        assert scope.pulse_ox_sample_count == 0

    def test_creates_i2c_attribute(self):
        scope = _make_scope()
        i2c = self._configure_i2c(nak_value=0)
        with patch("time.sleep"):
            scope.setup_device_pulse_ox()
        assert scope.i2c is i2c

    def test_writes_eight_config_registers(self):
        scope = _make_scope()
        i2c = self._configure_i2c(nak_value=0)
        with patch("time.sleep"):
            scope.setup_device_pulse_ox()
        # 8 config register pairs plus the 2 soft-reset writes = ≥8 calls
        assert i2c.write.call_count >= 8

    def test_nak_minus_one_raises_io_error(self):
        scope = _make_scope()
        self._configure_i2c(nak_value=-1)
        with patch("time.sleep"):
            with pytest.raises(IOError, match="I2C NACK"):
                scope.setup_device_pulse_ox()

    def test_calls_reset_first(self):
        scope = _make_scope()
        self._configure_i2c(nak_value=0)
        scope.device.digital_io.reset.reset_mock()
        with patch("time.sleep"):
            scope.setup_device_pulse_ox()
        scope.device.digital_io.reset.assert_called()


# ---------------------------------------------------------------------------
# setup_device_blood_pressure
# ---------------------------------------------------------------------------

class TestSetupDeviceBloodPressure:
    def test_sets_scope_to_analog_input(self):
        scope = _make_scope()
        scope.setup_device_blood_pressure()
        assert scope.scope is scope.device.analog_input


# ---------------------------------------------------------------------------
# setup_device_respiratory
# ---------------------------------------------------------------------------

class TestSetupDeviceRespiratory:
    def test_sets_scope_to_analog_input(self):
        scope = _make_scope()
        scope.setup_device_respiratory()
        assert scope.scope is scope.device.analog_input

    def test_configures_scan_shift(self):
        scope = _make_scope()
        scope.setup_device_respiratory()
        scope.scope.scan_shift.assert_called()

    def test_resets_digital_io(self):
        scope = _make_scope()
        scope.device.digital_io.reset.reset_mock()
        scope.setup_device_respiratory()
        scope.device.digital_io.reset.assert_called()


# ---------------------------------------------------------------------------
# get_reaction_samples
# ---------------------------------------------------------------------------

class TestGetReactionSamples:
    def test_returns_numpy_array(self):
        scope = _make_scope()
        scope.scope.channels[0].get_data.return_value = [0.1, 0.2, 0.3]
        result = scope.get_reaction_samples()
        assert isinstance(result, np.ndarray)
        np.testing.assert_array_almost_equal(result, [0.1, 0.2, 0.3])

    def test_increments_reaction_signal_time(self):
        scope = _make_scope()
        scope.scope.channels[0].get_data.return_value = [0.0] * 100
        scope.reaction_signal_time = 0.0
        scope.get_reaction_samples()
        assert scope.reaction_signal_time == pytest.approx(100 / 10000)

    def test_raises_io_error_on_read_failure(self):
        scope = _make_scope()
        scope.scope.read_status.side_effect = RuntimeError("hardware error")
        with pytest.raises(IOError, match="Scope not attached."):
            scope.get_reaction_samples()
        scope.scope.read_status.side_effect = None  # restore


# ---------------------------------------------------------------------------
# get_emg_samples
# ---------------------------------------------------------------------------

class TestGetEmgSamples:
    def test_returns_numpy_array(self):
        scope = _make_scope()
        scope.scope.channels[0].get_data.return_value = [1.0, 2.0, 3.0]
        result = scope.get_emg_samples()
        assert isinstance(result, np.ndarray)

    def test_raises_io_error_on_read_failure(self):
        scope = _make_scope()
        scope.scope.read_status.side_effect = RuntimeError("bad")
        with pytest.raises(IOError, match="Scope not attached."):
            scope.get_emg_samples()
        scope.scope.read_status.side_effect = None


# ---------------------------------------------------------------------------
# get_ecg_samples
# ---------------------------------------------------------------------------

class TestGetEcgSamples:
    def test_returns_numpy_array(self):
        scope = _make_scope()
        scope.scope.channels[0].get_data.return_value = [0.5, 0.6, 0.7]
        result = scope.get_ecg_samples()
        assert isinstance(result, np.ndarray)

    def test_raises_io_error_on_read_failure(self):
        scope = _make_scope()
        scope.scope.read_status.side_effect = RuntimeError("bad")
        with pytest.raises(IOError, match="Scope not attached."):
            scope.get_ecg_samples()
        scope.scope.read_status.side_effect = None


# ---------------------------------------------------------------------------
# get_pulse_ox_samples
# ---------------------------------------------------------------------------

class TestGetPulseOxSamples:
    def setup_method(self):
        self.scope = _make_scope()
        self.scope.i2c = MagicMock()

    def test_returns_samples_when_nak_zero(self):
        expected = [1, 2, 3, 4, 5, 6]
        self.scope.i2c.write_read.return_value = (expected, 0)
        result = self.scope.get_pulse_ox_samples()
        assert result == expected

    def test_increments_sample_count_on_success(self):
        self.scope.i2c.write_read.return_value = ([1, 2, 3, 4, 5, 6], 0)
        self.scope.pulse_ox_sample_count = 0
        self.scope.get_pulse_ox_samples()
        assert self.scope.pulse_ox_sample_count == 1

    def test_returns_none_when_nak_nonzero(self):
        self.scope.i2c.write_read.return_value = ([], 2)
        result = self.scope.get_pulse_ox_samples()
        assert result is None

    def test_does_not_increment_count_on_nak(self):
        self.scope.i2c.write_read.return_value = ([], 1)
        self.scope.pulse_ox_sample_count = 0
        self.scope.get_pulse_ox_samples()
        assert self.scope.pulse_ox_sample_count == 0

    def test_raises_io_error_on_exception(self):
        self.scope.i2c.write_read.side_effect = RuntimeError("bad")
        with pytest.raises(IOError, match="Scope not attached."):
            self.scope.get_pulse_ox_samples()


# ---------------------------------------------------------------------------
# get_blood_pressure_samples
# ---------------------------------------------------------------------------

class TestGetBloodPressureSamples:
    def test_returns_numpy_array(self):
        scope = _make_scope()
        scope.scope.channels[0].get_data.return_value = [0.3, 0.4, 0.5]
        result = scope.get_blood_pressure_samples()
        assert isinstance(result, np.ndarray)

    def test_raises_io_error_on_read_failure(self):
        scope = _make_scope()
        scope.scope.read_status.side_effect = RuntimeError("bad")
        with pytest.raises(IOError, match="Scope not attached."):
            scope.get_blood_pressure_samples()
        scope.scope.read_status.side_effect = None


# ---------------------------------------------------------------------------
# get_respiratory_samples
# ---------------------------------------------------------------------------

class TestGetRespiratorySamples:
    def test_returns_numpy_array(self):
        scope = _make_scope()
        scope.scope.channels[0].get_data.return_value = [0.1, 0.2, 0.3]
        result = scope.get_respiratory_samples()
        assert isinstance(result, np.ndarray)

    def test_increments_resp_signal_time(self):
        scope = _make_scope()
        scope.scope.channels[0].get_data.return_value = [0.0] * 50
        scope.resp_signal_time = 0.0
        scope.get_respiratory_samples()
        assert scope.resp_signal_time == pytest.approx(50 / 200)

    def test_raises_io_error_on_read_failure(self):
        scope = _make_scope()
        scope.scope.read_status.side_effect = RuntimeError("bad")
        with pytest.raises(IOError, match="Scope not attached."):
            scope.get_respiratory_samples()
        scope.scope.read_status.side_effect = None


# ---------------------------------------------------------------------------
# Time-axis methods
# ---------------------------------------------------------------------------

class TestTimeAxisMethods:
    def setup_method(self):
        self.scope = _make_scope()

    # get_emg_time_axis
    def test_emg_time_axis_length(self):
        samples = np.zeros(100)
        t = self.scope.get_emg_time_axis(samples)
        assert len(t) == 100

    def test_emg_time_axis_increments_sample_count(self):
        self.scope.emg_sample_count = 0
        self.scope.get_emg_time_axis(np.zeros(64))
        assert self.scope.emg_sample_count == 64

    def test_emg_time_axis_uses_existing_count_as_offset(self):
        self.scope.emg_sample_count = 40
        t = self.scope.get_emg_time_axis(np.zeros(10))
        assert t[0] == pytest.approx(40 / 4000)

    def test_emg_time_axis_second_call_continues(self):
        self.scope.emg_sample_count = 0
        t1 = self.scope.get_emg_time_axis(np.zeros(10))
        t2 = self.scope.get_emg_time_axis(np.zeros(10))
        assert t2[0] > t1[-1] or np.isclose(t2[0], t1[-1])

    # get_ecg_time_axis
    def test_ecg_time_axis_length(self):
        t = self.scope.get_ecg_time_axis(np.zeros(50))
        assert len(t) == 50

    def test_ecg_time_axis_increments_sample_count(self):
        self.scope.ecg_sample_count = 0
        self.scope.get_ecg_time_axis(np.zeros(32))
        assert self.scope.ecg_sample_count == 32

    def test_ecg_time_axis_uses_existing_count(self):
        self.scope.ecg_sample_count = 8192
        t = self.scope.get_ecg_time_axis(np.zeros(10))
        assert t[0] == pytest.approx(8192 / 8192)  # == 1.0 s

    # get_reaction_time_axis
    def test_reaction_time_axis_length(self):
        self.scope.reaction_signal_time = 1.0
        t = self.scope.get_reaction_time_axis(np.zeros(20))
        assert len(t) == 20

    def test_reaction_time_axis_endpoint_equals_signal_time(self):
        self.scope.reaction_signal_time = 2.5
        t = self.scope.get_reaction_time_axis(np.zeros(10))
        assert t[-1] == pytest.approx(2.5)

    def test_reaction_time_axis_startpoint(self):
        self.scope.reaction_signal_time = 1.0
        samples = np.zeros(1000)
        t = self.scope.get_reaction_time_axis(samples)
        assert t[0] == pytest.approx(1.0 - len(samples) / 10000)

    # get_respiratory_time_axis
    def test_respiratory_time_axis_length(self):
        t = self.scope.get_respiratory_time_axis(np.zeros(15))
        assert len(t) == 15

    def test_respiratory_time_axis_endpoint(self):
        self.scope.resp_signal_time = 3.0
        t = self.scope.get_respiratory_time_axis(np.zeros(10))
        assert t[-1] == pytest.approx(3.0)

    # get_pulse_ox_time_axis
    def test_pulse_ox_time_axis_length(self):
        self.scope.pulse_ox_sample_count = 5
        t = self.scope.get_pulse_ox_time_axis()
        assert len(t) == 5

    def test_pulse_ox_time_axis_zero_samples(self):
        self.scope.pulse_ox_sample_count = 0
        t = self.scope.get_pulse_ox_time_axis()
        assert len(t) == 0

    # get_blood_pressure_time_axis
    def test_blood_pressure_time_axis_length(self):
        t = self.scope.get_blood_pressure_time_axis(np.zeros(30))
        assert len(t) == 30

    def test_blood_pressure_time_axis_increments_count(self):
        self.scope.blood_pressure_sample_count = 0
        self.scope.get_blood_pressure_time_axis(np.zeros(20))
        assert self.scope.blood_pressure_sample_count == 20

    def test_blood_pressure_time_axis_uses_existing_count(self):
        self.scope.blood_pressure_sample_count = 200
        t = self.scope.get_blood_pressure_time_axis(np.zeros(10))
        assert t[0] == pytest.approx(200 / 200)  # == 1.0 s


# ---------------------------------------------------------------------------
# reset and close
# ---------------------------------------------------------------------------

class TestResetAndClose:
    def test_reset_calls_digital_io_reset(self):
        scope = _make_scope()
        scope.device.digital_io.reset.reset_mock()
        scope.reset()
        scope.device.digital_io.reset.assert_called_once()

    def test_reset_calls_digital_io_configure(self):
        scope = _make_scope()
        scope.device.digital_io.configure.reset_mock()
        scope.reset()
        scope.device.digital_io.configure.assert_called_once()

    def test_close_calls_device_close(self):
        scope = _make_scope()
        scope.device.close.reset_mock()
        scope.close()
        scope.device.close.assert_called_once()
