# CyVital UI Polish Overview

This document summarizes the UX polish work added during the “Microinteractions & Polish” effort. It outlines the intent behind each change, the important implementation points, and how to see the behavior in action when running the Tkinter client.

## 1. Loading animation before graphs render

- **Why:** Live plots previously revealed blank canvas widgets until the first dataset arrived. A lightweight overlay now communicates that data streaming is initializing.
- **Where:** `CyVitalApp._render_sensor_content`, `_show_loading_overlay`, `_animate_loading_label`, `_hide_loading_overlay`.
- **How it works:** When a module exposes a Matplotlib figure, the app places a centered overlay (`tk.Frame`) on `plot_frame`. Animated ellipses (“Loading data…”) are driven by a repeating `after` callback until `_apply_sensor_update` confirms data arrival.
- **Edge cases handled:** The overlay is removed when switching sensors, pausing/unavailable sensors, or during clean shutdown to avoid orphaned windows.

## 2. Animated metric transitions

- **Why:** Instant jumps on the “Latest/Average Reaction” cards made it hard to follow deltas between samples.
- **Where:** `_animate_metric_change`, `_extract_numeric_parts`, `_format_numeric_text`, `NumericTextParts`.
- **How it works:** Each metric value string is parsed for numeric content. When a new reading arrives, the code interpolates from the previous numeric value to the new one over 450 ms using a cubic ease-out curve. If labels contain additional text (units, prefixes), that text is preserved.
- **Fallbacks:** Non-numeric payloads skip animation and simply set the string variable. Outstanding animation callbacks are canceled when replacing sensor modules or when new values arrive quickly.

## 3. Sidebar hover & tooltips

- **Why:** Navigation previously only reacted when a sensor was active. Hover cues and contextual text improve discoverability.
- **Where:** `COLORS["sidebar_hover"]`, `HoverTooltip`, `NavItem`.
- **Behavior additions:**
  - Hovering a nav item fades the background to `sidebar_hover`, changes the indicator bar to a subtle outline, and shows a “hand” cursor.
  - After 200 ms, a tooltip appears to the right of the sidebar with the module subtitle. Moving away cancels the tooltip and restores the base styling.
- **Implementation details:** `HoverTooltip` manages debounced `after` callbacks and cleans up its `Toplevel` window. `NavItem` tracks `is_active` + `is_hovered` so hover color does not override the active highlight.

## 4. Auto-save / last-updated indicator

- **Why:** Users wanted confirmation that data is still streaming and safe to export. A relative timestamp now lives beneath the log text.
- **Where:** `self.last_updated_var`, `_reset_last_update_tracking`, `_mark_last_update`, `_refresh_last_updated_label`, `_build_footer_controls`.
- **How it works:** Every time `_apply_sensor_update` receives new copy or values, `_mark_last_update` records the timestamp and starts a once-per-second updater that renders messages such as “Last updated 5s ago.” Switching sensors or losing the stream resets the label to “--”.

## 5. Miscellaneous supporting tweaks

- Added `sidebar_hover`, `tooltip_bg`, and `tooltip_text` in `COLORS`.
- Populated `HoverTooltip` for reuse if future components need the same behavior.
- Ensured loading/animation state resets happen when stopping animations or closing the app (`shutdown`).
- Added a convenience note to run the GUI with a fake oscilloscope: `python src/gui/tkGui.py --fake-scope [--fake-seed 42]`.

## Verifying the experience

1. Launch the GUI with the fake scope to avoid hardware dependencies:
   ```bash
   python src/gui/tkGui.py --fake-scope
   ```
2. Switch between sensors to see the loading overlay and tooltip interactions.
3. Observe the top metric cards after each synthetic reaction trial to watch the eased transitions.
4. Confirm the footer shows “Last updated just now” and ticks up while the stream runs; it resets when switching modules or pausing.

