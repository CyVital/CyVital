"""Tests for src/gui/theme.py – colour and font constants."""

from __future__ import annotations

import pytest

from gui.theme import BASE_FONT_FAMILY, COLORS, FONT_FAMILY, FONTS


class TestColors:
    _REQUIRED_KEYS = [
        "background",
        "sidebar",
        "sidebar_hover",
        "sidebar_active",
        "sidebar_text_primary",
        "sidebar_text_secondary",
        "text_primary",
        "text_secondary",
        "panel",
        "panel_border",
        "panel_gloss",
        "accent",
        "accent_muted",
        "accent_text",
        "status_active",
        "status_inactive",
        "tooltip_bg",
        "tooltip_text",
    ]

    def test_all_required_keys_present(self):
        for key in self._REQUIRED_KEYS:
            assert key in COLORS, f"Missing colour key: {key}"

    def test_values_are_strings(self):
        for key, value in COLORS.items():
            assert isinstance(value, str), f"COLORS[{key!r}] is not a string"

    def test_hex_colour_format(self):
        """All colours should start with '#' (hex) or be non-empty strings."""
        for key, value in COLORS.items():
            assert value.startswith("#"), f"COLORS[{key!r}] = {value!r} doesn't start with '#'"

    def test_background_colour(self):
        assert COLORS["background"] == "#F5F5F7"

    def test_accent_colour(self):
        assert COLORS["accent"] == "#0071E3"

    def test_status_active_colour(self):
        assert COLORS["status_active"] == "#34C759"


class TestFonts:
    _REQUIRED_KEYS = [
        "brand",
        "brand_sub",
        "nav_title",
        "nav_sub",
        "header",
        "subheader",
        "body",
        "body_bold",
        "metric_value",
        "metric_label",
        "button",
    ]

    def test_all_required_keys_present(self):
        for key in self._REQUIRED_KEYS:
            assert key in FONTS, f"Missing font key: {key}"

    def test_values_are_tuples(self):
        for key, value in FONTS.items():
            assert isinstance(value, tuple), f"FONTS[{key!r}] is not a tuple"

    def test_tuples_have_at_least_two_elements(self):
        for key, value in FONTS.items():
            assert len(value) >= 2, f"FONTS[{key!r}] tuple has fewer than 2 elements"

    def test_second_element_is_int_size(self):
        for key, value in FONTS.items():
            assert isinstance(value[1], int), f"FONTS[{key!r}] size is not an int"

    def test_metric_value_is_large(self):
        assert FONTS["metric_value"][1] >= 20

    def test_brand_is_bold(self):
        assert "bold" in FONTS["brand"]


class TestFontFamily:
    def test_base_font_family_non_empty(self):
        assert BASE_FONT_FAMILY and isinstance(BASE_FONT_FAMILY, str)

    def test_font_family_wraps_base(self):
        assert BASE_FONT_FAMILY in FONT_FAMILY

    def test_font_family_has_curly_brackets(self):
        assert FONT_FAMILY.startswith("{")
        assert FONT_FAMILY.endswith("}")
