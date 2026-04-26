## `src/plots/PlotManager.py`

### Module: `PlotManager`
Base class for interactive matplotlib plotting and selection/export utilities.

#### Class: `PlotManager`

**Constructor**
- `PlotManager()`
  - Initializes selection state:
    - `selected_samples`
    - `selected_times`
    - `selection_start`
    - `selection_rect`

**Methods**

- `zoom_around_cursor(self, ax) -> None`
  - Installs a scroll-wheel zoom handler that zooms horizontally around the cursor x-position for a single axis.

- `save_data(self, filename: str) -> str`
  - Exports `selected_times` and `selected_samples` to an `.xlsx` file in `~/Downloads/filename`.
  - Returns the destination path as a string.

- `on_press(self, event, ax) -> None`
  - Left mouse button begins a selection region if the click is inside `ax`.
  - Clears existing selection rectangle.

- `on_release(self, event, ax, time, samples)`
  - Completes selection when releasing left mouse button in `ax`.
  - Builds a boolean mask selecting points between press/release x-limits.
  - Populates `self.selected_times` and `self.selected_samples`.
  - Draws a full-height translucent rectangle on the axis.
  - Returns the selection mask.

- `on_scroll(self, event) -> None`
  - Clears selection rectangle on scroll events.

- `_create_workbook(self, filename: str) -> tuple[xlsxwriter.Workbook, pathlib.Path]`
  - Creates an XlsxWriter workbook at the prepared export path.

- `_prepare_export_path(self, filename: str) -> pathlib.Path`
  - Ensures `~/Downloads` exists and returns the target file path.

---

## `src/plots/ECGPlot.py`

### Module: `ECGPlot`
Real-time ECG waveform visualization and heart rate estimation.

#### Class: `ECGPlot(PlotManager)`

**Constructor**
- `ECGPlot()`
  - Initializes buffers for raw waveform, detected peaks, BPM trend.
  - `window_duration: float` (seconds) used to compute recent BPM.
  - `sample_rate: int` default `8192`.
  - Calls `_setup_plot()`.

**Key attributes (selected)**
- `bpm_values: list[float]`
- `time_values: list[float]`
- `recent_peak_times: list[float]`
- `all_peak_times: list[float]`
- `latest_bpm: float | None`
- `avg_bpm: float | None`

**Methods**
- `_setup_plot(self) -> None`
  - Builds a figure with:
    - waveform axis with peak markers
    - BPM trend axis
  - Installs cursor/zoom/pan callbacks and selection callbacks.
  - Adds a text box for latest BPM.

- `update_plot(self, t_axis: np.ndarray, samples: np.ndarray)`
  - Appends raw data into history.
  - Detects peaks using `scipy.signal.find_peaks`.
  - Updates recent peak history within `window_duration`.
  - Computes BPM from mean RR interval; updates:
    - `latest_bpm`
    - `avg_bpm`
    - `bpm_values`, `time_values`
  - Updates matplotlib artists and returns them.

- `on_press(self, event) -> None`
  - Delegates to `PlotManager.on_press(...)` on waveform axis.

- `on_release(self, event) -> None`
  - Delegates to `PlotManager.on_release(...)` and redraws.

- `shift_review_window(self, direction: float) -> bool`
  - Shifts waveform axis x-limits by `direction * 5`.
  - Returns `True`.

- `_close_plot(self) -> None`
  - Closes the matplotlib figure.

- `plot_all(self) -> None`
  - Replots full stored waveform and BPM trend.

- `save_data(self, filename: str) -> str`
  - Writes an Excel workbook with sheets:
    - “Read Me”
    - “Heart Rate Trend”
    - “Detected Peaks”
    - “Raw Signal”
    - “Selected Window” (only if selection exists)
  - Returns output path.

---

## `src/plots/EMGPlot.py`

### Module: `EMGPlot`
Real-time EMG waveform visualization with envelope extraction.

