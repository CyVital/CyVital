"""Pulse oximeter sensor module for the Tk GUI."""

from __future__ import annotations

import logging
import time
from typing import Optional

from matplotlib.figure import Figure

from oscilloscope.Scope import Scope
from plots.PulseOxPlot import PulseOxPlot

try:
    from ..models import SensorUpdate
except ImportError:
    from models import SensorUpdate

from .base import SensorModule
from .helpers import normalize_artists

LOGGER = logging.getLogger(__name__)


class PulseOxSensorModule(SensorModule):
    supports_export = True

    def __init__(self) -> None:
        self.plot = PulseOxPlot()

    def setup_scope(self, scope: Scope) -> None:
        try:
            scope.setup_device_pulse_ox()
        except (IOError, OSError, AttributeError, NotImplementedError) as exc:
            self.supports_streaming = False
            LOGGER.warning("Pulse ox scope setup failed; streaming disabled: %s", exc)

    def get_figure(self) -> Optional[Figure]:
        return self.plot.fig

    def shift_history_window(self, direction: int) -> bool:
        return self.plot.shift_review_window(direction)

    def update(self, scope: Scope) -> SensorUpdate:
        try:
            samples = scope.get_pulse_ox_samples()
            t_axis = scope.get_pulse_ox_time_axis()
            artists_tuple = normalize_artists(self.plot.update_plot(t_axis, samples))

            if self.plot.bpm and self.plot.spo2:
                primary = f"{self.plot.spo2:.1f} %"
                secondary = f"{self.plot.bpm:.0f} bpm"
                log = "bpm and spo2"
            else:
                primary = "--"
                secondary = "--"
                log = "Waiting for first pulse ox sample"
        except IOError:
            primary = "--"
            secondary = "--"
            log = "IO Error: Cannot read scope"
            artists_tuple = tuple()

        return SensorUpdate(
            primary_value=primary,
            secondary_value=secondary,
            log_message=log,
            artists=artists_tuple,
        )

    def pause(self) -> None:
        self.plot.plot_all()

    def save_data(self) -> Optional[str]:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        return self.plot.save_data(f"pulse_ox_data_{timestamp}.xlsx")

    def cleanup(self) -> None:
        self.plot._close_plot()

