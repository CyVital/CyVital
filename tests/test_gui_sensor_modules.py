"""Tests for GUI sensor modules: ECG, EMG, BloodPressure, PulseOx, Reaction, Respiratory."""

from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from gui.models import SensorUpdate
from gui.sensors.ecg import ECGSensorModule
from gui.sensors.emg import EMGSensorModule
from gui.sensors.blood_pressure import BloodPressureSensorModule
from gui.sensors.pulse_ox import PulseOxSensorModule
from gui.sensors.reaction import ReactionSensorModule
from gui.sensors.respiratory import RespiratorySensorModule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scope(**kwargs):
    """Return a MagicMock that behaves like a minimal Scope."""
    scope = MagicMock()
    for attr, value in kwargs.items():
        setattr(scope, attr, value)
    return scope


def _flat_t_s(n: int = 64, sr: float = 8192.0):
    t = np.linspace(0.0, n / sr, n)
    s = np.zeros(n, dtype=np.float32)
    return t, s


# ---------------------------------------------------------------------------
# ECGSensorModule
# ---------------------------------------------------------------------------

class TestECGSensorModule:
    def setup_method(self):
        self.module = ECGSensorModule()

    def test_supports_export_true(self):
        assert self.module.supports_export is True

    def test_get_figure_returns_figure(self):
        fig = self.module.get_figure()
        assert fig is not None

    def test_setup_scope_success(self):
        scope = _make_scope()
        self.module.setup_scope(scope)
        scope.setup_device_ecg.assert_called_once()

    def test_setup_scope_io_error_disables_streaming(self):
        scope = _make_scope()
        scope.setup_device_ecg.side_effect = IOError("no device")
        self.module.setup_scope(scope)
        assert self.module.supports_streaming is False

    def test_setup_scope_os_error_disables_streaming(self):
        scope = _make_scope()
        scope.setup_device_ecg.side_effect = OSError("no device")
        self.module.setup_scope(scope)
        assert self.module.supports_streaming is False

    def test_setup_scope_not_implemented_disables_streaming(self):
        scope = _make_scope()
        scope.setup_device_ecg.side_effect = NotImplementedError
        self.module.setup_scope(scope)
        assert self.module.supports_streaming is False

    def test_update_returns_sensor_update(self):
        t, s = _flat_t_s()
        scope = _make_scope()
        scope.get_ecg_samples.return_value = s
        scope.get_ecg_time_axis.return_value = t
        result = self.module.update(scope)
        assert isinstance(result, SensorUpdate)

    def test_update_no_bpm_returns_dashes(self):
        t, s = _flat_t_s()
        scope = _make_scope()
        scope.get_ecg_samples.return_value = s
        scope.get_ecg_time_axis.return_value = t
        result = self.module.update(scope)
        assert result.primary_value == "--"
        assert result.secondary_value == "--"

    def test_update_with_bpm_returns_formatted_string(self):
        t, s = _flat_t_s()
        scope = _make_scope()
        scope.get_ecg_samples.return_value = s
        scope.get_ecg_time_axis.return_value = t
        # Patch update_plot so it doesn't overwrite the attributes we set below.
        with patch.object(self.module.plot, "update_plot", return_value=()):
            self.module.plot.latest_bpm = 72.5
            self.module.plot.avg_bpm = 71.0
            self.module.plot.time_values = [1.0]
            self.module.plot.recent_peak_times = [0.5]
            result = self.module.update(scope)
        assert "BPM" in result.primary_value
        assert "BPM" in result.secondary_value
        assert result.log_message is not None

    def test_update_io_error_returns_dashes(self):
        scope = _make_scope()
        scope.get_ecg_samples.side_effect = IOError("no scope")
        result = self.module.update(scope)
        assert result.primary_value == "--"
        assert result.secondary_value == "--"
        assert "IO Error" in result.log_message
        assert result.artists == ()

    def test_update_with_bpm_no_avg(self):
        t, s = _flat_t_s()
        scope = _make_scope()
        scope.get_ecg_samples.return_value = s
        scope.get_ecg_time_axis.return_value = t
        with patch.object(self.module.plot, "update_plot", return_value=()):
            self.module.plot.latest_bpm = 60.0
            self.module.plot.avg_bpm = None
            self.module.plot.time_values = [1.0]
            self.module.plot.recent_peak_times = [0.5]
            result = self.module.update(scope)
        # secondary falls back to latest when avg is None
        assert "60.0 BPM" in result.secondary_value

    def test_shift_history_window_delegates(self):
        with patch.object(self.module.plot, "shift_review_window", return_value=True) as mock:
            result = self.module.shift_history_window(1)
        mock.assert_called_once_with(1)
        assert result is True

    def test_save_data_produces_xlsx(self, tmp_path, monkeypatch):
        from PlotManager import PlotManager
        monkeypatch.setattr(
            PlotManager,
            "_prepare_export_path",
            lambda self, filename: tmp_path / filename,
        )
        t, s = _flat_t_s()
        scope = _make_scope()
        scope.get_ecg_samples.return_value = s
        scope.get_ecg_time_axis.return_value = t
        self.module.update(scope)
        self.module.plot.selected_samples = np.array([])
        self.module.plot.selected_times = np.array([])
        path = self.module.save_data()
        assert path.endswith(".xlsx")

    def test_pause_calls_plot_all(self):
        with patch.object(self.module.plot, "plot_all") as mock:
            self.module.pause()
        mock.assert_called_once()

    def test_cleanup_calls_close_plot(self):
        with patch.object(self.module.plot, "_close_plot") as mock:
            self.module.cleanup()
        mock.assert_called_once()