#### Class: `EMGPlot(PlotManager)`

**Constructor**
- `EMGPlot()`
  - Sets sample rate (`4000`), buffer size (`2048`), bandpass (`20–450 Hz`), and envelope window (`0.15s`).
  - Initializes history buffers.
  - Calls `_setup_plot()`.

**Methods**
- `_setup_plot(self) -> None`
  - Creates a figure with raw EMG and envelope axes.
  - Installs cursor/zoom/pan and selection callbacks.

- `update_plot(self, t_axis, samples)`
  - Extends raw history.
  - Filters signal via Butterworth bandpass + `lfilter`, rectifies, then computes moving-average envelope.
  - Updates plotted artists and returns them.

- `plot_all(self) -> None`
  - Plots full stored raw signal and envelope history.

- `shift_review_window(self, direction) -> bool`
  - Shifts both axes by `direction * 10`.
  - Returns `True`.

- `on_press(self, event)`, `on_release(self, event)`
  - Delegate selection to `PlotManager` and redraw on release.

- `_close_plot(self) -> None`
  - Closes the matplotlib figure.

**Private helpers**
- `_butter_bandpass(self, fs, order=4)`
- `_bandpass_filter(self, data, fs, order=4)`
- `_moving_average(self, data)`

---

## `src/plots/PulseOxPlot.py`

### Module: `PulseOxPlot`
Pulse oximeter visualization and estimation for BPM and SpO₂ from MAX30101-style samples.

#### Class: `PulseOxPlot(PlotManager)`

**Constructor**
- `PulseOxPlot()`
  - Initializes window buffers for red/IR values and a digital “bit view”.
  - Designs a band-pass filter (`0.7–4.0 Hz`) at `fs=10 Hz`.
  - Calls `_setup_plot()`.

**Methods**
- `_setup_plot(self) -> None`
  - Creates:
    - digital signal axis (step plot)
    - analog red/IR axis
  - Installs interactions and selection callbacks.

- `update_plot(self, time_axis, samples)`
  - Parses packed samples into 18-bit red/IR values.
  - Maintains buffers; updates plots.
  - Computes:
    - `bpm` via `estimate_bpm` then `smooth_bpm`
    - `spo2` via `estimate_spo2`
  - Returns updated artists.

- `filtered_ir(self, buf) -> np.ndarray`
  - Applies `filtfilt` band-pass filter to IR buffer.

- `estimate_bpm(self, ir_buf) -> float | None`
  - Detects peaks in filtered IR signal; if sufficient peaks, estimates BPM.

- `smooth_bpm(self, raw_bpm) -> float | None`
  - Moving average smoothing over last few BPM estimates.

- `estimate_spo2(self, red_buf, ir_buf) -> float | None`
  - Estimates SpO₂ using ratio-of-ratios approximation.

- `plot_all(self) -> None`
  - Plots full stored bitstream and full red/IR series.

- `shift_review_window(self, direction) -> bool`
  - Shifts x-limits for both axes by `direction * 20`.

- `on_press(self, event)`, `on_release(self, event)`
  - Uses PlotManager selection on red series, then mirrors mask to IR series into `selected_ir`.

- `save_data(self, filename: str) -> str`
  - Exports selected times, selected red, selected IR into Excel.

- `_close_plot(self) -> None`
  - Closes the matplotlib figure.

---

## `src/plots/ReactionPlot.py`

### Module: `ReactionPlot`
Reaction time visualization using a voltage threshold crossing as a “button press” detector.

#### Class: `ReactionPlot(PlotManager)`

**Constructor**
- `ReactionPlot()`
  - Sets:
    - `sample_rate=10000`
    - `threshold_voltage=2`
    - random cue delay in `[2,5]` seconds
  - Initializes buffers for time series and trial history.
  - Calls `_setup_plot()`.

