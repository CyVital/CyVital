"""Tests for src/gui/tkGui.py.

tkinter and the Tk-backend of matplotlib are not available in headless CI;
we substitute them with MagicMock objects *before* importing the module so
that every ``import tkinter as tk`` and ``from ... import FigureCanvasTkAgg``
inside tkGui resolve to our stubs.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stubs – must be installed in sys.modules BEFORE tkGui is imported.
# ---------------------------------------------------------------------------

_tk_mock = MagicMock()
for _attr in (
    "X", "Y", "BOTH", "LEFT", "RIGHT", "TOP", "BOTTOM",
    "NS", "EW", "NSEW", "N", "S", "E", "W",
    "FLAT", "NORMAL", "DISABLED", "CENTER",
):
    setattr(_tk_mock, _attr, _attr)

sys.modules.setdefault("tkinter", _tk_mock)
sys.modules.setdefault("matplotlib.backends.backend_tkagg", MagicMock())

# Now safe to import the module under test.
from gui.tkGui import NavItem, CyVitalApp, main  # noqa: E402
from gui.models import SensorUpdate  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_module(
    supports_streaming: bool = True,
    supports_export: bool = True,
    has_figure: bool = True,
    placeholder: str | None = None,
) -> MagicMock:
    m = MagicMock()
    m.supports_streaming = supports_streaming
    m.supports_export = supports_export
    m.get_figure.return_value = MagicMock() if has_figure else None
    m.get_placeholder_message.return_value = placeholder
    m.update.return_value = SensorUpdate(
        primary_value="1", secondary_value="2", log_message="ok"
    )
    m.shift_history_window.return_value = True
    return m


def _make_mock_definition(
    key: str = "test",
    title: str = "Test Sensor",
    subtitle: str = "Test Sub",
    primary_label: str = "Primary",
    secondary_label: str = "Secondary",
    module: object | None = None,
) -> MagicMock:
    d = MagicMock()
    d.key = key
    d.title = title
    d.subtitle = subtitle
    d.primary_label = primary_label
    d.secondary_label = secondary_label
    if module is None:
        module = _make_mock_module()
    d.module_factory = MagicMock(return_value=module)
    return d


def _make_app(definitions=None, scope=None):
    """Instantiate CyVitalApp with mocked DEFAULT_SENSORS."""
    if scope is None:
        scope = MagicMock()
    if definitions is None:
        definitions = [_make_mock_definition()]
    root = MagicMock()
    with patch("gui.tkGui.DEFAULT_SENSORS", definitions):
        app = CyVitalApp(root, scope)
    return app, root, scope


# ---------------------------------------------------------------------------
# NavItem
# ---------------------------------------------------------------------------

class TestNavItem:
    def setup_method(self):
        self.command = MagicMock()
        self.item = NavItem(MagicMock(), "ECG", "Electrocardiogram", self.command)

    def test_command_stored(self):
        assert self.item.command is self.command

    def test_on_click_calls_command(self):
        self.item._on_click(MagicMock())
        self.command.assert_called_once()

    def test_set_active_true_configures_widgets(self):
        self.item.set_active(True)
        self.item.container.configure.assert_called()
        self.item.text_frame.configure.assert_called()

    def test_set_active_false_configures_widgets(self):
        self.item.set_active(False)
        self.item.container.configure.assert_called()

    def test_indicator_configured_on_active(self):
        self.item.set_active(True)
        self.item.indicator.configure.assert_called()

    def test_indicator_configured_on_inactive(self):
        self.item.set_active(False)
        self.item.indicator.configure.assert_called()

    def test_title_and_subtitle_labels_configured_on_active(self):
        self.item.set_active(True)
        self.item.title_label.configure.assert_called()
        self.item.subtitle_label.configure.assert_called()


# ---------------------------------------------------------------------------
# CyVitalApp
# ---------------------------------------------------------------------------

class TestCyVitalApp:
    def setup_method(self):
        self.module = _make_mock_module()
        self.definition = _make_mock_definition(module=self.module)
        self.app, self.root, self.scope = _make_app([self.definition])

    # --- Initialisation ---

    def test_initial_sensor_key(self):
        assert self.app.current_sensor_key == "test"

    def test_initial_module_is_factory_result(self):
        assert self.app.current_module is self.module

    def test_scope_setup_called_on_first_sensor(self):
        self.module.setup_scope.assert_called_once_with(self.scope)

    def test_canvas_set_for_module_with_figure(self):
        assert self.app.canvas is not None

    def test_sensor_definition_registered(self):
        assert "test" in self.app.sensor_definitions

    def test_nav_item_registered(self):
        assert "test" in self.app.nav_items

    # --- set_sensor ---

    def test_set_sensor_same_key_is_noop(self):
        count_before = self.definition.module_factory.call_count
        self.app.set_sensor("test")
        assert self.definition.module_factory.call_count == count_before

    def test_set_sensor_unknown_key_does_not_change_current(self):
        self.app.set_sensor("nonexistent")
        assert self.app.current_sensor_key == "test"

    def test_set_sensor_switches_module(self):
        mod2 = _make_mock_module()
        def2 = _make_mock_definition(key="other", module=mod2)
        app, _, scope = _make_app([self.definition, def2])
        app.set_sensor("other")
        assert app.current_sensor_key == "other"
        assert app.current_module is mod2

    def test_set_sensor_cleans_up_previous_module(self):
        mod2 = _make_mock_module()
        def2 = _make_mock_definition(key="other", module=mod2)
        app, _, _ = _make_app([self.definition, def2])
        prev = app.current_module
        app.set_sensor("other" if app.current_sensor_key == "test" else "test")
        prev.cleanup.assert_called()

    def test_set_sensor_setup_scope_type_error_disables_streaming(self):
        mod2 = _make_mock_module()
        mod2.setup_scope.side_effect = TypeError("bad args")
        def2 = _make_mock_definition(key="err", module=mod2)
        app, _, _ = _make_app([self.definition, def2])
        app.set_sensor("err")
        assert mod2.supports_streaming is False

    def test_set_sensor_stream_not_connected_when_no_streaming(self):
        mod2 = _make_mock_module(supports_streaming=False)
        def2 = _make_mock_definition(key="off", module=mod2)
        app, _, _ = _make_app([self.definition, def2])
        app.set_sensor("off")
        # log_status_var.set should have been called with "Stream not connected"
        app.log_status_var.set.assert_called()

    # --- _render_sensor_content ---

    def test_render_with_figure_sets_canvas(self):
        self.app._render_sensor_content()
        assert self.app.canvas is not None

    def test_render_without_figure_sets_placeholder(self):
        self.app.current_module.get_figure.return_value = None
        self.app._render_sensor_content()
        assert self.app.canvas is None
        assert self.app.placeholder_label is not None

    def test_render_with_placeholder_message_uses_it(self):
        self.app.current_module.get_figure.return_value = None
        self.app.current_module.get_placeholder_message.return_value = "No device"
        self.app._render_sensor_content()
        assert self.app.placeholder_label is not None

    def test_render_destroys_existing_canvas_widget(self):
        old = MagicMock()
        self.app.canvas_widget = old
        self.app._render_sensor_content()
        old.destroy.assert_called_once()

    def test_render_destroys_existing_placeholder(self):
        old = MagicMock()
        self.app.placeholder_label = old
        self.app._render_sensor_content()
        old.destroy.assert_called_once()

    def test_render_no_module_falls_back_to_default_message(self):
        self.app.current_module = None
        self.app._render_sensor_content()
        assert self.app.placeholder_label is not None

    # --- _configure_controls_for_sensor ---

    def test_configure_controls_no_module_returns_early(self):
        self.app.current_module = None
        self.app._configure_controls_for_sensor()  # must not raise

    def test_configure_controls_export_supported_enables_button(self):
        self.app.current_module.supports_export = True
        self.app._configure_controls_for_sensor()
        self.app.export_btn.configure.assert_called()

    def test_configure_controls_export_not_supported_disables_button(self):
        self.app.current_module.supports_export = False
        self.app._configure_controls_for_sensor()
        self.app.export_btn.configure.assert_called()

    def test_configure_controls_streaming_with_figure_enables_toggle(self):
        self.app.current_module.supports_streaming = True
        self.app.current_module.get_figure.return_value = MagicMock()
        self.app._configure_controls_for_sensor()
        self.app.toggle_btn.configure.assert_called()

    def test_configure_controls_no_streaming_disables_toggle(self):
        self.app.current_module.supports_streaming = False
        self.app._configure_controls_for_sensor()
        self.app.toggle_btn.configure.assert_called()

    # --- _attach_button_hover ---

    def test_attach_button_hover_default_registers_callbacks(self):
        button = MagicMock()
        captured = {}
        button.bind.side_effect = lambda event, cb: captured.update({event: cb})
        self.app._attach_button_hover(button)
        assert "<Enter>" in captured
        assert "<Leave>" in captured

    def test_attach_button_hover_enter_callback_configures(self):
        button = MagicMock()
        captured = {}
        button.bind.side_effect = lambda event, cb: captured.update({event: cb})
        self.app._attach_button_hover(button)
        captured["<Enter>"](MagicMock())
        button.configure.assert_called()

    def test_attach_button_hover_leave_callback_configures(self):
        button = MagicMock()
        captured = {}
        button.bind.side_effect = lambda event, cb: captured.update({event: cb})
        self.app._attach_button_hover(button)
        captured["<Leave>"](MagicMock())
        button.configure.assert_called()

    def test_attach_button_hover_emphasis_registers_callbacks(self):
        button = MagicMock()
        captured = {}
        button.bind.side_effect = lambda event, cb: captured.update({event: cb})
        self.app._attach_button_hover(button, emphasis=True)
        captured["<Enter>"](MagicMock())
        captured["<Leave>"](MagicMock())
        button.configure.assert_called()

    # --- _stop_animation ---

    def test_stop_animation_with_animation_stops_it(self):
        anim = MagicMock()
        self.app.animation = anim
        self.app.animation_running = True
        self.app._stop_animation()
        anim.event_source.stop.assert_called_once()
        assert self.app.animation is None
        assert self.app.animation_running is False

    def test_stop_animation_without_animation_is_noop(self):
        self.app.animation = None
        self.app.animation_running = True
        self.app._stop_animation()
        assert self.app.animation_running is False

    # --- _start_animation ---

    def test_start_animation_no_module_returns_early(self):
        self.app.current_module = None
        self.app._start_animation()  # must not raise

    def test_start_animation_no_streaming_returns_early(self):
        self.app.current_module.supports_streaming = False
        self.app._start_animation()  # must not raise

    def test_start_animation_no_figure_returns_early(self):
        self.app.current_module.get_figure.return_value = None
        self.app._start_animation()  # must not raise

    def test_start_animation_with_canvas_creates_animation(self):
        with patch("gui.tkGui.FuncAnimation") as mock_anim_cls:
            self.app._start_animation()
        mock_anim_cls.assert_called_once()
        assert self.app.animation is not None

    def test_start_animation_focus_set_exception_handled(self):
        """If get_tk_widget().focus_set() raises, the except branch is taken."""
        self.app.canvas.get_tk_widget.return_value.focus_set.side_effect = Exception("no focus")
        with patch("gui.tkGui.FuncAnimation"):
            self.app._start_animation()  # must not raise

    def test_start_animation_no_canvas_prints_failure(self, capsys):
        self.app.canvas = None
        with patch("gui.tkGui.FuncAnimation") as mock_anim_cls:
            self.app._start_animation()
        out = capsys.readouterr().out
        assert "canvas failure" in out
        mock_anim_cls.assert_called_once()

    # --- _update_frame ---

    def test_update_frame_no_module_returns_empty_tuple(self):
        self.app.current_module = None
        assert self.app._update_frame(0) == tuple()

    def test_update_frame_calls_module_update(self):
        self.app._update_frame(0)
        self.app.current_module.update.assert_called_with(self.scope)

    def test_update_frame_returns_artists_from_update(self):
        artists = (MagicMock(),)
        self.app.current_module.update.return_value = SensorUpdate(
            primary_value="x", artists=artists
        )
        result = self.app._update_frame(0)
        assert result == artists

    def test_update_frame_returns_empty_tuple_when_no_artists(self):
        self.app.current_module.update.return_value = SensorUpdate()
        result = self.app._update_frame(0)
        assert result == tuple()

    # --- _apply_sensor_update ---

    def test_apply_sensor_update_sets_primary(self):
        self.app._apply_sensor_update(SensorUpdate(primary_value="99"))
        self.app.primary_value_var.set.assert_called_with("99")

    def test_apply_sensor_update_sets_secondary(self):
        self.app._apply_sensor_update(SensorUpdate(secondary_value="88"))
        self.app.secondary_value_var.set.assert_called_with("88")

    def test_apply_sensor_update_sets_log(self):
        self.app._apply_sensor_update(SensorUpdate(log_message="hello"))
        self.app.log_status_var.set.assert_called_with("hello")

    def test_apply_sensor_update_none_values_not_set(self):
        self.app.primary_value_var.set.reset_mock()
        self.app._apply_sensor_update(SensorUpdate())
        self.app.primary_value_var.set.assert_not_called()

    def test_apply_sensor_update_draws_canvas(self):
        self.app._apply_sensor_update(SensorUpdate())
        self.app.canvas.draw_idle.assert_called()

    def test_apply_sensor_update_no_canvas_does_not_raise(self):
        self.app.canvas = None
        self.app._apply_sensor_update(SensorUpdate())  # must not raise

    # --- toggle_animation ---

    def test_toggle_animation_pause_stops_animation(self):
        anim = MagicMock()
        self.app.animation = anim
        self.app.animation_running = True
        self.app.toggle_animation()
        anim.event_source.stop.assert_called_once()
        assert self.app.animation_running is False

    def test_toggle_animation_pause_calls_module_pause(self):
        self.app.animation = MagicMock()
        self.app.animation_running = True
        self.app.toggle_animation()
        self.app.current_module.pause.assert_called_once()

    def test_toggle_animation_play_sets_running(self):
        self.app.animation_running = False
        self.app.animation = None
        with patch("gui.tkGui.FuncAnimation"):
            self.app.toggle_animation()
        assert self.app.animation_running is True

    def test_toggle_animation_play_no_streaming_returns_early(self):
        self.app.animation_running = False
        self.app.current_module.supports_streaming = False
        self.app.toggle_animation()
        assert self.app.animation_running is False

    def test_toggle_animation_play_no_module_returns_early(self):
        self.app.animation_running = False
        self.app.current_module = None
        self.app.toggle_animation()
        assert self.app.animation_running is False

    def test_toggle_animation_play_start_fails_returns_early(self):
        """_start_animation doesn't set animation (no figure) → early return."""
        self.app.animation_running = False
        self.app.animation = None
        self.app.current_module.get_figure.return_value = None
        self.app.toggle_animation()
        assert self.app.animation_running is False

    def test_toggle_animation_play_existing_animation_skips_start(self):
        existing = MagicMock()
        self.app.animation = existing
        self.app.animation_running = False
        with patch("gui.tkGui.FuncAnimation") as mock_cls:
            self.app.toggle_animation()
        mock_cls.assert_not_called()
        assert self.app.animation_running is True

    # --- _shift_history ---

    def test_shift_history_calls_draw_idle_when_shifted(self):
        self.app.current_module.shift_history_window.return_value = True
        self.app._shift_history(1)
        self.app.canvas.draw_idle.assert_called()

    def test_shift_history_no_draw_when_not_shifted(self):
        self.app.current_module.shift_history_window.return_value = False
        canvas = MagicMock()
        self.app.canvas = canvas
        self.app._shift_history(-1)
        canvas.draw_idle.assert_not_called()

    def test_shift_history_no_canvas_does_not_raise(self):
        self.app.current_module.shift_history_window.return_value = True
        self.app.canvas = None
        self.app._shift_history(1)  # must not raise

    # --- export_data ---

    def test_export_data_with_path_logs_destination(self):
        self.app.current_module.save_data.return_value = "/tmp/data.xlsx"
        self.app.export_data()
        self.app.log_status_var.set.assert_called_with("Data exported: /tmp/data.xlsx")

    def test_export_data_no_path_logs_generic_message(self):
        self.app.current_module.save_data.return_value = None
        self.app.export_data()
        self.app.log_status_var.set.assert_called_with("Data exported.")

    def test_export_data_no_module_does_not_raise(self):
        self.app.current_module = None
        self.app.export_data()

    def test_export_data_no_export_support_skips_save(self):
        self.app.current_module.supports_export = False
        self.app.export_data()
        self.app.current_module.save_data.assert_not_called()

    # --- shutdown ---

    def test_shutdown_stops_animation_and_calls_cleanup(self):
        anim = MagicMock()
        self.app.animation = anim
        self.app.animation_running = True
        self.app.shutdown()
        anim.event_source.stop.assert_called()
        self.app.current_module.cleanup.assert_called()

    def test_shutdown_calls_scope_reset_and_close(self):
        self.app.shutdown()
        self.scope.reset.assert_called()
        self.scope.close.assert_called()

    def test_shutdown_scope_exception_is_swallowed(self):
        self.scope.reset.side_effect = RuntimeError("no device")
        self.app.shutdown()  # must not raise

    def test_shutdown_no_module_does_not_raise(self):
        self.app.current_module = None
        self.app.shutdown()

    def test_shutdown_quits_and_destroys_root(self):
        self.app.shutdown()
        self.root.quit.assert_called()
        self.root.destroy.assert_called()

    # --- Register multiple sensors ---

    def test_register_two_sensors_both_in_dicts(self):
        d1 = _make_mock_definition(key="a")
        d2 = _make_mock_definition(key="b")
        app, _, _ = _make_app([d1, d2])
        assert "a" in app.sensor_definitions
        assert "b" in app.sensor_definitions
        assert "a" in app.nav_items
        assert "b" in app.nav_items


