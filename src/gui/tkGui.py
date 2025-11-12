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
import sys
import tkinter as tk
from dataclasses import dataclass
from statistics import mean
from typing import Callable, Dict, Optional, Tuple
import time

from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from oscilloscope.FakeScope import FakeScope
from oscilloscope.Scope import Scope
from plots.ReactionPlot import ReactionPlot
from plots.EMGPlot import EMGPlot
from plots.ECGPlot import ECGPlot


COLORS = {
    "background": "#f4f7fb",
    "sidebar": "#ffffff",
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
}


@dataclass
class SensorUpdate:
    #Normalized payload returned each animation frame by a sensor module

    primary_value: Optional[str] = None
    secondary_value: Optional[str] = None
    log_message: Optional[str] = None
    artists: Tuple[object, ...] = ()


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

    def get_figure(self) -> Optional[Figure]:
        return self.plot.fig

    def update(self, scope: Scope) -> SensorUpdate:
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

class EMGSensorModule(SensorModule):

    supports_export = True

    def __init__(self) -> None:
        self.plot = EMGPlot()

    def get_figure(self) -> Optional[Figure]:
        return self.plot.fig

    def update(self, scope: Scope) -> SensorUpdate:
        samples = scope.get_emg_samples()
        t_axis = scope.get_emg_time_axis(samples)

        artists = self.plot.update_plot(t_axis, samples)
        if artists is None:
            artists_tuple: Tuple[object, ...] = tuple()
        elif isinstance(artists, tuple):
            artists_tuple = artists
        elif isinstance(artists, list):
            artists_tuple = tuple(artists)
        else:
            artists_tuple = (artists,)

        return SensorUpdate(
            primary_value="--",
            secondary_value="--",
            log_message= "",
            artists=artists_tuple,
        )

    def save_data(self) -> Optional[str]:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        file_str = f"emg_data_{timestamp}.xlsx"
        return self.plot.save_data(file_str)

    def cleanup(self) -> None:
        self.plot._close_plot()

class ECGSensorModule(SensorModule):

    supports_export = True

    def __init__(self) -> None:
        self.plot = ECGPlot()

    def get_figure(self) -> Optional[Figure]:
        return self.plot.fig

    def update(self, scope: Scope) -> SensorUpdate:
        samples = scope.get_ecg_samples()
        t_axis = None 

        artists = self.plot.update_plot(t_axis, samples)
        if artists is None:
            artists_tuple: Tuple[object, ...] = tuple()
        elif isinstance(artists, tuple):
            artists_tuple = artists
        elif isinstance(artists, list):
            artists_tuple = tuple(artists)
        else:
            artists_tuple = (artists,)

        return SensorUpdate(
            primary_value="--",
            secondary_value="--",
            log_message= "",
            artists=artists_tuple,
        )

    def save_data(self) -> Optional[str]:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        file_str = f"emg_data_{timestamp}.xlsx"
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
        primary_label="Primary Reading",
        secondary_label="Secondary Reading",
        module_factory=ECGSensorModule,
    ),
    SensorDefinition(
        key="emg",
        title="EMG",
        subtitle="Electromyography",
        primary_label="Primary Reading",
        secondary_label="Secondary Reading",
        module_factory=EMGSensorModule,
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

        for widget in (
            self.container,
            self.indicator,
            self.text_frame,
            self.title_label,
            self.subtitle_label,
        ):
            widget.bind("<Button-1>", self._on_click)

    def _on_click(self, _event: tk.Event) -> None:
        self.command()

    def set_active(self, active: bool) -> None:
        bg_color = COLORS["sidebar_active"] if active else COLORS["sidebar"]
        accent = COLORS["accent"] if active else COLORS["sidebar"]

        self.container.configure(bg=bg_color)
        self.text_frame.configure(bg=bg_color)
        self.title_label.configure(bg=bg_color)
        self.subtitle_label.configure(bg=bg_color)
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
        tk.Label(
            frame,
            textvariable=value_var,
            fg=COLORS["accent"],
            bg=COLORS["panel"],
            font=("Segoe UI", 26, "bold"),
            pady=6,
        ).pack(anchor="w")
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

        tk.Label(
            footer_controls,
            textvariable=self.log_status_var,
            fg=COLORS["text_secondary"],
            bg=COLORS["background"],
            font=("Segoe UI", 10),
        ).grid(row=0, column=0, sticky="w")

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

        figure = self.current_module.get_figure() if self.current_module else None
        if figure:
            self.canvas = FigureCanvasTkAgg(figure, master=self.plot_frame)
            self.canvas_widget = self.canvas.get_tk_widget()
            self.canvas_widget.configure(bg=COLORS["panel"])
            self.canvas_widget.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
            self.canvas.draw()
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
        if update.primary_value is not None:
            self.primary_value_var.set(update.primary_value)
        if update.secondary_value is not None:
            self.secondary_value_var.set(update.secondary_value)
        if update.log_message is not None:
            self.log_status_var.set(update.log_message)
        if self.canvas:
            self.canvas.draw_idle()

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
