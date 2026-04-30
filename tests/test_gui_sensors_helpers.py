"""Tests for src/gui/sensors/helpers.py – normalize_artists."""

from __future__ import annotations

import pytest

from gui.sensors.helpers import normalize_artists


class TestNormalizeArtists:
    def test_none_returns_empty_tuple(self):
        assert normalize_artists(None) == ()

    def test_empty_tuple_returns_empty_tuple(self):
        assert normalize_artists(()) == ()

    def test_non_empty_tuple_returned_unchanged(self):
        sentinel = object()
        result = normalize_artists((sentinel,))
        assert result == (sentinel,)

    def test_list_converted_to_tuple(self):
        a, b = object(), object()
        result = normalize_artists([a, b])
        assert result == (a, b)
        assert isinstance(result, tuple)

    def test_empty_list_returns_empty_tuple(self):
        result = normalize_artists([])
        assert result == ()
        assert isinstance(result, tuple)

    def test_single_non_container_wrapped_in_tuple(self):
        sentinel = object()
        result = normalize_artists(sentinel)
        assert result == (sentinel,)

    def test_string_wrapped_as_single_element(self):
        # A string is not a tuple or list, so it should be wrapped.
        result = normalize_artists("artist")
        assert result == ("artist",)

    def test_integer_wrapped_as_single_element(self):
        result = normalize_artists(42)
        assert result == (42,)
