"""Tests for GUI sensor adapter modules."""

from __future__ import annotations

import pytest

from gui.models import SensorDefinition, SensorUpdate
from gui.sensors.base import SensorModule
from gui.sensors.helpers import normalize_artists
from gui.sensors.message import MessageSensorModule
from gui.sensors.registry import DEFAULT_SENSORS
from gui.sensors import blood_pressure, ecg, emg, pulse_ox, reaction, respiratory


#pretend matplotlib figure
class DummyFigure:
    pass


class BasePlot:
    def __init__(self, *args, **kwargs):
        self.fig = DummyFigure()
        self.updated_with = None
        self.closed = False
        self.paused = False
        self.saved_filename = None

    def update_plot(self, t_axis, samples):
        self.updated_with = (t_axis, samples)
        return ["artist"]

    #demonstrates a user clicking left/right navigation
    def shift_review_window(self, direction):
        self.shifted = direction
        return direction != 0
    
    #if the plot is paused and data needs to be ready for staorage/export
    def plot_all(self):
        self.paused = True

    #if export has gone through
    def save_data(self, filename):
        self.saved_filename = filename
        return filename

    def _close_plot(self):
        self.closed = True


class ECGPlotFake(BasePlot):
    latest_bpm = 72.0
    avg_bpm = 70.5
    time_values = [1.5]
    window_duration = 10
    recent_peak_times = [0.1, 0.8]


class PulseOxPlotFake(BasePlot):
    bpm = 64
    spo2 = 98.2


class ReactionPlotFake(BasePlot):
    def __init__(self, cue_output=None):
        super().__init__()
        self.cue_output = cue_output
        self.reaction_times = [210.0, 190.0]


class RespiratoryPlotFake(BasePlot):
    latest_rate = 14.2
    latest_effort_delta = 0.34
    window_breath_count = 7
    rate_window = 60
    sample_rate = 50



# FAKE HARDWARE
#simple call and responses that emulate our hardware - also give failure flags

class ScopeStub:
    def __init__(self, fail_setup=False, fail_read=False):
        self.fail_setup = fail_setup
        self.fail_read = fail_read
        self.led_state = None

    def _maybe_fail_setup(self):
        if self.fail_setup:
            raise OSError("setup failed")

    def _maybe_fail_read(self):
        if self.fail_read:
            raise IOError("read failed")

    def setup_device_ecg(self):
        self._maybe_fail_setup()

    def setup_device_emg(self):
        self._maybe_fail_setup()

    def setup_device_pulse_ox(self):
        self._maybe_fail_setup()

    def setup_device_blood_pressure(self):
        self._maybe_fail_setup()

    def setup_device_reaction(self):
        self._maybe_fail_setup()

    def setup_device_respiratory(self):
        self._maybe_fail_setup()

    def set_reaction_led(self, active):
        self.led_state = active

    def get_ecg_samples(self):
        self._maybe_fail_read()
        return [0.1, 0.2]

    def get_ecg_time_axis(self, samples):
        return [0.0, 0.1]

    def get_emg_samples(self):
        self._maybe_fail_read()
        return [0.1, 0.2]

    def get_emg_time_axis(self, samples):
        return [0.0, 0.1]

    def get_pulse_ox_samples(self):
        self._maybe_fail_read()
        return [1, 2, 3, 4, 5, 6]

    def get_pulse_ox_time_axis(self):
        return [0.0]

    def get_blood_pressure_samples(self):
        self._maybe_fail_read()
        return [0.1, 0.2]

    def get_blood_pressure_time_axis(self, samples):
        return [0.0, 0.1]

    def get_reaction_samples(self):
        self._maybe_fail_read()
        return [0.1, 0.2]

    def get_reaction_time_axis(self, samples):
        return [0.0, 0.1]

    def get_respiratory_samples(self):
        self._maybe_fail_read()
        return [0.1, 0.2]

    def get_respiratory_time_axis(self, samples):
        return [0.0, 0.1]


#blank update to data satarts empty
def test_sensor_update_defaults():
    update = SensorUpdate()
    assert update.primary_value is None
    assert update.secondary_value is None
    assert update.log_message is None
    assert update.artists == ()


def test_sensor_definition_holds_factory():
    definition = SensorDefinition("key", "Title", "Sub", "A", "B", SensorModule)
    assert definition.module_factory is SensorModule


#empty data should not be able to be exported
def test_base_sensor_defaults_and_export_error():
    module = SensorModule()
    assert module.get_figure() is None
    assert module.get_placeholder_message() is None
    assert module.update(ScopeStub()).artists == ()
    assert module.shift_history_window(1) is False
    assert module.pause() is None
    assert module.cleanup() is None
    with pytest.raises(NotImplementedError):
        module.save_data()


def test_message_sensor_returns_placeholder_message():
    module = MessageSensorModule("No device")
    assert module.supports_streaming is False
    assert module.get_placeholder_message() == "No device"


@pytest.mark.parametrize(
    ("artists", "expected"),
    [
        (None, ()),
        (("a", "b"), ("a", "b")),
        (["a", "b"], ("a", "b")),
        ("a", ("a",)),
    ],
)
def test_normalize_artists(artists, expected):
    assert normalize_artists(artists) == expected


def test_registry_contains_unique_sensor_keys():
    keys = [definition.key for definition in DEFAULT_SENSORS]
    assert len(keys) == len(set(keys))
    assert {definition.key for definition in DEFAULT_SENSORS} == {
        "reaction",
        "ecg",
        "emg",
        "pulse",
        "pressure",
        "resp",
    }


