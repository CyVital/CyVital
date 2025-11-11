"""Tkinter entry point for CyVital

layou structured so sensor stay self-contained

TO ADD NEW SENSOR

1. Implement a subclass of SensorModule
   - Provide a Matplotlib figure (get_figure()) for live plots, or return a
     placeholder string from (get_placeholder_message())
   - Fetch data in (update()) and return a SensorUpdate describing the values
   - Override save_data() if the sensor supports exports
2. Register the sensor by append a SensorDefinition to DEFAULT_SENSORS
   - navigation menu, metric labels, figure embedding all update
   automatically based on the definition
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tkinter as tk
from dataclasses import dataclass
from statistics import mean
from typing import Callable, Dict, Optional, Tuple
import time

import numpy as np

from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from oscilloscope.FakeScope import FakeScope
from oscilloscope.Scope import Scope
from plots.ECGPlot import ECGPlot
from plots.ReactionPlot import ReactionPlot


COLORS = {
    "background": "#f4f7fb",
    "sidebar": "#ffffff",
    "sidebar_hover": "#f0f4ff",
    "sidebar_active": "#e7efff",
    "sidebar_text_primary": "#1d2742",
    "sidebar_text_secondary": "#637190",
    "text_primary": "#1d2742",
    "text_secondary": "#637190",
    "panel": "#ffffff",
    "panel_border": "#d7e3f5",
    "accent": "#2f6fed",
    "accent_text": "#ffffff",
    "status_active": "#2f6fed",
    "status_inactive": "#94a3c0",
    "tooltip_bg": "#1d2742",
    "tooltip_text": "#ffffff",
}


@dataclass
class SensorUpdate:
    #Normalized payload returned each animation frame by a sensor module

    primary_value: Optional[str] = None
    secondary_value: Optional[str] = None
    log_message: Optional[str] = None
    artists: Tuple[object, ...] = ()


@dataclass
class NumericTextParts:
    value: float
    prefix: str
    suffix: str
    decimals: int


class SensorModule:
    #sensor integrations

    supports_streaming: bool = True
    supports_export: bool = False

    def get_figure(self) -> Optional[Figure]:
        #Return a Matplotlib figure to embed in graph
        return None

    def get_placeholder_message(self) -> Optional[str]:
        #Return a when no data
        return None

    def update(self, scope: Scope) -> SensorUpdate:
        #Fetch new data and describe what should ouput
        return SensorUpdate()

    def save_data(self) -> Optional[str]:
        #send collected data when export button
        raise NotImplementedError("Export not implemented for this module.")

    def cleanup(self) -> None:
        #Release resource
        pass

class ReactionSensorModule(SensorModule):
    #reaction-time workflow within app

    supports_export = True

    def __init__(self) -> None:
        self.plot = ReactionPlot()
        self._reaction_configured = False

    def get_figure(self) -> Optional[Figure]:
        return self.plot.fig

    def update(self, scope: Scope) -> SensorUpdate:
        if not self._reaction_configured:
            setup_fn = getattr(scope, "setup_device_reaction", None)
            if callable(setup_fn):
                setup_fn()
            self._reaction_configured = True

        samples = scope.get_reaction_samples()
        t_axis = scope.get_reaction_time_axis(samples)

        artists = self.plot.update_plot(t_axis, samples)
        if artists is None:
            artists_tuple: Tuple[object, ...] = tuple()
        elif isinstance(artists, tuple):
            artists_tuple = artists
        elif isinstance(artists, list):
            artists_tuple = tuple(artists)
        else:
            artists_tuple = (artists,)

        if self.plot.reaction_times:
            latest = self.plot.reaction_times[-1]
            average = mean(self.plot.reaction_times)
            primary = f"{latest:.1f} ms"
            secondary = f"{average:.1f} ms"
            log = (
                f"Trials recorded: {len(self.plot.reaction_times)} | "
                f"Average reaction: {average:.1f} ms"
            )
        else:
            primary = "--"
            secondary = "--"
            log = "Waiting for first reaction sample"

        return SensorUpdate(
            primary_value=primary,
            secondary_value=secondary,
            log_message=log,
            artists=artists_tuple,
        )

    def save_data(self) -> Optional[str]:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        file_str = f"reaction_data_{timestamp}.xlsx"
        return self.plot.save_data(file_str)

    def cleanup(self) -> None:
        self.plot._close_plot()


class ECGSensorModule(SensorModule):
    """Streams ECG samples into the ECGPlot and surfaces BPM stats."""

    supports_export = True

    def __init__(self) -> None:
        self.plot = ECGPlot()
        self._ecg_configured = False

    def get_figure(self) -> Optional[Figure]:
        return self.plot.fig

    def update(self, scope: Scope) -> SensorUpdate:
        if not self._ecg_configured:
            setup_fn = getattr(scope, "setup_device_ecg", None)
            if callable(setup_fn):
                setup_fn()
            self._ecg_configured = True

        samples = scope.get_ecg_samples()
        if hasattr(scope, "get_ecg_time_axis"):
            t_axis = scope.get_ecg_time_axis(samples)
        else:
            sample_rate = getattr(self.plot, "sample_rate", 1) or 1
            t_axis = np.arange(len(samples)) / sample_rate

        artists = self.plot.update_plot(t_axis, samples)
        if artists is None:
            artists_tuple: Tuple[object, ...] = tuple()
        elif isinstance(artists, tuple):
            artists_tuple = artists
        elif isinstance(artists, list):
            artists_tuple = tuple(artists)
        else:
            artists_tuple = (artists,)

        valid_bpm = [value for value in self.plot.bpm_values if value > 0]
        if valid_bpm:
            latest = valid_bpm[-1]
            average = mean(valid_bpm)
            primary = f"{latest:.1f} BPM"
            secondary = f"{average:.1f} BPM"
            elapsed = self.plot.time_values[-1] if self.plot.time_values else 0.0
            log = (
                f"Elapsed time: {elapsed:.1f}s | Peaks in window: {len(self.plot.peak_times)}"
            )
        else:
            primary = "--"
            secondary = "--"
            log = "Detecting ECG peaks..."

        return SensorUpdate(
            primary_value=primary,
            secondary_value=secondary,
            log_message=log,
            artists=artists_tuple,
        )

    def save_data(self) -> Optional[str]:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        file_str = f"ecg_data_{timestamp}.xlsx"
        return self.plot.save_data(file_str)

    def cleanup(self) -> None:
        self.plot._close_plot()


class MessageSensorModule(SensorModule):
    #onboarding instructions

    supports_streaming = False

    def __init__(self, message: str) -> None:
        self.message = message

    def get_placeholder_message(self) -> Optional[str]:
        return self.message


@dataclass
class SensorDefinition:
    #How sensors appear in UI and how to instantiate

    key: str
    title: str
    subtitle: str
    primary_label: str
    secondary_label: str
    module_factory: Callable[[], SensorModule]


DEFAULT_SENSORS = [
    SensorDefinition(
        key="reaction",
        title="Reaction Time",
        subtitle="Response Test",
        primary_label="Latest Reaction",
        secondary_label="Average Reaction",
        module_factory=ReactionSensorModule,
    ),
    SensorDefinition(
        key="ecg",
        title="ECG",
        subtitle="Electrocardiogram",
        primary_label="Current BPM",
        secondary_label="Avg BPM",
        module_factory=ECGSensorModule,
    ),
    SensorDefinition(
        key="emg",
        title="EMG",
        subtitle="Electromyography",
        primary_label="Primary Reading",
        secondary_label="Secondary Reading",
        module_factory=lambda: MessageSensorModule(
            "EMG module not wired yet.\nCreate a SensorModule subclass and update DEFAULT_SENSORS."
        ),
    ),
    SensorDefinition(
        key="pulse",
        title="Pulse Oximeter",
        subtitle="Blood Oxygen",
        primary_label="SpO₂",
        secondary_label="Pulse",
        module_factory=lambda: MessageSensorModule(
            "Pulse Oximeter module not wired yet.\nCreate a SensorModule subclass and update DEFAULT_SENSORS."
        ),
    ),
]


class HoverTooltip:
    """Lightweight tooltip helper for sidebar items."""

    def __init__(self, widget: tk.Widget, text: str, delay: int = 200) -> None:
        self.widget = widget
        self.text = text
        self.delay = delay
        self._after_id: Optional[str] = None
        self.tip_window: Optional[tk.Toplevel] = None

    def schedule(self) -> None:
        if not self.text:
            return
        self.cancel_timer()
        self._after_id = self.widget.after(self.delay, self._show)

    def cancel_timer(self) -> None:
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        self._hide()

    def _show(self) -> None:
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() + 12
        y = self.widget.winfo_rooty() + 10
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.tip_window,
            text=self.text,
            justify=tk.LEFT,
            bg=COLORS["tooltip_bg"],
            fg=COLORS["tooltip_text"],
            relief=tk.SOLID,
            borderwidth=1,
            font=("Segoe UI", 9),
            padx=8,
            pady=4,
        )
        label.pack()

    def _hide(self) -> None:
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class NavItem:
    #Navigation that toggles active sensor

    def __init__(self, parent: tk.Frame, title: str, subtitle: str, command: Callable[[], None]) -> None:
        self.command = command
        self.container = tk.Frame(parent, bg=COLORS["sidebar"])
        self.container.pack(fill=tk.X, pady=4)

        self.indicator = tk.Frame(self.container, width=4, bg=COLORS["sidebar"], height=48)
        self.indicator.pack(side=tk.LEFT, fill=tk.Y)

        self.text_frame = tk.Frame(self.container, bg=COLORS["sidebar"], padx=16, pady=12)
        self.text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.title_label = tk.Label(
            self.text_frame,
            text=title,
            fg=COLORS["sidebar_text_primary"],
            bg=COLORS["sidebar"],
            font=("Segoe UI Semibold", 12),
        )
        self.title_label.pack(anchor="w")

        self.subtitle_label = tk.Label(
            self.text_frame,
            text=subtitle,
            fg=COLORS["sidebar_text_secondary"],
            bg=COLORS["sidebar"],
            font=("Segoe UI", 9),
        )
        self.subtitle_label.pack(anchor="w")

        self.is_active = False
        self.is_hovered = False
        self.tooltip = HoverTooltip(self.container, subtitle)

        self._interactive_widgets = (
            self.container,
            self.indicator,
            self.text_frame,
            self.title_label,
            self.subtitle_label,
        )

        for widget in self._interactive_widgets:
            widget.bind("<Button-1>", self._on_click)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.configure(cursor="hand2")

        self._refresh_colors()

    def _on_click(self, _event: tk.Event) -> None:
        self.tooltip.cancel_timer()
        self.command()

    def _on_enter(self, _event: tk.Event) -> None:
        self.is_hovered = True
        self.tooltip.schedule()
        self._refresh_colors()

    def _on_leave(self, event: tk.Event) -> None:
        widget_under_pointer = self.container.winfo_containing(event.x_root, event.y_root)
        if widget_under_pointer in self._interactive_widgets:
            return
        self.is_hovered = False
        self.tooltip.cancel_timer()
        self._refresh_colors()

    def set_active(self, active: bool) -> None:
        self.is_active = active
        self._refresh_colors()

    def _refresh_colors(self) -> None:
        if self.is_active:
            bg_color = COLORS["sidebar_active"]
            accent = COLORS["accent"]
        elif self.is_hovered:
            bg_color = COLORS["sidebar_hover"]
            accent = COLORS["panel_border"]
        else:
            bg_color = COLORS["sidebar"]
            accent = COLORS["sidebar"]

        for widget in (
            self.container,
            self.text_frame,
            self.title_label,
            self.subtitle_label,
        ):
            widget.configure(bg=bg_color)
        self.indicator.configure(bg=accent)


class CyVitalApp:
    #Main app - sensor wiring and control

    def __init__(self, root: tk.Tk, scope: Scope) -> None:
        self.root = root
        self.scope = scope

        self.sensor_definitions: Dict[str, SensorDefinition] = {}
        self.nav_items: Dict[str, NavItem] = {}

        self.current_sensor_key: Optional[str] = None
        self.current_module: Optional[SensorModule] = None
        self.animation: Optional[FuncAnimation] = None
        self.animation_running = False

        self.canvas: Optional[FigureCanvasTkAgg] = None
        self.canvas_widget: Optional[tk.Widget] = None
        self.placeholder_label: Optional[tk.Label] = None

        self.primary_label_var = tk.StringVar(value="Primary Reading")
        self.secondary_label_var = tk.StringVar(value="Secondary Reading")
        self.primary_value_var = tk.StringVar(value="--")
        self.secondary_value_var = tk.StringVar(value="--")
        self.log_status_var = tk.StringVar(value="No data recorded yet")
        self.status_text_var = tk.StringVar(value="Live")
        self.last_updated_var = tk.StringVar(value="Last updated --")

        self.metric_animation_jobs: Dict[int, Optional[str]] = {}
        self.last_update_time: Optional[float] = None
        self.last_update_job: Optional[str] = None
        self.loading_overlay: Optional[tk.Frame] = None
        self.loading_label: Optional[tk.Label] = None
        self.loading_subtext_label: Optional[tk.Label] = None
        self.loading_animation_job: Optional[str] = None
        self.loading_phase = 0
        self.plot_has_figure = False

        self._configure_root()
        self._build_layout()
        self._register_sensors(DEFAULT_SENSORS)

        if self.sensor_definitions:
            first_key = next(iter(self.sensor_definitions))
            self.set_sensor(first_key)

    def _configure_root(self) -> None:
        self.root.title("CyVital")
        self.root.configure(bg=COLORS["background"])
        self.root.minsize(1180, 720)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

    def _build_layout(self) -> None:
        self.sidebar = tk.Frame(self.root, width=260, bg=COLORS["sidebar"])
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)
        self.sidebar.rowconfigure(1, weight=1)

        self._build_branding()
        self._build_nav()
        self._build_sidebar_footer()
        self._build_main_area()

    def _build_branding(self) -> None:
        brand_frame = tk.Frame(self.sidebar, bg=COLORS["sidebar"], padx=24, pady=32)
        brand_frame.grid(row=0, column=0, sticky="ew")

        tk.Label(
            brand_frame,
            text="CyVital",
            fg=COLORS["sidebar_text_primary"],
            bg=COLORS["sidebar"],
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w")
        tk.Label(
            brand_frame,
            text="Biomedical Monitor",
            fg=COLORS["sidebar_text_secondary"],
            bg=COLORS["sidebar"],
            font=("Segoe UI", 10),
        ).pack(anchor="w")

    def _build_nav(self) -> None:
        self.nav_frame = tk.Frame(self.sidebar, bg=COLORS["sidebar"], padx=16)
        self.nav_frame.grid(row=1, column=0, sticky="nsew")
        self.nav_frame.grid_propagate(False)

    def _build_sidebar_footer(self) -> None:
        footer_frame = tk.Frame(self.sidebar, bg=COLORS["sidebar"], padx=16, pady=20)
        footer_frame.grid(row=2, column=0, sticky="ew")
        tk.Label(
            footer_frame,
            text="Live Monitoring",
            fg=COLORS["accent"],
            bg=COLORS["sidebar_active"],
            font=("Segoe UI", 10, "bold"),
            padx=16,
            pady=12,
        ).pack(fill=tk.X)

    def _build_main_area(self) -> None:
        self.main_container = tk.Frame(self.root, bg=COLORS["background"], padx=20, pady=20)
        self.main_container.grid(row=0, column=1, sticky="nsew")
        self.main_container.columnconfigure(0, weight=1)
        self.main_container.rowconfigure(2, weight=1)

        self._build_header()
        self._build_metrics()
        self._build_plot_area()
        self._build_footer_controls()

    def _build_header(self) -> None:
        header_frame = tk.Frame(self.main_container, bg=COLORS["background"])
        header_frame.grid(row=0, column=0, sticky="ew")

        header_info = tk.Frame(header_frame, bg=COLORS["background"])
        header_info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.header_title_label = tk.Label(
            header_info,
            text="",
            fg=COLORS["text_primary"],
            bg=COLORS["background"],
            font=("Segoe UI", 22, "bold"),
        )
        self.header_title_label.pack(anchor="w")

        self.header_subtitle_label = tk.Label(
            header_info,
            text="",
            fg=COLORS["text_secondary"],
            bg=COLORS["background"],
            font=("Segoe UI", 11),
            pady=4,
        )
        self.header_subtitle_label.pack(anchor="w")

        self.controls_frame = tk.Frame(header_frame, bg=COLORS["background"])
        self.controls_frame.pack(side=tk.RIGHT)

        self.status_indicator = tk.Label(
            self.controls_frame,
            text="●",
            fg=COLORS["status_active"],
            bg=COLORS["background"],
            font=("Segoe UI", 14),
        )
        self.status_indicator.grid(row=0, column=0, padx=(0, 6))

        tk.Label(
            self.controls_frame,
            textvariable=self.status_text_var,
            fg=COLORS["text_primary"],
            bg=COLORS["background"],
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=1, padx=(0, 12))

        self.toggle_btn = tk.Button(
            self.controls_frame,
            text="Pause",
            command=self.toggle_animation,
            bg=COLORS["panel"],
            fg=COLORS["text_primary"],
            activebackground=COLORS["panel_border"],
            activeforeground=COLORS["text_primary"],
            relief=tk.FLAT,
            padx=18,
            pady=8,
        )
        self.toggle_btn.grid(row=0, column=2)

    def _build_metrics(self) -> None:
        metrics_frame = tk.Frame(self.main_container, bg=COLORS["background"])
        metrics_frame.grid(row=1, column=0, sticky="ew", pady=(20, 16))
        metrics_frame.columnconfigure(0, weight=1)
        metrics_frame.columnconfigure(1, weight=1)

        self.primary_card = self._create_metric_card(
            metrics_frame, self.primary_label_var, self.primary_value_var
        )
        self.primary_card.grid(row=0, column=0, sticky="ew", padx=(0, 14))

        self.secondary_card = self._create_metric_card(
            metrics_frame, self.secondary_label_var, self.secondary_value_var
        )
        self.secondary_card.grid(row=0, column=1, sticky="ew", padx=(14, 0))

    def _create_metric_card(
        self, parent: tk.Frame, title_var: tk.StringVar, value_var: tk.StringVar
    ) -> tk.Frame:
        frame = tk.Frame(
            parent,
            bg=COLORS["panel"],
            highlightbackground=COLORS["panel_border"],
            highlightcolor=COLORS["panel_border"],
            highlightthickness=1,
            padx=20,
            pady=20,
        )
        tk.Label(
            frame,
            textvariable=title_var,
            fg=COLORS["text_secondary"],
            bg=COLORS["panel"],
            font=("Segoe UI", 10),
        ).pack(anchor="w")
        value_label = tk.Label(
            frame,
            textvariable=value_var,
            fg=COLORS["accent"],
            bg=COLORS["panel"],
            font=("Segoe UI", 26, "bold"),
            pady=6,
        )
        value_label.pack(anchor="w")
        return frame

    def _build_plot_area(self) -> None:
        self.plot_frame = tk.Frame(
            self.main_container,
            bg=COLORS["panel"],
            highlightbackground=COLORS["panel_border"],
            highlightcolor=COLORS["panel_border"],
            highlightthickness=1,
        )
        self.plot_frame.grid(row=2, column=0, sticky="nsew")
        self.plot_frame.columnconfigure(0, weight=1)
        self.plot_frame.rowconfigure(0, weight=1)

    def _build_footer_controls(self) -> None:
        footer_controls = tk.Frame(self.main_container, bg=COLORS["background"])
        footer_controls.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        footer_controls.columnconfigure(0, weight=1)

        status_stack = tk.Frame(footer_controls, bg=COLORS["background"])
        status_stack.grid(row=0, column=0, sticky="w")

        tk.Label(
            status_stack,
            textvariable=self.log_status_var,
            fg=COLORS["text_secondary"],
            bg=COLORS["background"],
            font=("Segoe UI", 10),
        ).pack(anchor="w")

        tk.Label(
            status_stack,
            textvariable=self.last_updated_var,
            fg=COLORS["sidebar_text_secondary"],
            bg=COLORS["background"],
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(2, 0))

        export_frame = tk.Frame(footer_controls, bg=COLORS["background"])
        export_frame.grid(row=0, column=1, sticky="e")

        self.export_btn = tk.Button(
            export_frame,
            text="Export CSV",
            command=self.export_data,
            bg=COLORS["panel"],
            fg=COLORS["text_primary"],
            activebackground=COLORS["panel_border"],
            activeforeground=COLORS["text_primary"],
            relief=tk.FLAT,
            padx=16,
            pady=8,
        )
        self.export_btn.pack(side=tk.RIGHT)

    def _register_sensors(self, definitions) -> None:
        for definition in definitions:
            self.register_sensor(definition)

    def register_sensor(self, definition: SensorDefinition) -> None:
        #Expose a sensor in menu
        self.sensor_definitions[definition.key] = definition
        nav_item = NavItem(
            self.nav_frame,
            title=definition.title,
            subtitle=definition.subtitle,
            command=lambda key=definition.key: self.set_sensor(key),
        )
        self.nav_items[definition.key] = nav_item

    def set_sensor(self, key: str) -> None:
        #Switch active module based on dilution key
        if key == self.current_sensor_key:
            return

        definition = self.sensor_definitions.get(key)
        if not definition:
            return

        self._stop_animation()
        self._hide_loading_overlay()
        if self.current_module:
            self.current_module.cleanup()

        self.current_sensor_key = key
        self.current_module = definition.module_factory()

        for nav_key, nav_item in self.nav_items.items():
            nav_item.set_active(nav_key == key)

        self.header_title_label.configure(text=f"{definition.title} Monitor")
        self.header_subtitle_label.configure(text=f"Real-time {definition.subtitle.lower()} analysis")
        self.primary_label_var.set(definition.primary_label)
        self.secondary_label_var.set(definition.secondary_label)
        self.primary_value_var.set("--")
        self.secondary_value_var.set("--")
        self.log_status_var.set(
            "Preparing stream..." if self.current_module.supports_streaming else "Stream not connected"
        )
        self._reset_last_update_tracking()

        self._render_sensor_content()
        self._configure_controls_for_sensor()

    def _render_sensor_content(self) -> None:
        if self.canvas_widget:
            self.canvas_widget.destroy()
            self.canvas_widget = None
        if self.placeholder_label:
            self.placeholder_label.destroy()
            self.placeholder_label = None
        self.canvas = None
        self.plot_has_figure = False
        self._hide_loading_overlay()

        figure = self.current_module.get_figure() if self.current_module else None
        if figure:
            self.canvas = FigureCanvasTkAgg(figure, master=self.plot_frame)
            self.canvas_widget = self.canvas.get_tk_widget()
            self.canvas_widget.configure(bg=COLORS["panel"])
            self.canvas_widget.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
            self.canvas.draw()
            self.plot_has_figure = True
            self._show_loading_overlay()
        else:
            message = ""
            if self.current_module:
                placeholder = self.current_module.get_placeholder_message()
                if placeholder:
                    message = placeholder
            self.placeholder_label = tk.Label(
                self.plot_frame,
                text=message or "No visual available for this sensor yet.",
                fg=COLORS["text_secondary"],
                bg=COLORS["panel"],
                font=("Segoe UI", 12),
                justify=tk.CENTER,
                wraplength=480,
                padx=20,
                pady=20,
            )
            self.placeholder_label.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

    def _configure_controls_for_sensor(self) -> None:
        if not self.current_module:
            return

        if self.current_module.supports_export:
            self.export_btn.configure(state=tk.NORMAL)
        else:
            self.export_btn.configure(state=tk.DISABLED)

        if self.current_module.supports_streaming and self.current_module.get_figure():
            self.toggle_btn.configure(state=tk.NORMAL, text="Pause")
            self.animation_running = True
            self.status_indicator.configure(fg=COLORS["status_active"])
            self.status_text_var.set("Live")
            self._start_animation()
        else:
            self.toggle_btn.configure(state=tk.DISABLED, text="Unavailable")
            self.animation_running = False
            self.status_indicator.configure(fg=COLORS["status_inactive"])
            self.status_text_var.set("Offline")
            self._hide_loading_overlay()

    def _start_animation(self) -> None:
        if not self.current_module or not self.current_module.supports_streaming:
            return
        figure = self.current_module.get_figure()
        if not figure:
            return
        self.animation = FuncAnimation(figure, self._update_frame, interval=50, blit=False)

    def _stop_animation(self) -> None:
        if self.animation:
            self.animation.event_source.stop()
            self.animation = None
        self.animation_running = False

    def _update_frame(self, _frame: int):
        if not self.current_module:
            return tuple()

        update = self.current_module.update(self.scope)
        self._apply_sensor_update(update)
        return update.artists or tuple()

    def _apply_sensor_update(self, update: SensorUpdate) -> None:
        data_changed = False
        if update.primary_value is not None:
            self._animate_metric_change(self.primary_value_var, update.primary_value)
            data_changed = True
        if update.secondary_value is not None:
            self._animate_metric_change(self.secondary_value_var, update.secondary_value)
            data_changed = True
        if update.log_message is not None:
            self.log_status_var.set(update.log_message)
            data_changed = True

        data_received = data_changed or bool(update.artists)
        if data_received:
            self._mark_last_update()
            if self.plot_has_figure:
                self._hide_loading_overlay()

        if self.canvas:
            self.canvas.draw_idle()

    def _animate_metric_change(self, target_var: tk.StringVar, target_value: str) -> None:
        current_value = target_var.get()
        if current_value == target_value:
            return

        job_key = id(target_var)
        existing_job = self.metric_animation_jobs.pop(job_key, None)
        if existing_job:
            self.root.after_cancel(existing_job)

        target_parts = self._extract_numeric_parts(target_value)
        current_parts = self._extract_numeric_parts(current_value)
        if not target_parts:
            target_var.set(target_value)
            return
        if not current_parts:
            current_parts = NumericTextParts(
                value=target_parts.value,
                prefix=target_parts.prefix,
                suffix=target_parts.suffix,
                decimals=target_parts.decimals,
            )

        value_delta = target_parts.value - current_parts.value
        if abs(value_delta) < 1e-6:
            target_var.set(target_value)
            return

        start_time = time.time()
        duration = 0.45  # seconds

        def step() -> None:
            elapsed = time.time() - start_time
            progress = min(1.0, elapsed / duration)
            eased = 1 - pow(1 - progress, 3)
            interpolated = current_parts.value + value_delta * eased
            formatted = self._format_numeric_text(
                interpolated, target_parts.prefix, target_parts.suffix, target_parts.decimals
            )
            target_var.set(formatted)
            if progress < 1.0:
                self.metric_animation_jobs[job_key] = self.root.after(16, step)
            else:
                target_var.set(target_value)
                self.metric_animation_jobs.pop(job_key, None)

        step()

    def _extract_numeric_parts(self, text: str) -> Optional[NumericTextParts]:
        match = re.search(r"[-+]?\d*\.?\d+", text)
        if not match:
            return None
        number_text = match.group(0)
        decimals = 0
        if "." in number_text:
            decimals = len(number_text.split(".")[1])
        return NumericTextParts(
            value=float(number_text),
            prefix=text[: match.start()],
            suffix=text[match.end() :],
            decimals=decimals,
        )

    def _format_numeric_text(self, value: float, prefix: str, suffix: str, decimals: int) -> str:
        if decimals <= 0:
            number = f"{value:.0f}"
        else:
            number = f"{value:.{decimals}f}"
        return f"{prefix}{number}{suffix}"

    def _reset_last_update_tracking(self) -> None:
        self.last_update_time = None
        if self.last_update_job:
            self.root.after_cancel(self.last_update_job)
            self.last_update_job = None
        self.last_updated_var.set("Last updated --")

    def _mark_last_update(self) -> None:
        self.last_update_time = time.time()
        self.last_updated_var.set("Last updated just now")
        if self.last_update_job:
            self.root.after_cancel(self.last_update_job)
        self.last_update_job = self.root.after(1000, self._refresh_last_updated_label)

    def _refresh_last_updated_label(self) -> None:
        if self.last_update_time is None:
            self.last_updated_var.set("Last updated --")
            self.last_update_job = None
            return
        elapsed = max(0, int(time.time() - self.last_update_time))
        if elapsed < 1:
            text = "Last updated just now"
        elif elapsed == 1:
            text = "Last updated 1s ago"
        else:
            text = f"Last updated {elapsed}s ago"
        self.last_updated_var.set(text)
        self.last_update_job = self.root.after(1000, self._refresh_last_updated_label)

    def _show_loading_overlay(self) -> None:
        if not self.plot_has_figure or self.loading_overlay:
            return
        self.loading_overlay = tk.Frame(
            self.plot_frame,
            bg=COLORS["panel"],
            highlightthickness=0,
        )
        self.loading_overlay.place(relx=0.5, rely=0.5, anchor="center")
        self.loading_label = tk.Label(
            self.loading_overlay,
            text="Loading data",
            fg=COLORS["text_primary"],
            bg=COLORS["panel"],
            font=("Segoe UI", 14, "bold"),
        )
        self.loading_label.pack()
        self.loading_subtext_label = tk.Label(
            self.loading_overlay,
            text="Preparing visualization...",
            fg=COLORS["text_secondary"],
            bg=COLORS["panel"],
            font=("Segoe UI", 10),
        )
        self.loading_subtext_label.pack(pady=(4, 0))
        self.loading_phase = 0
        self._animate_loading_label()

    def _animate_loading_label(self) -> None:
        if not self.loading_overlay or not self.loading_label:
            return
        dots = "." * (self.loading_phase % 4)
        self.loading_label.configure(text=f"Loading data{dots}")
        self.loading_phase += 1
        self.loading_animation_job = self.root.after(300, self._animate_loading_label)

    def _hide_loading_overlay(self) -> None:
        if self.loading_animation_job:
            self.root.after_cancel(self.loading_animation_job)
            self.loading_animation_job = None
        if self.loading_overlay:
            self.loading_overlay.destroy()
            self.loading_overlay = None
        self.loading_label = None
        self.loading_subtext_label = None
        self.loading_phase = 0

    def toggle_animation(self) -> None:
        if not self.animation or not self.current_module:
            return
        if self.animation_running:
            self.animation.event_source.stop()
            self.animation_running = False
            self.toggle_btn.configure(text="Resume")
            self.status_indicator.configure(fg=COLORS["status_inactive"])
            self.status_text_var.set("Paused")
        else:
            self.animation.event_source.start()
            self.animation_running = True
            self.toggle_btn.configure(text="Pause")
            self.status_indicator.configure(fg=COLORS["status_active"])
            self.status_text_var.set("Live")

    def export_data(self) -> None:
        if self.current_module and self.current_module.supports_export:
            destination = self.current_module.save_data()
            if destination:
                self.log_status_var.set(f"Data exported: {destination}")
            else:
                self.log_status_var.set("Data exported.")

    def shutdown(self) -> None:
        self._stop_animation()
        self._hide_loading_overlay()
        if self.current_module:
            self.current_module.cleanup()
        try:
            self.scope.reset()
            self.scope.close()
        except Exception:
            pass
        self.root.quit()
        self.root.destroy()


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="CyVital GUI")
    parser.add_argument(
        "--fake-scope",
        action="store_true",
        help="Run the app with synthetic oscilloscope data instead of hardware.",
    )
    parser.add_argument(
        "--fake-seed",
        type=int,
        help="Optional random seed for the fake scope to get repeatable traces.",
    )
    args = parser.parse_args(argv)

    if args.fake_scope:
        scope = FakeScope(rng_seed=args.fake_seed)
    else:
        scope = Scope()

    root = tk.Tk()
    app = CyVitalApp(root, scope)

    def on_closing() -> None:
        app.shutdown()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.shutdown()


if __name__ == "__main__":
    main()
