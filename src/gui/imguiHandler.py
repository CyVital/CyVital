import sys
import os
import subprocess
import threading
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Optional
from imgui_bundle import hello_imgui, imgui

DEMO = os.getenv("CYVITAL_DEMO") == "1" #Demo Flag - run the artificial demos

SRC_DIR = Path(__file__).resolve().parent.parent
SENSORS_DIR = SRC_DIR / "sensors"
DEMO_SCRIPT_PATH = SENSORS_DIR / "_demo_sensor.py"

if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))
log_lock = threading.Lock()
log_messages = []

SENSOR_CONFIGS = {
    "ECG": {
        "title": "Heart Rate Monitoring",
        "script": "HeartRate.py",
        "demo_arg": "ECG",
    },
    "Pulse OX": {
        "title": "Pulse Oxymeter",
        "script": "PulseOx.py",
        "demo_arg": "Pulse Ox",
    },
    "EMG": {
        "title": "Electromyography",
        "script": "Emg.py",
        "demo_arg": "EMG",
    },
    "Reaction": {
        "title": "Reaction",
        "script": "Reaction.Py",
        "demo_arg": "Reaction",
    },
}


class AppState:
    def __init__(self):
        self.current_view = "ECG"
        self.heart_process = None
        self.output_thread = None
        self.active_sensor = None
        self.selectedMUX = None # 0, 1, 2, 3

def add_to_logs(message: str):
    with log_lock:
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_messages.append(f"[{timestamp}]: {message}")
        if len(log_messages) > 1000:
            log_messages.pop(0)

def custom_log_gui():
    imgui.begin_child("Logs", imgui.ImVec2(0, 0), imgui.ChildFlags_.borders)
    imgui.push_style_color(imgui.Col_.text, imgui.get_color_u32((1.0, 1.0, 1.0, 1.0)))
    with log_lock:
        for msg in log_messages:
            imgui.text_unformatted(msg)
    imgui.pop_style_color()
    imgui.end_child()

def read_output(process):
    stdout = process.stdout
    if not stdout:
        return

    for line in stdout:
        if not line:
            break
        add_to_logs(line.rstrip())


def is_sensor_running(app_state: AppState, sensor_key: Optional[str] = None) -> bool:
    process = app_state.heart_process
    if not process:
        return False

    if process.poll() is not None:
        stop_sensor(app_state)
        return False

    if sensor_key is None:
        return True

    return app_state.active_sensor == sensor_key


def stop_sensor(app_state: AppState) -> bool:
    process = app_state.heart_process
    if not process:
        app_state.active_sensor = None
        return False

    try:
        if process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        else:
            process.wait()
    finally:
        stdout = getattr(process, "stdout", None)
        if stdout and not stdout.closed:
            with suppress(Exception):
                stdout.close()
        stderr = getattr(process, "stderr", None)
        if stderr and not stderr.closed:
            with suppress(Exception):
                stderr.close()

    thread = app_state.output_thread
    if thread and thread.is_alive() and thread is not threading.current_thread():
        thread.join(timeout=1.0)

    app_state.heart_process = None
    app_state.output_thread = None
    app_state.active_sensor = None
    return True


def start_sensor(app_state: AppState, sensor_key: str) -> bool:
    config = SENSOR_CONFIGS[sensor_key]

    if is_sensor_running(app_state):
        previous_sensor = app_state.active_sensor
        if stop_sensor(app_state) and previous_sensor:
            add_to_logs(f"Stopped {previous_sensor} before starting {sensor_key}")

    script_path = DEMO_SCRIPT_PATH if DEMO else SENSORS_DIR / config["script"]

    if not script_path.exists():
        raise FileNotFoundError(f"Sensor script not found: {script_path}")

    cmd = [sys.executable, str(script_path)]
    if DEMO and config.get("demo_arg"):
        cmd.append(config["demo_arg"])

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    app_state.heart_process = process
    app_state.active_sensor = sensor_key

    output_thread = threading.Thread(
        target=read_output,
        args=(process,),
        daemon=True
    )
    output_thread.start()

    app_state.output_thread = output_thread
    return True


