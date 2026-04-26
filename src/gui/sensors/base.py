"""Base sensor interface for GUI sensor modules."""

from __future__ import annotations

from typing import Optional

from matplotlib.figure import Figure

from oscilloscope.Scope import Scope

try:
    from ..models import SensorUpdate
except ImportError:
    from models import SensorUpdate


class SensorModule:
    # sensor integrations

    supports_streaming: bool = True
    supports_export: bool = False

    def get_figure(self) -> Optional[Figure]:
        # Return a Matplotlib figure to embed in graph
        return None

    def setup_scope(self, scope: Scope) -> None:
        pass

    def get_placeholder_message(self) -> Optional[str]:
        # Return a message when no data is available
        return None

    def update(self, scope: Scope) -> SensorUpdate:
        # Fetch new data and describe what should output
        return SensorUpdate()

    def shift_history_window(self, direction: int) -> bool:
        # Move through stored plot history when a sensor supports review.
        return False

    def pause(self) -> None:
        # Let sensors render a paused/full-history view if they support one.
        pass

    def save_data(self) -> Optional[str]:
        # Send collected data when export button is pressed
        raise NotImplementedError("Export not implemented for this module.")

    def cleanup(self) -> None:
        # Release resources
        pass

