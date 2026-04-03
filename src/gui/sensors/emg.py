"""EMG sensor module for the Tk GUI."""

from __future__ import annotations

import logging
import time
from typing import Optional

from matplotlib.figure import Figure

from oscilloscope.Scope import Scope
from plots.EMGPlot import EMGPlot

try:
    from ..models import SensorUpdate
except ImportError:
    from models import SensorUpdate

from .base import SensorModule
from .helpers import normalize_artists

LOGGER = logging.getLogger(__name__)


class EMGSensorModule(SensorModule):
    supports_export = True

    def __init__(self) -> None:
        self.plot = EMGPlot()

    def get_figure(self) -> Optional[Figure]:
        return self.plot.fig

    def setup_scope(self, scope: Scope) -> None:
        try:
            scope.setup_device_emg()
        except (IOError, OSError, AttributeError, NotImplementedError) as exc:
            self.supports_streaming = False
            LOGGER.warning("EMG scope setup failed; streaming disabled: %s", exc)

    def shift_history_window(self, direction: int) -> bool:
        return self.plot.shift_review_window(direction)

    def update(self, scope: Scope) -> SensorUpdate:
        try:
            samples = scope.get_emg_samples()
            t_axis = scope.get_emg_time_axis(samples)
            artists_tuple = normalize_artists(self.plot.update_plot(t_axis, samples))
            msg = ""
        except IOError:
            msg = "IO Error: Cannot read scope"
            artists_tuple = tuple()

        return SensorUpdate(
            primary_value="--",
            secondary_value="--",
            log_message=msg,
            artists=artists_tuple,
        )

    def pause(self) -> None:
        self.plot.plot_all()

    def save_data(self) -> Optional[str]:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        return self.plot.save_data(f"emg_data_{timestamp}.xlsx")

    def cleanup(self) -> None:
        self.plot._close_plot()

