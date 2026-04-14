# CyVital GUI API Documentation

This document covers the public API surface and intended usage for the Tk GUI layer and its sensor-module integrations.

## `src/gui/models.py` — GUI models (dataclasses)

UI-facing dataclasses shared across the Tk GUI. These types are used as the contract between:

- the GUI (`tkGui.py`)
- individual sensor modules (`src/gui/sensors/*`)
- plot layers (`src/plots/*`)

### `SensorUpdate`
Dataclass describing what a sensor module produced during a single UI refresh / animation frame.

Returned by `SensorModule.update()` and consumed by the GUI to update:
- primary/secondary metric readouts
- status/log message text
- Matplotlib artists that need to be re-drawn

#### Fields
- `primary_value: Optional[str] = None`  
  Primary metric string (e.g., `"72.4 BPM"`, `"98.0 %"`).

- `secondary_value: Optional[str] = None`  
  Secondary metric string (e.g., average or trend).

- `log_message: Optional[str] = None`  
  Short UI status string (e.g., `"Detecting ECG peaks..."`).

- `artists: Tuple[object, ...] = ()`  
  Matplotlib artists updated this frame (Line2D, Text, etc.). Returned to the animation driver for efficient redraw.

---

### `SensorDefinition`
Dataclass describing how a sensor appears in the UI and how to instantiate its module.

Usually created in a registry (see `src/gui/sensors/registry.py`) and registered with the app.

#### Fields
- `key: str`  
  Unique identifier used to select the sensor (e.g., `"ecg"`, `"reaction"`).

- `title: str`  
  Sidebar display name.

- `subtitle: str`  
  Sidebar secondary text.

- `primary_label: str`  
  Label for the primary metric card.

- `secondary_label: str`  
  Label for the secondary metric card.

- `module_factory: Callable[[], SensorModule]`  
  Factory that creates a `SensorModule` implementation (typically a class).

> Note: `SensorModule` is referenced as a type but not imported in this module; implementations live in
> `src/gui/sensors/base.py`.

---

## `src/gui/theme.py` — Tkinter theme constants

Shared theme constants for the CyVital Tk GUI: font families, font tuples, and color tokens.

### Constants

- `BASE_FONT_FAMILY: str`  
  Base font family name (default: `"Segoe UI"`).

- `FONT_FAMILY: str`  
  Brace-wrapped font family string used for Tk so that the family name is treated as a single token.
  Example: `"{Segoe UI}"`.

### Dictionaries

#### `COLORS: dict[str, str]`
Central palette used by the GUI.

Common keys:
- `"background"`, `"panel"`, `"panel_border"`, `"panel_gloss"`
- `"sidebar"`, `"sidebar_hover"`, `"sidebar_active"`
- `"sidebar_text_primary"`, `"sidebar_text_secondary"`
- `"text_primary"`, `"text_secondary"`
- `"accent"`, `"accent_muted"`, `"accent_text"`
- `"status_active"`, `"status_inactive"`
- `"tooltip_bg"`, `"tooltip_text"`

#### `FONTS: dict[str, tuple]`
Tk font tuples keyed by semantic usage.

---

## `src/gui/tkGui.py` — Tk GUI application

Tkinter GUI entrypoint, navigation, sensor lifecycle management, and the animation loop.

This module wires together:
- a `Scope` instance (hardware access; `oscilloscope/Scope.py`)
- registered `SensorDefinition` entries and instantiated `SensorModule` implementations
- Matplotlib figures embedded in the Tk UI
- controls (start/stop streaming, export, history shifting)

### Globals

- `SCRIPT_DIR: str`  
  Directory containing `tkGui.py`.

- `SRC_ROOT: str`  
  Absolute path to the `src/` root (computed from `SCRIPT_DIR`).

- `LOGGER: logging.Logger`  
  Module logger.

### `NavItem`
Sidebar navigation item that toggles the active sensor.

#### Constructor
- `NavItem(parent: tk.Frame, title: str, subtitle: str, command: Callable[[], None]) -> None`

Creates a clickable navigation row; triggers `command()` on click.

#### Methods
- `_on_click(self, _event: tk.Event) -> None`  
  Invokes the configured command.

- `set_active(self, active: bool) -> None`  
  Updates visual state to reflect selection.

---

### `CyVitalApp`
Main app: builds layout, registers sensors, embeds plots, runs/pauses streaming updates, and manages exporting + shutdown.

#### Constructor
- `CyVitalApp(root: tk.Tk, scope: Scope) -> None`

#### Layout / build helpers
These methods typically construct and pack/grid Tk widgets.