**Methods**
- `_setup_plot(self) -> None`
  - Creates 2 axes:
    - button signal waveform
    - scatter of reaction time vs trial index
  - Installs cursor/zoom/pan and selection callbacks.

- `update_plot(self, t_axis, samples)`
  - Appends streaming samples into rolling buffers.
  - Triggers a “GO!” cue after random delay.
  - When cue is active, detects button press via `samples > threshold_voltage`:
    - computes reaction time (ms)
    - appends trial result
    - updates scatter plot and cue text
  - Returns updated artists.

- `shift_review_window(self, direction) -> bool`
  - Shifts waveform x-limits by `direction * 20`.

- `plot_all(self) -> None`
  - Plots entire stored waveform.

- `on_press(self, event)`, `on_release(self, event)`
  - Delegates selection to `PlotManager`.

- `save_data(self, filename: str) -> str`
  - Exports workbook with sheets:
    - “Read Me”
    - “Reaction Trials”
    - “Raw Signal”
    - “Selected Window” (if selection exists)

- `_close_plot(self) -> None`

---

## `src/plots/BloodPressurePlot.py`

### Module: `BloodPressurePlot`
Simple real-time blood pressure visualization derived from voltage samples via a linear scaling factor.

#### Class: `BloodPressurePlot(PlotManager)`

**Constructor**
- `BloodPressurePlot()`
  - Initializes rolling buffers and sets:
    - `m: float` scaling factor (default `1`)
    - `window_size: int` (default `200`)
  - Calls `_setup_plot()`.

**Methods**
- `_setup_plot(self) -> None`
  - Creates 2 axes:
    - raw voltage trace
    - converted pressure trace
  - Installs cursor/zoom/pan and selection callbacks.

- `update_plot(self, t_axis, samples)`
  - Appends to history.
  - Converts samples to pressures via `_calc_pressure`.
  - Updates plot lines; returns artists.

- `_calc_pressure(self, samples) -> list[float]`
  - Returns `sample * m` for each sample.

- `plot_all(self, event) -> None`
  - Updates plots to show full history.

- `shift_review_window(self, direction) -> bool`
  - Shifts both axes x-limits by `direction * 50`.

- `on_press(self, event)`, `on_release(self, event)`
  - Delegates selection to `PlotManager` and redraws.

- `_close_plot(self) -> None`

---

## `src/plots/RespiratoryPlot.py`

### Module: `RespiratoryPlot`
Streaming respiratory effort waveform display and breaths-per-minute estimation via rising median-crossings.

#### Class: `RespiratoryPlot(PlotManager)`

**Constructor**
- `RespiratoryPlot()`
  - Defaults:
    - `sample_rate=200`
    - `display_window=20` seconds
    - `rate_window=60` seconds
  - Initializes deques for display and breath history.
  - Creates waveform/rate figure and artists.

**Methods**
- `update_plot(self, t_axis: Iterable[float], samples: Iterable[float])`
  - Maintains a rolling waveform window.
  - Detects breath events via `_detect_breaths`.
  - Updates breath history, computes breaths/min, updates trend plot.
  - Updates:
    - `latest_rate`, `avg_rate`
    - `latest_effort_delta`
    - `window_breath_count`
  - Returns waveform and rate artists.

- `_detect_breaths(self, t_axis: np.ndarray, samples: np.ndarray) -> list[float]`
  - Uses rising crossings of `samples - median(samples)` as breath timestamps.

- `_update_breath_history(self, new_times: list[float], current_time: float) -> None`
  - Maintains breath timestamps within the last `rate_window` seconds.

- `_compute_rate(self) -> float | None`
  - Computes rate as `60 / mean(intervals)` for recent breaths.

- `shift_review_window(self, direction)`
  - Shifts rate axis x-limits by `direction * 10`.

- `plot_all(self) -> None`
  - Not implemented (`pass`).

- `_close_plot(self) -> None`
  - Closes the matplotlib figure.