@pytest.mark.parametrize(
    ("module_obj", "plot_attr", "plot_cls", "module_cls", "setup_name", "primary"),
    [
        (ecg, "ECGPlot", ECGPlotFake, ecg.ECGSensorModule, "setup_device_ecg", "72.0 BPM"),
        (emg, "EMGPlot", BasePlot, emg.EMGSensorModule, "setup_device_emg", "--"),
        (
            pulse_ox,
            "PulseOxPlot",
            PulseOxPlotFake,
            pulse_ox.PulseOxSensorModule,
            "setup_device_pulse_ox",
            "98.2 %",
        ),
        (
            blood_pressure,
            "BloodPressurePlot",
            BasePlot,
            blood_pressure.BloodPressureSensorModule,
            "setup_device_blood_pressure",
            "--",
        ),
    ],
)
def test_streaming_sensor_success_paths(
    monkeypatch, #for our "fake plot class"
    module_obj,
    plot_attr,
    plot_cls,
    module_cls,
    setup_name,
    primary,
):
    monkeypatch.setattr(module_obj, plot_attr, plot_cls)
    sensor = module_cls()
    scope = ScopeStub()

    sensor.setup_scope(scope)
    update = sensor.update(scope)

    assert update.primary_value == primary
    assert update.artists == ("artist",)
    assert sensor.get_figure().__class__ is DummyFigure
    assert sensor.shift_history_window(1) is True
    sensor.pause()
    assert sensor.plot.paused is True
    assert sensor.save_data().endswith(".xlsx")
    sensor.cleanup()
    assert sensor.plot.closed is True
    assert hasattr(scope, setup_name)


#Easily run same tests multiple times with different parameters
@pytest.mark.parametrize(
    ("module_obj", "plot_attr", "plot_cls", "module_cls", "setup_method"),
    [
        (ecg, "ECGPlot", ECGPlotFake, ecg.ECGSensorModule, "setup_scope"),
        (emg, "EMGPlot", BasePlot, emg.EMGSensorModule, "setup_scope"),
        (pulse_ox, "PulseOxPlot", PulseOxPlotFake, pulse_ox.PulseOxSensorModule, "setup_scope"),
        (
            blood_pressure,
            "BloodPressurePlot",
            BasePlot,
            blood_pressure.BloodPressureSensorModule,
            "setup_scope",
        ),
        (reaction, "ReactionPlot", ReactionPlotFake, reaction.ReactionSensorModule, "setup_scope"),
    ],
)






#COMMUNICATION TESTS - the main tests here

# 1. Replace the real plot with a fake plot.
# 2. Create the sensor module.
# 3. Create fake hardware.
# 4. Run hardware setup.
# 5. Run one sensor update frame.


def test_setup_failure_disables_streaming(
    monkeypatch,
    module_obj,
    plot_attr,
    plot_cls,
    module_cls,
    setup_method,
):
    monkeypatch.setattr(module_obj, plot_attr, plot_cls)
    sensor = module_cls()
    getattr(sensor, setup_method)(ScopeStub(fail_setup=True))
    assert sensor.supports_streaming is False


#explination per test
def test_reaction_sensor_led_update_and_cleanup(monkeypatch):
    # 1. Replace the real plot with a fake plot.
    monkeypatch.setattr(reaction, "ReactionPlot", ReactionPlotFake)
    
    # 2. Create the sensor module.
    # 3. Create fake hardware.
    sensor = reaction.ReactionSensorModule()
    scope = ScopeStub()

    # 4. Run hardware setup.
    sensor.setup_scope(scope)
    sensor._set_external_led(True)
    # 5. Run one sensor update frame.
    update = sensor.update(scope)


    #6. Test results
    assert scope.led_state is True
    assert update.primary_value == "190.0 ms"
    assert update.secondary_value == "200.0 ms"
    assert "Trials recorded: 2" in update.log_message
    sensor.cleanup()
    assert scope.led_state is False


def test_reaction_sensor_io_error(monkeypatch):
    monkeypatch.setattr(reaction, "ReactionPlot", ReactionPlotFake)
    sensor = reaction.ReactionSensorModule()

    update = sensor.update(ScopeStub(fail_read=True))

    assert update.primary_value == "--"
    assert update.secondary_value == "--"
    assert update.log_message == "IO Error: Cannot read scope"
    assert update.artists == ()


def test_respiratory_sensor_configures_lazily_and_updates(monkeypatch):
    monkeypatch.setattr(respiratory, "RespiratoryPlot", RespiratoryPlotFake)
    sensor = respiratory.RespiratorySensorModule()

    update = sensor.update(ScopeStub())

    assert sensor._configured is True
    assert update.primary_value == "14.2 BrPM"
    assert update.secondary_value == "0.340 V delta"
    assert update.artists == ("artist",)


def test_respiratory_sensor_io_error(monkeypatch):
    monkeypatch.setattr(respiratory, "RespiratoryPlot", RespiratoryPlotFake)
    sensor = respiratory.RespiratorySensorModule()

    update = sensor.update(ScopeStub(fail_read=True))

    assert update.primary_value == "--"
    assert update.secondary_value == "--"
    assert update.log_message == "IO error: respiratory stream unavailable"
    assert update.artists == ()
