"""ECG sensor module for the Tk GUI."""

from __future__ import annotations

import logging
import time
from typing import Optional

from matplotlib.figure import Figure

from oscilloscope.Scope import Scope
from plots.ECGPlot import ECGPlot

try:
    from ..models import SensorUpdate
except ImportError:
    from models import SensorUpdate

from .base import SensorModule
from .helpers import normalize_artists

LOGGER = logging.getLogger(__name__)


class ECGSensorModule(SensorModule):
    supports_export = True

    def __init__(self) -> None:
        self.plot = ECGPlot()

    def setup_scope(self, scope: Scope) -> None:
        try:
            scope.setup_device_ecg()
        except (IOError, OSError, AttributeError, NotImplementedError) as exc:
            self.supports_streaming = False
            LOGGER.warning("ECG scope setup failed; streaming disabled: %s", exc)

    def get_figure(self) -> Optional[Figure]:
        return self.plot.fig

    def shift_history_window(self, direction: int) -> bool:
        return self.plot.shift_review_window(direction)

    def update(self, scope: Scope) -> SensorUpdate:
        try:
            samples = scope.get_ecg_samples()
            t_axis = scope.get_ecg_time_axis(samples)
            artists_tuple = normalize_artists(self.plot.update_plot(t_axis, samples))

            latest = self.plot.latest_bpm
            average = self.plot.avg_bpm
            if latest is not None:
                primary = f"{latest:.1f} BPM"
                secondary_value = average if average is not None else latest
                secondary = f"{secondary_value:.1f} BPM"
                elapsed = self.plot.time_values[-1] if self.plot.time_values else 0.0
                log = (
                    f"Elapsed time: {elapsed:.1f}s | Peaks in {self.plot.window_duration:.0f}s window: "
                    f"{len(self.plot.recent_peak_times)}"
                )
            else:
                primary = "--"
                secondary = "--"
                log = "Detecting ECG peaks..."
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

    def save_data(self) -> Optional[str]:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        return self.plot.save_data(f"ecg_data_{timestamp}.xlsx")

    def pause(self) -> None:
        self.plot.plot_all()

    def cleanup(self) -> None:
        self.plot._close_plot()