# ---------------------------------------------------------------------------
# EMGSensorModule
# ---------------------------------------------------------------------------

class TestEMGSensorModule:
    def setup_method(self):
        self.module = EMGSensorModule()

    def test_supports_export_true(self):
        assert self.module.supports_export is True

    def test_get_figure_returns_figure(self):
        assert self.module.get_figure() is not None

    def test_setup_scope_success(self):
        scope = _make_scope()
        self.module.setup_scope(scope)
        scope.setup_device_emg.assert_called_once()

    def test_setup_scope_failure_disables_streaming(self):
        scope = _make_scope()
        scope.setup_device_emg.side_effect = IOError("no device")
        self.module.setup_scope(scope)
        assert self.module.supports_streaming is False

    def test_update_returns_sensor_update(self):
        n = 64
        t = np.linspace(0, n / 4000, n)
        s = np.zeros(n, dtype=np.float32)
        scope = _make_scope()
        scope.get_emg_samples.return_value = s
        scope.get_emg_time_axis.return_value = t
        result = self.module.update(scope)
        assert isinstance(result, SensorUpdate)

    def test_update_io_error_returns_error_message(self):
        scope = _make_scope()
        scope.get_emg_samples.side_effect = IOError("no scope")
        result = self.module.update(scope)
        assert "IO Error" in result.log_message
        assert result.artists == ()

    def test_shift_history_window_delegates(self):
        with patch.object(self.module.plot, "shift_review_window", return_value=True) as mock:
            result = self.module.shift_history_window(-1)
        mock.assert_called_once_with(-1)
        assert result is True

    def test_pause_calls_plot_all(self):
        with patch.object(self.module.plot, "plot_all") as mock:
            self.module.pause()
        mock.assert_called_once()

    def test_cleanup_calls_close_plot(self):
        with patch.object(self.module.plot, "_close_plot") as mock:
            self.module.cleanup()
        mock.assert_called_once()

    def test_save_data_produces_xlsx(self, tmp_path, monkeypatch):
        from PlotManager import PlotManager
        monkeypatch.setattr(
            PlotManager,
            "_prepare_export_path",
            lambda self, filename: tmp_path / filename,
        )
        n = 64
        t = np.linspace(0, n / 4000, n)
        s = np.zeros(n, dtype=np.float32)
        scope = _make_scope()
        scope.get_emg_samples.return_value = s
        scope.get_emg_time_axis.return_value = t
        self.module.update(scope)
        self.module.plot.selected_samples = np.array([])
        self.module.plot.selected_times = np.array([])
        path = self.module.save_data()
        assert path.endswith(".xlsx")


# ---------------------------------------------------------------------------
# BloodPressureSensorModule
# ---------------------------------------------------------------------------

