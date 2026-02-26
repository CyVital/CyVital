"""Reaction-time sensor module for the Tk GUI."""

from __future__ import annotations

import logging
import time
from statistics import mean
from typing import Optional, Tuple

from matplotlib.figure import Figure

from oscilloscope.Scope import Scope
from plots.ReactionPlot import ReactionPlot

try:
    from ..models import SensorUpdate
except ImportError:
    from models import SensorUpdate

from .base import SensorModule

LOGGER = logging.getLogger(__name__)


class ReactionSensorModule(SensorModule):
    # reaction-time workflow within app

    supports_export = True

    def __init__(self) -> None:
        self.plot = ReactionPlot()

    def setup_scope(self, scope: Scope) -> None:
        try:
            scope.setup_device_reaction()
        except (IOError, OSError, AttributeError, NotImplementedError) as exc:
            self.supports_streaming = False
            LOGGER.warning("Reaction scope setup failed; streaming disabled: %s", exc)

    def get_figure(self) -> Optional[Figure]:
        return self.plot.fig

    def shift_history_window(self, direction: int) -> bool:
        return self.plot.shift_review_window(direction)

    def update(self, scope: Scope) -> SensorUpdate:
        try:
            samples = scope.get_reaction_samples()
            t_axis = scope.get_reaction_time_axis(samples)

            artists = self.plot.update_plot(t_axis, samples)
            if artists is None:
                artists_tuple: Tuple[object, ...] = tuple()
            elif isinstance(artists, tuple):
                artists_tuple = artists
            elif isinstance(artists, list):
                artists_tuple = tuple(artists)
            else:
                artists_tuple = (artists,)

            if self.plot.reaction_times:
                latest = self.plot.reaction_times[-1]
                average = mean(self.plot.reaction_times)
                primary = f"{latest:.1f} ms"
                secondary = f"{average:.1f} ms"
                log = (
                    f"Trials recorded: {len(self.plot.reaction_times)} | "
                    f"Average reaction: {average:.1f} ms"
                )
            else:
                primary = "--"
                secondary = "--"
                log = "Waiting for first reaction sample"
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
        file_str = f"reaction_data_{timestamp}.xlsx"
        return self.plot.save_data(file_str)

    def cleanup(self) -> None:
        self.plot._close_plot()

