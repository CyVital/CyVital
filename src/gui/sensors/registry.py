"""Default sensor registry for the Tk GUI."""

from __future__ import annotations

try:
    from ..models import SensorDefinition
except ImportError:
    from models import SensorDefinition

from .blood_pressure import BloodPressureSensorModule
from .ecg import ECGSensorModule
from .emg import EMGSensorModule
from .pulse_ox import PulseOxSensorModule
from .reaction import ReactionSensorModule
from .respiratory import RespiratorySensorModule


DEFAULT_SENSORS = [
    SensorDefinition(
        key="reaction",
        title="Reaction Time",
        subtitle="Response Test",
        primary_label="Latest Reaction",
        secondary_label="Average Reaction",
        module_factory=ReactionSensorModule,
    ),
    SensorDefinition(
        key="ecg",
        title="ECG",
        subtitle="Electrocardiogram",
        primary_label="Primary Reading",
        secondary_label="Secondary Reading",
        module_factory=ECGSensorModule,
    ),
    SensorDefinition(
        key="emg",
        title="EMG",
        subtitle="Electromyography",
        primary_label="Primary Reading",
        secondary_label="Secondary Reading",
        module_factory=EMGSensorModule,
    ),
    SensorDefinition(
        key="pulse",
        title="Pulse Oximeter",
        subtitle="Blood Oxygen",
        primary_label="SpOâ‚‚",
        secondary_label="Pulse",
        module_factory=PulseOxSensorModule,
    ),
    SensorDefinition(
        key="pressure",
        title="Blood Pressure",
        subtitle="blood pressure",
        primary_label="Primary Reading",
        secondary_label="Secondary Reading",
        module_factory=BloodPressureSensorModule,
    ),
    SensorDefinition(
        key="resp",
        title="Respiratory Effort",
        subtitle="Thoracic Belt",
        primary_label="Respirations/min",
        secondary_label="Effort Range",
        module_factory=RespiratorySensorModule,
    ),
]