class TestBloodPressureSensorModule:
    def setup_method(self):
        self.module = BloodPressureSensorModule()

    def test_supports_export_true(self):
        assert self.module.supports_export is True

    def test_get_figure_returns_figure(self):
        assert self.module.get_figure() is not None

    def test_setup_scope_success(self):
        scope = _make_scope()
        self.module.setup_scope(scope)
        scope.setup_device_blood_pressure.assert_called_once()

    def test_setup_scope_failure_disables_streaming(self):
        scope = _make_scope()
        scope.setup_device_blood_pressure.side_effect = IOError("no device")
        self.module.setup_scope(scope)
        assert self.module.supports_streaming is False

    def test_update_returns_sensor_update(self):
        n = 64
        t = np.linspace(0, n / 200, n)
        s = np.full(n, 0.5, dtype=np.float32)
        scope = _make_scope()
        scope.get_blood_pressure_samples.return_value = s
        scope.get_blood_pressure_time_axis.return_value = t
        result = self.module.update(scope)
        assert isinstance(result, SensorUpdate)
        assert result.log_message == "Displaying data"

    def test_update_io_error_returns_error_message(self):
        scope = _make_scope()
        scope.get_blood_pressure_samples.side_effect = IOError("no scope")
        result = self.module.update(scope)
        assert "IO Error" in result.log_message
        assert result.artists == ()

    def test_shift_history_window_delegates(self):
        with patch.object(self.module.plot, "shift_review_window", return_value=True) as mock:
            result = self.module.shift_history_window(1)
        mock.assert_called_once_with(1)
        assert result is True

    def test_pause_calls_plot_all(self):
        with patch.object(self.module.plot, "plot_all") as mock:
            self.module.pause()
        mock.assert_called_once()

    def test_cleanup_calls_close_plot(self):
        with patch.object(self.module.plot, "_close_plot") as mock:
            self.module.cleanup()
        mock.assert_called_once()

    def test_save_data_produces_xlsx(self, tmp_path, monkeypatch):
        from PlotManager import PlotManager
        monkeypatch.setattr(
            PlotManager,
            "_prepare_export_path",
            lambda self, filename: tmp_path / filename,
        )
        n = 64
        t = np.linspace(0, n / 200, n)
        s = np.full(n, 0.5, dtype=np.float32)
        scope = _make_scope()
        scope.get_blood_pressure_samples.return_value = s
        scope.get_blood_pressure_time_axis.return_value = t
        self.module.update(scope)
        path = self.module.save_data()
        assert path.endswith(".xlsx")


# ---------------------------------------------------------------------------
# PulseOxSensorModule
# ---------------------------------------------------------------------------

class TestPulseOxSensorModule:
    def setup_method(self):
        self.module = PulseOxSensorModule()

    def test_supports_export_true(self):
        assert self.module.supports_export is True

    def test_get_figure_returns_figure(self):
        assert self.module.get_figure() is not None

    def test_setup_scope_success(self):
        scope = _make_scope()
        self.module.setup_scope(scope)
        scope.setup_device_pulse_ox.assert_called_once()

    def test_setup_scope_failure_disables_streaming(self):
        scope = _make_scope()
        scope.setup_device_pulse_ox.side_effect = IOError("no device")
        self.module.setup_scope(scope)
        assert self.module.supports_streaming is False

    def _make_pulse_ox_scope(self, n_samples: int = 10):
        """Return a scope mock with minimal pulse-ox data."""
        base = 50000
        samples_list = []
        for i in range(n_samples):
            red = base + i * 100
            ir = base + i * 80
            samples_list.append([
                (red >> 16) & 0xFF, (red >> 8) & 0xFF, red & 0xFF,
                (ir >> 16) & 0xFF, (ir >> 8) & 0xFF, ir & 0xFF,
            ])
        scope = _make_scope()
        scope.get_pulse_ox_samples.side_effect = samples_list
        scope.get_pulse_ox_time_axis.return_value = np.arange(n_samples, dtype=float)
        return scope

    def test_update_no_bpm_returns_dashes(self):
        scope = self._make_pulse_ox_scope()
        self.module.plot.bpm = None
        self.module.plot.spo2 = None
        result = self.module.update(scope)
        assert isinstance(result, SensorUpdate)
        assert result.primary_value == "--"

    def test_update_with_bpm_and_spo2(self):
        scope = self._make_pulse_ox_scope()
        with patch.object(self.module.plot, "update_plot", return_value=()):
            self.module.plot.bpm = 72.0
            self.module.plot.spo2 = 98.5
            result = self.module.update(scope)
        assert "%" in result.primary_value
        assert "bpm" in result.secondary_value

    def test_update_io_error_returns_error_message(self):
        scope = _make_scope()
        scope.get_pulse_ox_samples.side_effect = IOError("no scope")
        result = self.module.update(scope)
        assert "IO Error" in result.log_message
        assert result.artists == ()

    def test_shift_history_window_delegates(self):
        with patch.object(self.module.plot, "shift_review_window", return_value=True) as mock:
            result = self.module.shift_history_window(1)
        mock.assert_called_once_with(1)
        assert result is True

    def test_pause_calls_plot_all(self):
        with patch.object(self.module.plot, "plot_all") as mock:
            self.module.pause()
        mock.assert_called_once()

    def test_cleanup_calls_close_plot(self):
        with patch.object(self.module.plot, "_close_plot") as mock:
            self.module.cleanup()
        mock.assert_called_once()

    def test_save_data_produces_xlsx(self, tmp_path, monkeypatch):
        from PlotManager import PlotManager
        monkeypatch.setattr(
            PlotManager,
            "_prepare_export_path",
            lambda self, filename: tmp_path / filename,
        )
        path = self.module.save_data()
        assert path.endswith(".xlsx")


