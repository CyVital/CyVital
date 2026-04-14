"""Shared helpers for GUI sensor modules."""

from __future__ import annotations

from typing import Tuple


def normalize_artists(artists: object) -> Tuple[object, ...]:
    if artists is None:
        return tuple()
    if isinstance(artists, tuple):
        return artists
    if isinstance(artists, list):
        return tuple(artists)
    return (artists,)

