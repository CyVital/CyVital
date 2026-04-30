"""Tests for src/gui/sensors/base.py, message.py, and registry.py."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from gui.sensors.base import SensorModule
from gui.sensors.message import MessageSensorModule
from gui.sensors.registry import DEFAULT_SENSORS
from gui.models import SensorUpdate, SensorDefinition


class TestSensorModuleBase:
    def setup_method(self):
        self.module = SensorModule()

    def test_supports_streaming_default_true(self):
        assert self.module.supports_streaming is True

    def test_supports_export_default_false(self):
        assert self.module.supports_export is False

    def test_get_figure_returns_none(self):
        assert self.module.get_figure() is None

    def test_setup_scope_does_not_raise(self):
        scope = MagicMock()
        self.module.setup_scope(scope)  # Should be a no-op

    def test_get_placeholder_message_returns_none(self):
        assert self.module.get_placeholder_message() is None

    def test_update_returns_sensor_update(self):
        scope = MagicMock()
        result = self.module.update(scope)
        assert isinstance(result, SensorUpdate)

    def test_update_returns_empty_sensor_update(self):
        scope = MagicMock()
        result = self.module.update(scope)
        assert result.primary_value is None
        assert result.secondary_value is None
        assert result.log_message is None
        assert result.artists == ()

    def test_save_data_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            self.module.save_data()

    def test_cleanup_does_not_raise(self):
        self.module.cleanup()  # Should be a no-op


class TestMessageSensorModule:
    def test_supports_streaming_is_false(self):
        module = MessageSensorModule("hello")
        assert module.supports_streaming is False

    def test_get_placeholder_message_returns_message(self):
        module = MessageSensorModule("Device not found")
        assert module.get_placeholder_message() == "Device not found"

    def test_empty_string_message(self):
        module = MessageSensorModule("")
        assert module.get_placeholder_message() == ""

    def test_message_stored(self):
        module = MessageSensorModule("test msg")
        assert module.message == "test msg"


class TestDefaultSensors:
    def test_default_sensors_is_list(self):
        assert isinstance(DEFAULT_SENSORS, list)

    def test_correct_count(self):
        assert len(DEFAULT_SENSORS) == 6

    def test_all_are_sensor_definitions(self):
        for sensor in DEFAULT_SENSORS:
            assert isinstance(sensor, SensorDefinition)

    def test_all_have_non_empty_key(self):
        for sensor in DEFAULT_SENSORS:
            assert sensor.key and isinstance(sensor.key, str)

    def test_all_have_non_empty_title(self):
        for sensor in DEFAULT_SENSORS:
            assert sensor.title and isinstance(sensor.title, str)

    def test_all_module_factories_are_callable(self):
        for sensor in DEFAULT_SENSORS:
            assert callable(sensor.module_factory)

    def test_keys_are_unique(self):
        keys = [s.key for s in DEFAULT_SENSORS]
        assert len(keys) == len(set(keys))

    def test_expected_keys_present(self):
        keys = {s.key for s in DEFAULT_SENSORS}
        expected = {"reaction", "ecg", "emg", "pulse", "pressure", "resp"}
        assert keys == expected

    def test_reaction_sensor_definition(self):
        reaction = next(s for s in DEFAULT_SENSORS if s.key == "reaction")
        assert reaction.title == "Reaction Time"
        assert reaction.primary_label == "Latest Reaction"
        assert reaction.secondary_label == "Average Reaction"

    def test_ecg_sensor_definition(self):
        ecg = next(s for s in DEFAULT_SENSORS if s.key == "ecg")
        assert ecg.title == "ECG"
        assert ecg.subtitle == "Electrocardiogram"