- `_configure_root(self) -> None`
- `_build_layout(self) -> None`
- `_build_branding(self) -> None`
- `_build_nav(self) -> None`
- `_build_sidebar_footer(self) -> None`
- `_build_main_area(self) -> None`
- `_build_header(self) -> None`
- `_build_metrics(self) -> None`
- `_create_metric_card(self, ...) -> ...`
- `_build_plot_area(self) -> None`
- `_build_footer_controls(self) -> None`

#### UI behavior helpers
- `_attach_button_hover(self, button: tk.Button, *, emphasis: bool = False) -> None`  
  Adds hover styling (bg/fg/cursor) to a button.

- `_shift_history(self, direction: int) -> None`  
  Requests a sensor module to shift its review window left/right (if supported).

#### Sensor registry / selection
- `_register_sensors(self, definitions) -> None`  
  Registers multiple `SensorDefinition` entries.

- `register_sensor(self, definition: SensorDefinition) -> None`  
  Registers a single sensor definition.

- `set_sensor(self, key: str) -> None`  
  Switches the active sensor by key. Typical responsibilities:
  - stop/pause previous module
  - cleanup old plot embeds
  - instantiate new module via `definition.module_factory()`
  - call `module.setup_scope(scope)` when streaming is supported
  - update UI labels + plot embedding

- `_render_sensor_content(self) -> None`  
  Refreshes the main area for the active sensor.

- `_configure_controls_for_sensor(self) -> None`  
  Enables/disables streaming/export controls based on module capability flags.

#### Animation lifecycle
- `_start_animation(self) -> None`
- `_stop_animation(self) -> None`
- `_update_frame(self, _frame: int)`  
  Typically calls `module.update(scope)` and applies the update.

- `_apply_sensor_update(self, update: SensorUpdate) -> None`  
  Applies:
  - `primary_value`, `secondary_value`
  - `log_message`
  - updated Matplotlib artists

- `toggle_animation(self) -> None`
- `export_data(self) -> None`
- `shutdown(self) -> None`

### `main(argv: Optional[list[str]] = None) -> None`
Entry point for launching the app. Usually:
- initializes Tk root
- creates `Scope`
- creates `CyVitalApp`
- sets window close handler (e.g., `on_closing`)
- runs `root.mainloop()`

---

## `src/gui/sensors/base.py` — Sensor module interface

Defines the interface for GUI sensor modules.

A sensor module is responsible for:
- configuring the `Scope` for a modality (optional)
- returning a Matplotlib `Figure` for embedding (optional)
- producing `SensorUpdate` objects on each UI refresh
- exporting captured data (optional)
- releasing resources on shutdown

### `SensorModule`

#### Capability flags
- `supports_streaming: bool = True`  
  Whether the module streams live updates from `Scope`.

- `supports_export: bool = False`  
  Whether `save_data()` is implemented.

#### Methods

- `get_figure(self) -> Optional[matplotlib.figure.Figure]`  
  Return the Matplotlib figure to embed, or `None`. Default returns `None`.

- `setup_scope(self, scope: oscilloscope.Scope.Scope) -> None`  
  Configure the scope for this modality. Default no-op.

- `get_placeholder_message(self) -> Optional[str]`  
  Return a message when no plot/data is available. Default `None`.

- `update(self, scope: oscilloscope.Scope.Scope) -> SensorUpdate`  
  Fetch new data and return a `SensorUpdate`. Default returns `SensorUpdate()`.

- `save_data(self) -> Optional[str]`  
  Export captured data. Default raises `NotImplementedError`.

- `cleanup(self) -> None`  
  Release resources. Default no-op.

---

## `src/gui/sensors/helpers.py` — Shared helpers

### `normalize_artists(artists: object) -> tuple[object, ...]`
Normalizes the return value of a plot update into a tuple of artists.

#### Parameters
- `artists: object`
  - `None`, `tuple`, `list`, or a single artist-like object.

#### Returns
- `tuple[object, ...]`
  - `()` if `artists is None`
  - `artists` if `artists` is already a tuple
  - `tuple(artists)` if `artists` is a list
  - `(artists,)` otherwise

---

## `src/gui/sensors/message.py` — Message-only sensor module

### `MessageSensorModule(SensorModule)`
A placeholder module that does not stream and only provides a static message.

#### Capability flags
- `supports_streaming: bool = False`

#### Constructor
- `MessageSensorModule(message: str) -> None`

#### Methods
- `get_placeholder_message(self) -> Optional[str]`  
  Returns the configured message.

---

