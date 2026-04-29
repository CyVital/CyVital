"""Controller-level tests for Tk GUI logic without opening a Tk window."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from gui.models import SensorDefinition, SensorUpdate
from gui import theme
from gui import tkGui


class Var:
    def __init__(self, value=None):
        self.value = value

    def set(self, value):
        self.value = value

    def get(self):
        return self.value


class Widget:
    def __init__(self, **config):
        self.config = dict(config)
        self.bindings = {}
        self.destroyed = False
        self.gridded = False
        self.packed = False
        self.focused = False

    def __getitem__(self, key):
        return self.config[key]

    def configure(self, **kwargs):
        self.config.update(kwargs)

    def bind(self, event, handler):
        self.bindings[event] = handler

    def grid(self, **kwargs):
        self.gridded = True
        self.grid_kwargs = kwargs

    def pack(self, **kwargs):
        self.packed = True
        self.pack_kwargs = kwargs

    def destroy(self):
        self.destroyed = True

    def focus_set(self):
        self.focused = True


class Canvas:
    def __init__(self, figure=None, master=None):
        self.figure = figure
        self.master = master
        self.widget = Widget(bg="white")
        self.draw_count = 0
        self.idle_count = 0

    def get_tk_widget(self):
        return self.widget

    def draw(self):
        self.draw_count += 1

    def draw_idle(self):
        self.idle_count += 1


class EventSource:
    def __init__(self):
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


class Animation:
    def __init__(self):
        self.event_source = EventSource()


class Root:
    def __init__(self):
        self.after_calls = []
        self.quit_called = False
        self.destroy_called = False
        self.updated = False

    def after(self, delay, callback):
        self.after_calls.append((delay, callback))
        callback()

    def update_idletasks(self):
        self.updated = True

    def quit(self):
        self.quit_called = True

    def destroy(self):
        self.destroy_called = True


class Module:
    supports_export = True
    supports_streaming = True

    def __init__(self, figure=True):
        self.figure = object() if figure else None
        self.cleaned = False
        self.paused = False
        self.setup_called = False
        self.saved = False

    def setup_scope(self, scope):
        self.setup_called = True

    def cleanup(self):
        self.cleaned = True

    def get_figure(self):
        return self.figure

    def get_placeholder_message(self):
        return "placeholder"

    def shift_history_window(self, direction):
        self.shifted = direction
        return True

    def update(self, scope):
        return SensorUpdate("P", "S", "log", ("artist",))

    def pause(self):
        self.paused = True

    def save_data(self):
        self.saved = True
        return "out.xlsx"


def make_app():
    app = tkGui.CyVitalApp.__new__(tkGui.CyVitalApp)
    app.root = Root()
    app.scope = MagicMock()
    app.sensor_definitions = {}
    app.nav_items = {}
    app.current_sensor_key = None
    app.current_module = None
    app.animation = None
    app.animation_running = False
    app.canvas = None
    app.canvas_widget = None
    app.placeholder_label = None
    app.plot_frame = Widget()
    app.nav_frame = Widget()
    app.header_title_label = Widget()
    app.header_subtitle_label = Widget()
    app.export_btn = Widget(bg="white", fg="black")
    app.toggle_btn = Widget(bg="white", fg="black")
    app.status_indicator = Widget(fg="grey")
    app.history_buttons = [Widget(), Widget()]
    app.primary_label_var = Var()
    app.secondary_label_var = Var()
    app.primary_value_var = Var()
    app.secondary_value_var = Var()
    app.log_status_var = Var()
    app.status_text_var = Var()
    return app


def test_theme_constants_are_available():
    assert theme.FONT_FAMILY.startswith("{")
    assert "background" in theme.COLORS
    assert "button" in theme.FONTS


def test_attach_button_hover_updates_button_colors():
    app = make_app()
    button = Widget(bg="base", fg="fg")

    app._attach_button_hover(button, emphasis=True)
    button.bindings["<Enter>"](None)
    assert button.config["bg"] == tkGui.COLORS["accent"]
    assert button.config["cursor"] == "hand2"
    button.bindings["<Leave>"](None)
    assert button.config["bg"] == "base"
    assert button.config["fg"] == "fg"


def test_shift_history_draws_when_module_accepts_shift():
    app = make_app()
    app.current_module = Module()
    app.canvas = Canvas()

    app._shift_history(-1)

    assert app.current_module.shifted == -1
    assert app.canvas.idle_count == 1


def test_register_and_set_sensor(monkeypatch):
    app = make_app()
    nav_items = []

    class Nav:
        def __init__(self, parent, title, subtitle, command):
            self.parent = parent
            self.title = title
            self.subtitle = subtitle
            self.command = command
            self.active = None
            nav_items.append(self)

        def set_active(self, active):
            self.active = active

    monkeypatch.setattr(tkGui, "NavItem", Nav)
    monkeypatch.setattr(app, "_render_sensor_content", MagicMock())
    monkeypatch.setattr(app, "_configure_controls_for_sensor", MagicMock())
    definition = SensorDefinition("ecg", "ECG", "Heart", "Primary", "Secondary", Module)

    app.register_sensor(definition)
    app.set_sensor("ecg")

    assert app.sensor_definitions["ecg"] is definition
    assert app.current_sensor_key == "ecg"
    assert app.current_module.setup_called is True
    assert nav_items[0].active is True
    assert app.primary_label_var.get() == "Primary"
    assert app.secondary_label_var.get() == "Secondary"
    assert app.log_status_var.get() == "Ready to stream (press Play)"
    app.set_sensor("missing")
    app.set_sensor("ecg")


def test_render_sensor_content_for_figure_and_placeholder(monkeypatch):
    app = make_app()
    monkeypatch.setattr(tkGui, "FigureCanvasTkAgg", Canvas)

    app.current_module = Module(figure=True)
    app._render_sensor_content()
    assert isinstance(app.canvas, Canvas)
    assert app.canvas_widget.gridded is True
    assert app.canvas.draw_count == 1

    old_widget = app.canvas_widget
    monkeypatch.setattr(tkGui.tk, "Label", lambda *args, **kwargs: Widget(**kwargs))
    app.current_module = Module(figure=False)
    app._render_sensor_content()
    assert old_widget.destroyed is True
    assert app.placeholder_label.config["text"] == "placeholder"
    assert app.placeholder_label.gridded is True


def test_configure_controls_for_sensor_states():
    app = make_app()
    app.current_module = Module(figure=True)
    app._configure_controls_for_sensor()
    assert app.export_btn.config["state"] == tkGui.tk.NORMAL
    assert app.toggle_btn.config["text"] == "Play"
    assert app.status_text_var.get() == "Ready"

    app.current_module = Module(figure=False)
    app.current_module.supports_export = False
    app.current_module.supports_streaming = False
    app._configure_controls_for_sensor()
    assert app.export_btn.config["state"] == tkGui.tk.DISABLED
    assert app.toggle_btn.config["text"] == "Unavailable"
    assert app.status_text_var.get() == "Offline"


def test_update_apply_toggle_export_and_shutdown(monkeypatch):
    app = make_app()
    app.current_module = Module()
    app.canvas = Canvas()
    animation = Animation()
    monkeypatch.setattr(tkGui, "FuncAnimation", lambda *args, **kwargs: animation)

    artists = app._update_frame(0)
    assert artists == ("artist",)
    assert app.primary_value_var.get() == "P"
    assert app.secondary_value_var.get() == "S"
    assert app.log_status_var.get() == "log"

    app.toggle_animation()
    assert app.animation_running is True
    assert animation.event_source.started is True
    assert app.toggle_btn.config["text"] == "Pause"

    app.toggle_animation()
    assert app.animation_running is False
    assert animation.event_source.stopped is True
    assert app.current_module.paused is True
    assert app.status_text_var.get() == "Paused"

    app.export_data()
    assert app.current_module.saved is True
    assert app.log_status_var.get() == "Data exported: out.xlsx"

    app.shutdown()
    assert app.current_module.cleaned is True
    assert app.scope.reset.called is True
    assert app.scope.close.called is True
    assert app.root.quit_called is True
    assert app.root.destroy_called is True