# ---------------------------------------------------------------------------
# ReactionSensorModule
# ---------------------------------------------------------------------------

class TestReactionSensorModule:
    def setup_method(self):
        self.module = ReactionSensorModule()

    def test_supports_export_true(self):
        assert self.module.supports_export is True

    def test_get_figure_returns_figure(self):
        assert self.module.get_figure() is not None

    def test_setup_scope_success(self):
        scope = _make_scope()
        self.module.setup_scope(scope)
        scope.setup_device_reaction.assert_called_once()

    def test_setup_scope_failure_disables_streaming(self):
        scope = _make_scope()
        scope.setup_device_reaction.side_effect = IOError("no device")
        self.module.setup_scope(scope)
        assert self.module.supports_streaming is False

    def test_update_no_reactions_returns_dashes(self):
        n = 64
        t = np.linspace(0, n / 10000, n)
        s = np.zeros(n, dtype=np.float32)
        scope = _make_scope()
        scope.get_reaction_samples.return_value = s
        scope.get_reaction_time_axis.return_value = t
        self.module.plot.reaction_times = []
        result = self.module.update(scope)
        assert result.primary_value == "--"
        assert result.secondary_value == "--"
        assert "Waiting" in result.log_message

    def test_update_with_reactions_returns_formatted_values(self):
        n = 64
        t = np.linspace(0, n / 10000, n)
        s = np.zeros(n, dtype=np.float32)
        scope = _make_scope()
        scope.get_reaction_samples.return_value = s
        scope.get_reaction_time_axis.return_value = t
        self.module.plot.reaction_times = [250.0, 300.0, 275.0]
        result = self.module.update(scope)
        assert "ms" in result.primary_value
        assert "ms" in result.secondary_value
        assert "Trials recorded" in result.log_message

    def test_update_io_error_returns_error_message(self):
        scope = _make_scope()
        scope.get_reaction_samples.side_effect = IOError("no scope")
        result = self.module.update(scope)
        assert "IO Error" in result.log_message
        assert result.artists == ()

    def test_shift_history_window_delegates(self):
        with patch.object(self.module.plot, "shift_review_window", return_value=True) as mock:
            result = self.module.shift_history_window(1)
        mock.assert_called_once_with(1)
        assert result is True

    def test_pause_calls_plot_all(self):
        with patch.object(self.module.plot, "plot_all") as mock:
            self.module.pause()
        mock.assert_called_once()

    def test_cleanup_calls_close_plot(self):
        with patch.object(self.module.plot, "_close_plot") as mock:
            self.module.cleanup()
        mock.assert_called_once()

    def test_save_data_produces_xlsx(self, tmp_path, monkeypatch):
        from PlotManager import PlotManager
        monkeypatch.setattr(
            PlotManager,
            "_prepare_export_path",
            lambda self, filename: tmp_path / filename,
        )
        self.module.plot.selected_samples = np.array([])
        self.module.plot.selected_times = np.array([])
        path = self.module.save_data()
        assert path.endswith(".xlsx")


# ---------------------------------------------------------------------------
# RespiratorySensorModule
# ---------------------------------------------------------------------------