## `src/gui/sensors/blood_pressure.py` — Blood pressure sensor module

### `BloodPressureSensorModule(SensorModule)`
GUI integration for blood pressure acquisition and plotting.

#### Capability flags
- `supports_export: bool = True`

#### Constructor
- `BloodPressureSensorModule() -> None`  
  Creates `self.plot = BloodPressurePlot()`.

#### Methods
- `get_figure(self) -> Optional[Figure]`  
  Returns `self.plot.fig`.

- `setup_scope(self, scope: Scope) -> None`  
  Calls `scope.setup_device_blood_pressure()`. On setup failure, disables streaming and logs warning.

- `shift_history_window(self, direction: int) -> bool`  
  Delegates to `self.plot.shift_review_window(direction)`.

- `update(self, scope: Scope) -> SensorUpdate`  
  Reads samples/time axis from scope and updates plot. Returns `SensorUpdate` with normalized artists.
  On `IOError`, returns empty artists and log message `"IO Error: Cannot read scope"`.

- `pause(self) -> None`  
  Calls `self.plot.plot_all()`.

- `save_data(self) -> Optional[str]`  
  Exports to `blood_pressure_data_<timestamp>.xlsx` via the plot.

- `cleanup(self) -> None`  
  Closes plot via `self.plot._close_plot()`.

---

## `src/gui/sensors/ecg.py` — ECG sensor module

### `ECGSensorModule(SensorModule)`
GUI integration for ECG waveform streaming + BPM display.

#### Capability flags
- `supports_export: bool = True`

#### Constructor
- `ECGSensorModule() -> None`  
  Creates `self.plot = ECGPlot()`.

#### Methods
- `setup_scope(self, scope: Scope) -> None`  
  Calls `scope.setup_device_ecg()`. On failure, disables streaming and logs warning.

- `get_figure(self) -> Optional[Figure]`  
  Returns `self.plot.fig`.

- `shift_history_window(self, direction: int) -> bool`  
  Delegates to `self.plot.shift_review_window(direction)`.

- `update(self, scope: Scope) -> SensorUpdate`  
  Reads ECG samples and time axis, updates plot, and formats UI metrics:
  - primary: latest BPM
  - secondary: average BPM (or latest if average not available)
  - log: elapsed time + peak count in window
  If BPM not available yet: placeholders and `"Detecting ECG peaks..."`.
  On `IOError`: placeholders and `"IO Error: Cannot read scope"`.

- `save_data(self) -> Optional[str]`  
  Exports to `ecg_data_<timestamp>.xlsx` via plot.

- `pause(self) -> None`  
  Calls `self.plot.plot_all()`.

- `cleanup(self) -> None`  
  Closes plot via `self.plot._close_plot()`.

---

## `src/gui/sensors/emg.py` — EMG sensor module

### `EMGSensorModule(SensorModule)`
GUI integration for EMG streaming and envelope plotting.

#### Capability flags
- `supports_export: bool = True`

#### Constructor
- `EMGSensorModule() -> None`  
  Creates `self.plot = EMGPlot()`.

#### Methods
- `get_figure(self) -> Optional[Figure]`  
  Returns `self.plot.fig`.

- `setup_scope(self, scope: Scope) -> None`  
  Calls `scope.setup_device_emg()`. On failure, disables streaming and logs warning.

- `shift_history_window(self, direction: int) -> bool`  
  Delegates to `self.plot.shift_review_window(direction)`.

- `update(self, scope: Scope) -> SensorUpdate`  
  Reads EMG samples and time axis, updates plot, returns normalized artists.
  Uses placeholder metric strings (`"--"`). On `IOError`, returns empty artists and log message.

- `pause(self) -> None`  
  Calls `self.plot.plot_all()`.

- `save_data(self) -> Optional[str]`  
  Exports to `emg_data_<timestamp>.xlsx`.

- `cleanup(self) -> None`  
  Closes plot via `self.plot._close_plot()`.

---

## `src/gui/sensors/pulse_ox.py` — Pulse oximeter sensor module

### `PulseOxSensorModule(SensorModule)`
GUI integration for pulse oximeter acquisition and estimation.

#### Capability flags
- `supports_export: bool = True`

#### Constructor
- `PulseOxSensorModule() -> None`  
  Creates `self.plot = PulseOxPlot()`.

#### Methods
- `setup_scope(self, scope: Scope) -> None`  
  Calls `scope.setup_device_pulse_ox()`. On failure, disables streaming and logs warning.

- `get_figure(self) -> Optional[Figure]`  
  Returns `self.plot.fig`.

