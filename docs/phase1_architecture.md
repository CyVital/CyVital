# CyVital GUI Modernization – Phase 1 Notes

## 1. Current GUI Snapshot
- Entry point: `src/gui/tkGui.py` creates a plain `tk.Tk` window, embeds a single Matplotlib figure via `FigureCanvasTkAgg`, and wires a `FuncAnimation` loop to continually update the reaction-time plot.
- Data pipeline: Uses `Scope` from `src/oscilloscope/Scope.py` directly inside the GUI thread. Sampling configuration and hardware lifecycle (open/reset/close) live in that module.
- Plotting logic: Handled entirely by `ReactionPlot` in `src/plots/ReactionPlot.py`; manages figure creation, cues, selection rectangles, and export-to-Excel.
- UI controls: Two `tk.Button` widgets (“Stop”, “Save”) stacked under the plot. No navigation controls, no separation of concerns between modalities.
- Styling: Default Tk widgets with minimal theming. The Matplotlib figure is styled for dark backgrounds, which we want to retain.

## 2. Target Template Highlights
- Left rail navigation showing modalities (ECG, EMG, Pulse Oximeter, Reaction Time) with iconography and accent colors.
- Main content area framed with panels: header (title + subtitle), key readings (primary/secondary metrics), large plot container, footer actions (live status, export buttons).
- Dark theme with red/yellow accents, drop shadows, rounded panels; typography hierarchy (title, section labels, metric values).

## 3. Bridging Current → Template
| Template Element | Current State | Required Adjustments |
| --- | --- | --- |
| Navigation rail | None | Introduce a `ttk.Frame` or custom canvas-based sidebar; maintain existing color palette (deep reds/yellows). |
| Multi-modality tabs | Single Reaction view | Architect notebook/panel system so each modality can mount its own plot + metrics; Reaction logic becomes one panel. |
| Header metrics | None | Abstract data summaries (BPM, mV, etc.) into reusable metric cards; placeholders until modality logic is implemented. |
| Plot container | Matplotlib figure already styled | Wrap figure inside modern frame with padding, consistent with template; reuse dark background. |
| Footer controls | Stop/Save buttons | Provide toolbar/footer for Start/Stop/Export actions while preserving current behaviors (stop animation, export selection). |

## 4. Architectural Direction
- **App shell**: Move toward `CyVitalApp(tk.Tk)` responsible for window, layout, theming.
- **Panels**: Create reusable `PlotPanel` base; specific modalities extend this. Reaction panel migrates `ReactionPlot` logic.
- **Data abstraction**: Introduce `DataSource` interface wrapping `Scope`. Allows fallback simulation, reduced latency, cleaner code.
- **Styling**: Define centralized color constants (matching current dark/red scheme) and widget styles for sidebar, header, cards, buttons.
- **Export actions**: Keep existing Excel export; plan for CSV/PDF modules later. Buttons appear in footer ready for Phase 7 integration.

## 5. Immediate Next Steps (for Phase 2)
1. Scaffold new module layout: `src/app/app.py`, `src/app/panels/`, `src/app/datasources/`, preserving current functionality while reorganizing imports.
2. Replace script-style `main()` with instantiable app; ensure Reaction plot can still launch standalone during migration.
3. Create sidebar + notebook placeholders to match template structure before wiring real data.
4. Preserve color palette and Matplotlib styling while enhancing layout containers (frames, labels) to match template hierarchy.