# ---------------------------------------------------------------------------
# CyVitalApp: empty sensor list (edge case used by main() tests)
# ---------------------------------------------------------------------------

class TestCyVitalAppNoSensors:
    def test_init_with_no_sensors_does_not_raise(self):
        root = MagicMock()
        scope = MagicMock()
        with patch("gui.tkGui.DEFAULT_SENSORS", []):
            app = CyVitalApp(root, scope)
        assert app.current_sensor_key is None
        assert app.current_module is None


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

class TestMain:
    def test_main_fake_scope_does_not_raise(self):
        with patch("gui.tkGui.DEFAULT_SENSORS", []):
            main(["--fake-scope"])

    def test_main_fake_scope_with_seed(self):
        with patch("gui.tkGui.DEFAULT_SENSORS", []):
            main(["--fake-scope", "--fake-seed", "42"])

    def test_main_default_scope_uses_scope_class(self):
        with patch("gui.tkGui.DEFAULT_SENSORS", []):
            with patch("gui.tkGui.Scope") as mock_cls:
                main([])
        mock_cls.assert_called_once()

    def test_main_keyboard_interrupt_is_handled(self):
        _tk_mock.Tk.return_value.mainloop.side_effect = KeyboardInterrupt()
        try:
            with patch("gui.tkGui.DEFAULT_SENSORS", []):
                main(["--fake-scope"])
        finally:
            _tk_mock.Tk.return_value.mainloop.side_effect = None

    def test_main_registers_wm_delete_window_protocol(self):
        captured: dict = {}

        def _capture(event, cb):
            captured[event] = cb

        _tk_mock.Tk.return_value.protocol.side_effect = _capture
        try:
            with patch("gui.tkGui.DEFAULT_SENSORS", []):
                main(["--fake-scope"])
        finally:
            _tk_mock.Tk.return_value.protocol.side_effect = None

        assert "WM_DELETE_WINDOW" in captured

    def test_main_on_closing_callback_shuts_down(self):
        captured: dict = {}

        def _capture(event, cb):
            captured[event] = cb

        _tk_mock.Tk.return_value.protocol.side_effect = _capture
        try:
            with patch("gui.tkGui.DEFAULT_SENSORS", []):
                main(["--fake-scope"])
        finally:
            _tk_mock.Tk.return_value.protocol.side_effect = None

        # Invoke the on_closing closure — must not raise.
        captured["WM_DELETE_WINDOW"]()
