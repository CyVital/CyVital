# CyVital GUI

# Current GUI
- `src/gui/tkGui.py` creates a plain `tk.Tk` window, embeds single Matplotlib w/ `FigureCanvasTkAgg`, and wires a `FuncAnimation` loop to update the reaction-time plot making it "live"
- Data pipeline: Uses `Scope` from `src/oscilloscope/Scope.py` inside the GUI thread
- Plotting logic: Handled by `ReactionPlot` in `src/plots/ReactionPlot.py` creates, cues, selection rectangles, and exports to excel.
- UI controls: Two `tk.Button` widgets (Stop, Save) stacked under the plot

# Architecture
- **App shell**: Move toward `CyVitalApp(tk.Tk)` responsible for window, layout, themes
- **Panels**: reusable `PlotPanel` base specific modalities extend. Reaction panel has `ReactionPlot` logic.
- **Data abstraction**:`DataSource` interface wrapping `Scope` for fallback simulation, reduced latency

# Next Steps?
1. new module layout: `src/app/app.py`, `src/app/panels/`, `src/app/datasources/`, reorganizing imports...
2. Replace `main()` with app & ensure Reaction plot can still launch standalone
3. sidebar + notebook placeholders
4. Better Export features
5. professionalize features, focus on usability and feel