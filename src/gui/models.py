"""UI-facing dataclasses shared across the Tk GUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Tuple


@dataclass
class SensorUpdate:
    # Normalized payload returned each animation frame by a sensor module.
    primary_value: Optional[str] = None
    secondary_value: Optional[str] = None
    log_message: Optional[str] = None
    artists: Tuple[object, ...] = ()


@dataclass
class SensorDefinition:
    # How sensors appear in the UI and how to instantiate them.
    key: str
    title: str
    subtitle: str
    primary_label: str
    secondary_label: str
    module_factory: Callable[[], SensorModule]

