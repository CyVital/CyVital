"""Shared Tkinter theme constants for the CyVital GUI."""

BASE_FONT_FAMILY = "Segoe UI"
# Brace-wrapped so Tk treats the family name as a single token.
FONT_FAMILY = f"{{{BASE_FONT_FAMILY}}}"

COLORS = {
    "background": "#F5F5F7",
    "sidebar": "#1F1F1F",
    "sidebar_hover": "#2A2A2A",
    "sidebar_active": "#353535",
    "sidebar_text_primary": "#FFFFFF",
    "sidebar_text_secondary": "#9EA3AE",
    "text_primary": "#111111",
    "text_secondary": "#6B6D71",
    "panel": "#FFFFFF",
    "panel_border": "#E3E3E8",
    "panel_gloss": "#FFFFFFCC",
    "accent": "#0071E3",
    "accent_muted": "#4D9FF8",
    "accent_text": "#FFFFFF",
    "status_active": "#34C759",
    "status_inactive": "#8E8E93",
    "tooltip_bg": "#1F1F1F",
    "tooltip_text": "#FFFFFF",
}

FONTS = {
    "brand": (FONT_FAMILY, 20, "bold"),
    "brand_sub": (FONT_FAMILY, 10),
    "nav_title": (FONT_FAMILY, 12, "bold"),
    "nav_sub": (FONT_FAMILY, 10),
    "header": (FONT_FAMILY, 24, "bold"),
    "subheader": (FONT_FAMILY, 12),
    "body": (FONT_FAMILY, 11),
    "body_bold": (FONT_FAMILY, 11, "bold"),
    "metric_value": (FONT_FAMILY, 28, "bold"),
    "metric_label": (FONT_FAMILY, 10),
    "button": (FONT_FAMILY, 11, "bold"),
}

