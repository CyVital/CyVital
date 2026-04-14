"""Respiratory effort sensor module for the Tk GUI."""

from __future__ import annotations

import logging
import time
from typing import Optional

import numpy as np
from matplotlib.figure import Figure

from oscilloscope.Scope import Scope
from plots.RespiratoryPlot import RespiratoryPlot

try:
    from ..models import SensorUpdate
except ImportError:
    from models import SensorUpdate

from .base import SensorModule
from .helpers import normalize_artists

LOGGER = logging.getLogger(__name__)


class RespiratorySensorModule(SensorModule):
    """Streams respiratory effort data and surfaces respiration metrics."""

    supports_export = True

    def __init__(self) -> None:
        self.plot = RespiratoryPlot()
        self._configured = False

    def get_figure(self) -> Optional[Figure]:
        return self.plot.fig

    def shift_history_window(self, direction: int) -> bool:
        return self.plot.shift_review_window(direction)

    def update(self, scope: Scope) -> SensorUpdate:
        if not self._configured:
            setup_fn = getattr(scope, "setup_device_respiratory", None)
            if callable(setup_fn):
                setup_fn()
            self._configured = True

        try:
            samples = scope.get_respiratory_samples()
            if hasattr(scope, "get_respiratory_time_axis"):
                t_axis = scope.get_respiratory_time_axis(samples)
            else:
                sample_rate = getattr(self.plot, "sample_rate", 1) or 1
                t_axis = np.arange(len(samples)) / sample_rate

            artists_tuple = normalize_artists(self.plot.update_plot(t_axis, samples))

            latest_rate = self.plot.latest_rate
            effort_delta = self.plot.latest_effort_delta
            window_count = self.plot.window_breath_count
            rate_window = self.plot.rate_window

            if latest_rate is not None:
                primary = f"{latest_rate:.1f} BrPM"
                secondary = f"{(effort_delta or 0.0):.3f} V Î”"
                log = f"Breaths detected in last {rate_window}s: {window_count}"
            else:
                primary = "--"
                secondary = "--" if effort_delta is None else f"{effort_delta:.3f} V Î”"
                log = "Tracking respiratory baseline..."
        except (IOError, OSError) as exc:
            primary = "--"
            secondary = "--"
            log = "IO error: respiratory stream unavailable"
            artists_tuple = tuple()
            LOGGER.warning("Respiratory scope read failed: %s", exc)
        except (AttributeError, ValueError, TypeError) as exc:
            primary = "--"
            secondary = "--"
            log = "Respiratory processing error (see logs)"
            artists_tuple = tuple()
            LOGGER.exception("Respiratory data processing failed: %s", exc)

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
        return self.plot.save_data(f"resp_data_{timestamp}.xlsx")

    def cleanup(self) -> None:
        self.plot._close_plot()