class TestRespiratorySensorModule:
    def setup_method(self):
        self.module = RespiratorySensorModule()

    def test_supports_export_true(self):
        assert self.module.supports_export is True

    def test_get_figure_returns_figure(self):
        assert self.module.get_figure() is not None

    def test_configured_false_initially(self):
        assert self.module._configured is False

    def _make_resp_scope(self, n: int = 15):
        t = np.linspace(0, n / 50, n)
        s = np.sin(2 * np.pi * 0.2 * t).astype(np.float32)
        scope = _make_scope()
        scope.get_respiratory_samples.return_value = s
        scope.get_respiratory_time_axis.return_value = t
        return scope

    def test_first_update_calls_setup_if_available(self):
        scope = self._make_resp_scope()
        self.module.update(scope)
        scope.setup_device_respiratory.assert_called_once()
        assert self.module._configured is True

    def test_second_update_does_not_call_setup_again(self):
        scope = self._make_resp_scope()
        self.module.update(scope)
        scope.get_respiratory_samples.return_value = np.zeros(15, dtype=np.float32)
        scope.get_respiratory_time_axis.return_value = np.linspace(0, 0.3, 15)
        self.module.update(scope)
        scope.setup_device_respiratory.assert_called_once()

    def test_update_without_setup_attr_still_works(self):
        scope = self._make_resp_scope()
        del scope.setup_device_respiratory
        result = self.module.update(scope)
        assert isinstance(result, SensorUpdate)

    def test_update_returns_sensor_update(self):
        scope = self._make_resp_scope()
        result = self.module.update(scope)
        assert isinstance(result, SensorUpdate)

    def test_update_no_rate_returns_dashes_for_primary(self):
        scope = self._make_resp_scope()
        self.module.plot.latest_rate = None
        result = self.module.update(scope)
        assert result.primary_value == "--"

    def test_update_with_rate_returns_formatted_primary(self):
        scope = self._make_resp_scope()
        with patch.object(self.module.plot, "update_plot", return_value=()):
            self.module.plot.latest_rate = 14.5
            self.module.plot.latest_effort_delta = 0.123
            self.module.plot.window_breath_count = 3
            self.module.plot.rate_window = 30
            result = self.module.update(scope)
        assert "BrPM" in result.primary_value

    def test_update_io_error_returns_error_message(self):
        scope = self._make_resp_scope()
        scope.get_respiratory_samples.side_effect = IOError("no scope")
        result = self.module.update(scope)
        assert "io error" in result.log_message.lower()
        assert result.artists == ()

    def test_update_attribute_error_returns_processing_error(self):
        scope = self._make_resp_scope()
        scope.get_respiratory_samples.side_effect = AttributeError("bad attr")
        result = self.module.update(scope)
        assert "processing error" in result.log_message.lower()
        assert result.artists == ()

    def test_update_value_error_returns_processing_error(self):
        scope = self._make_resp_scope()
        scope.get_respiratory_samples.side_effect = ValueError("bad value")
        result = self.module.update(scope)
        assert "processing error" in result.log_message.lower()

    def test_update_without_get_respiratory_time_axis(self):
        n = 15
        s = np.zeros(n, dtype=np.float32)
        scope = _make_scope()
        scope.get_respiratory_samples.return_value = s
        # Remove the time-axis method so the fallback arange path is exercised
        del scope.get_respiratory_time_axis
        result = self.module.update(scope)
        assert isinstance(result, SensorUpdate)

    def test_shift_history_window_delegates(self):
        with patch.object(self.module.plot, "shift_review_window", return_value=True) as mock:
            result = self.module.shift_history_window(1)
        mock.assert_called_once_with(1)
        assert result is True

    def test_pause_calls_plot_all(self):
        with patch.object(self.module.plot, "plot_all") as mock:
            self.module.pause()
        mock.assert_called_once()

    def test_cleanup_calls_close_plot(self):
        with patch.object(self.module.plot, "_close_plot") as mock:
            self.module.cleanup()
        mock.assert_called_once()

    def test_save_data_produces_xlsx(self, tmp_path, monkeypatch):
        from PlotManager import PlotManager
        monkeypatch.setattr(
            PlotManager,
            "_prepare_export_path",
            lambda self, filename: tmp_path / filename,
        )
        self.module.plot.selected_samples = np.array([])
        self.module.plot.selected_times = np.array([])
        path = self.module.save_data()
        assert path.endswith(".xlsx")