- `shift_history_window(self, direction: int) -> bool`  
  Delegates to `self.plot.shift_review_window(direction)`.

- `update(self, scope: Scope) -> SensorUpdate`  
  Reads packed pulse ox samples and time axis, updates plot.
  If both BPM and SpO₂ are available, formats:
  - primary: SpO₂ percent string
  - secondary: BPM string
  Otherwise: placeholders and `"Waiting for first pulse ox sample"`.
  On `IOError`: placeholders and `"IO Error: Cannot read scope"`.

- `pause(self) -> None`  
  Calls `self.plot.plot_all()`.

- `save_data(self) -> Optional[str]`  
  Exports to `pulse_ox_data_<timestamp>.xlsx`.

- `cleanup(self) -> None`  
  Closes plot via `self.plot._close_plot()`.

---

## `src/gui/sensors/reaction.py` — Reaction-time sensor module

### `ReactionSensorModule(SensorModule)`
GUI integration for the reaction-time workflow (cue + threshold press detection handled in plot layer).

#### Capability flags
- `supports_export: bool = True`

#### Constructor
- `ReactionSensorModule() -> None`  
  Creates `self.plot = ReactionPlot()`.

#### Methods
- `setup_scope(self, scope: Scope) -> None`  
  Calls `scope.setup_device_reaction()`. On failure, disables streaming and logs warning.

- `get_figure(self) -> Optional[Figure]`  
  Returns `self.plot.fig`.

- `shift_history_window(self, direction: int) -> bool`  
  Delegates to `self.plot.shift_review_window(direction)`.

- `update(self, scope: Scope) -> SensorUpdate`  
  Reads reaction samples and time axis, updates plot.
  If trials exist, formats:
  - primary: latest reaction time in ms
  - secondary: mean reaction time in ms
  - log: trial count + average
  Else placeholders and `"Waiting for first reaction sample"`.
  On `IOError`: placeholders and `"IO Error: Cannot read scope"`.

- `pause(self) -> None`  
  Calls `self.plot.plot_all()`.

- `save_data(self) -> Optional[str]`  
  Exports to `reaction_data_<timestamp>.xlsx`.

- `cleanup(self) -> None`  
  Closes plot via `self.plot._close_plot()`.

---

## `src/gui/sensors/respiratory.py` — Respiratory effort sensor module

### `RespiratorySensorModule(SensorModule)`
Streams respiratory effort data and surfaces respiration metrics (breaths/min and effort range).

#### Capability flags
- `supports_export: bool = True`

#### Constructor
- `RespiratorySensorModule() -> None`  
  Creates `self.plot = RespiratoryPlot()` and sets `_configured = False`.

#### Methods
- `get_figure(self) -> Optional[Figure]`  
  Returns `self.plot.fig`.

- `shift_history_window(self, direction: int) -> bool`  
  Delegates to `self.plot.shift_review_window(direction)`.

- `update(self, scope: Scope) -> SensorUpdate`  
  Lazy configuration:
  - On the first call, if `scope.setup_device_respiratory` exists and is callable, it is invoked.
  Per-frame:
  - Reads `scope.get_respiratory_samples()`
  - Time axis uses `scope.get_respiratory_time_axis(samples)` if present, else falls back to `np.arange(...) / sample_rate`
  - Updates plot and normalizes artists
  - Formats:
    - primary: latest rate as `BrPM` when available
    - secondary: effort voltage delta
    - log: breath count in the last `rate_window` seconds
  Errors:
  - `(IOError, OSError)`: `"IO error: respiratory stream unavailable"`
  - `(AttributeError, ValueError, TypeError)`: `"Respiratory processing error (see logs)"`

- `pause(self) -> None`  
  Calls `self.plot.plot_all()` (note: current `RespiratoryPlot.plot_all()` is `pass` in the snippet you shared).

- `save_data(self) -> Optional[str]`  
  Exports to `resp_data_<timestamp>.xlsx` via plot.

- `cleanup(self) -> None`  
  Closes plot via `self.plot._close_plot()`.

---

## `src/gui/sensors/registry.py` — Default sensor registry

Defines the default list of sensors available to the Tk GUI.

### `DEFAULT_SENSORS: list[SensorDefinition]`
A list of `SensorDefinition` entries used to populate navigation and instantiate modules.

Included sensors:
- `reaction` → `ReactionSensorModule`
- `ecg` → `ECGSensorModule`
- `emg` → `EMGSensorModule`
- `pulse` → `PulseOxSensorModule`
- `pressure` → `BloodPressureSensorModule`
- `resp` → `RespiratorySensorModule`
