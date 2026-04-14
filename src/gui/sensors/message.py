"""Message-only placeholder sensor module for the Tk GUI."""

from __future__ import annotations

from typing import Optional

from .base import SensorModule


class MessageSensorModule(SensorModule):
    supports_streaming = False

    def __init__(self, message: str) -> None:
        self.message = message

    def get_placeholder_message(self) -> Optional[str]:
        return self.message

