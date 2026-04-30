"""Tests for src/gui/models.py – SensorUpdate and SensorDefinition dataclasses."""

from __future__ import annotations

import pytest

from gui.models import SensorDefinition, SensorUpdate


class TestSensorUpdate:
    def test_default_values(self):
        update = SensorUpdate()
        assert update.primary_value is None
        assert update.secondary_value is None
        assert update.log_message is None
        assert update.artists == ()

    def test_set_all_fields(self):
        sentinel = object()
        update = SensorUpdate(
            primary_value="98.6",
            secondary_value="72",
            log_message="OK",
            artists=(sentinel,),
        )
        assert update.primary_value == "98.6"
        assert update.secondary_value == "72"
        assert update.log_message == "OK"
        assert update.artists == (sentinel,)

    def test_artists_defaults_to_empty_tuple(self):
        update = SensorUpdate(primary_value="x")
        assert isinstance(update.artists, tuple)
        assert len(update.artists) == 0

    def test_equality(self):
        a = SensorUpdate(primary_value="1", secondary_value="2")
        b = SensorUpdate(primary_value="1", secondary_value="2")
        assert a == b

    def test_inequality(self):
        a = SensorUpdate(primary_value="1")
        b = SensorUpdate(primary_value="2")
        assert a != b

    def test_repr_contains_class_name(self):
        update = SensorUpdate()
        assert "SensorUpdate" in repr(update)


class TestSensorDefinition:
    def _make_factory(self):
        return lambda: None

    def test_all_fields_stored(self):
        factory = self._make_factory()
        defn = SensorDefinition(
            key="ecg",
            title="ECG",
            subtitle="Electrocardiogram",
            primary_label="BPM",
            secondary_label="Avg BPM",
            module_factory=factory,
        )
        assert defn.key == "ecg"
        assert defn.title == "ECG"
        assert defn.subtitle == "Electrocardiogram"
        assert defn.primary_label == "BPM"
        assert defn.secondary_label == "Avg BPM"
        assert defn.module_factory is factory

    def test_module_factory_is_callable(self):
        defn = SensorDefinition(
            key="test",
            title="T",
            subtitle="sub",
            primary_label="p",
            secondary_label="s",
            module_factory=list,
        )
        result = defn.module_factory()
        assert isinstance(result, list)

    def test_equality(self):
        factory = self._make_factory()
        a = SensorDefinition("k", "T", "sub", "p", "s", factory)
        b = SensorDefinition("k", "T", "sub", "p", "s", factory)
        assert a == b

    def test_inequality_different_key(self):
        factory = self._make_factory()
        a = SensorDefinition("k1", "T", "sub", "p", "s", factory)
        b = SensorDefinition("k2", "T", "sub", "p", "s", factory)
        assert a != b