def render_sensor_view(app_state: AppState, sensor_key: str):
    config = SENSOR_CONFIGS[sensor_key]

    imgui.text_colored((0.4, 0.8, 1.0, 1.0), config["title"])
    imgui.separator()

    running_any_sensor = is_sensor_running(app_state)
    running_this_sensor = running_any_sensor and app_state.active_sensor == sensor_key
    running_other_sensor = running_any_sensor and not running_this_sensor

    if running_this_sensor:
        if imgui.button("Stop Monitoring", (-1, 90)):
            if stop_sensor(app_state):
                add_to_logs(f"{sensor_key} monitoring stopped")
        imgui.same_line()
        imgui.text_colored((0, 1, 0, 1), "Status: Running")
    else:
        if imgui.button("Start Monitoring", (-1, 90)):
            try:
                start_sensor(app_state, sensor_key)
                add_to_logs(f"{sensor_key} monitoring started")
            except Exception as e:
                add_to_logs(f"Error starting {sensor_key}: {str(e)}")
        imgui.same_line()
        if running_other_sensor:
            other_sensor = app_state.active_sensor or "another sensor"
            imgui.text_colored((1, 0.65, 0, 1), f"Status: Running ({other_sensor})")
        else:
            imgui.text_colored((1, 0, 0, 1), "Status: Stopped")

def show_sidebar(app_state: AppState):
    imgui.begin_child("Sidebar", imgui.ImVec2(-1, -1), imgui.ChildFlags_.borders)
    views = ["ECG", "Pulse OX", "EMG", "Reaction"]
    for view in views:
        if imgui.button(view, imgui.ImVec2(-1, 90)):
            app_state.current_view = view
    imgui.end_child()


def show_ecg_view(app_state: AppState):
    render_sensor_view(app_state, "ECG")


def show_emg_view(app_state: AppState):
    render_sensor_view(app_state, "EMG")

def show_pulseOx_view(app_state: AppState):
    render_sensor_view(app_state, "Pulse OX")


def show_reaction_view(app_state: AppState):
    render_sensor_view(app_state, "Reaction")


def show_main_content(app_state: AppState):
    try:
        if app_state.current_view == "ECG":
            show_ecg_view(app_state)
        elif app_state.current_view == "Pulse OX":
            show_pulseOx_view(app_state)
        elif app_state.current_view == "EMG":
            show_emg_view(app_state)
        elif app_state.current_view == "Reaction":
            show_reaction_view(app_state)
    except Exception as e:
        add_to_logs(f"Error in {app_state.current_view} view: {str(e)}")

def create_docking_layout(app_state: AppState) -> hello_imgui.DockingParams:
    docking_params = hello_imgui.DockingParams()
    
    # CREATE SPACING OF MENU
    split_left = hello_imgui.DockingSplit()
    split_left.initial_dock = "MainDockSpace"
    split_left.new_dock = "SidebarSpace"
    split_left.direction = imgui.Dir.left
    split_left.ratio = 0.2

    split_bottom = hello_imgui.DockingSplit()
    split_bottom.initial_dock = "MainDockSpace"
    split_bottom.new_dock = "LogsSpace"
    split_bottom.direction = imgui.Dir.down
    split_bottom.ratio = 0.25

    docking_params.docking_splits = [split_left, split_bottom]

    # DOCKABLE
    sidebar_window = hello_imgui.DockableWindow()
    sidebar_window.label = "Sensors"
    sidebar_window.dock_space_name = "SidebarSpace"
    sidebar_window.gui_function = lambda: show_sidebar(app_state)

    main_window = hello_imgui.DockableWindow()
    main_window.label = "Dock"
    main_window.dock_space_name = "MainDockSpace"
    main_window.gui_function = lambda: show_main_content(app_state)

    logs_window = hello_imgui.DockableWindow()
    logs_window.label = "Logs"
    logs_window.dock_space_name = "LogsSpace"
    logs_window.gui_function = custom_log_gui

    docking_params.dockable_windows = [sidebar_window, main_window, logs_window]
    
    return docking_params

def main():
    app_state = AppState()
    
    runner_params = hello_imgui.RunnerParams()
    runner_params.app_window_params.window_title = "ISU CyVitals Beta"

    if DEMO:
        runner_params.app_window_params.window_title += " [DEMO]"

    runner_params.app_window_params.window_geometry.size = (800, 600)
    
    # Configure docking layout
    runner_params.docking_params = create_docking_layout(app_state)
    runner_params.imgui_window_params.default_imgui_window_type = (
        hello_imgui.DefaultImGuiWindowType.provide_full_screen_dock_space
    )
    
    # Basic menu bar
    runner_params.imgui_window_params.show_menu_view_themes = False
    runner_params.imgui_window_params.show_menu_bar = True
    runner_params.imgui_window_params.show_menu_app = False
    
    hello_imgui.run(runner_params)

if __name__ == "__main__":
    main()
