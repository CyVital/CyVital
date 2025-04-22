import sys
import os
import subprocess
import threading
from datetime import datetime
from imgui_bundle import hello_imgui, implot, imgui
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
log_lock = threading.Lock()
log_messages = []

class AppState:
    def __init__(self):
        self.current_view = "Home"
        self.heart_process = None
        self.output_thread = None

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
    while True:
        line = process.stdout.readline()
        if not line:
            break
        add_to_logs(line.strip())

def show_sidebar(app_state: AppState):
    imgui.begin_child("Sidebar", imgui.ImVec2(-1, -1), imgui.ChildFlags_.borders)
    views = ["ECG", "Blood O2", "EMG"]
    for view in views:
        if imgui.button(view, imgui.ImVec2(-1, 90)):
            app_state.current_view = view
    imgui.end_child()

def show_ecg_view(app_state: AppState):
    imgui.text_colored((0.4, 0.8, 1.0, 1.0), "Heart Rate Monitoring")
    imgui.separator()
    
    process_running = app_state.heart_process and app_state.heart_process.poll() is None
    
    if process_running:
        if imgui.button("Stop Monitoring", (-1, 90)):
            app_state.heart_process.terminate()
            app_state.heart_process.wait()
            if app_state.output_thread:
                app_state.output_thread.join()
            app_state.heart_process = None
            add_to_logs("Monitoring stopped")
        imgui.same_line()
        imgui.text_colored((0, 1, 0, 1), "Status: Running")
    else:
        if imgui.button("Start Monitoring", (-1, 90)):
            try:
                app_state.heart_process = subprocess.Popen(
                    ["python", "sensors/HeartRate.py"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                app_state.output_thread = threading.Thread(
                    target=read_output,
                    args=(app_state.heart_process,),
                    daemon=True
                )
                app_state.output_thread.start()
                add_to_logs("Monitoring started")
            except Exception as e:
                add_to_logs(f"Error starting process: {str(e)}")
        imgui.same_line()
        imgui.text_colored((1, 0, 0, 1), "Status: Stopped")

def show_main_content(app_state: AppState):
    try:
        if app_state.current_view == "ECG":
            show_ecg_view(app_state)
        elif app_state.current_view == "Blood O2":
            imgui.text_wrapped("Blood Oxygen Monitoring (Not implemented)")
        elif app_state.current_view == "EMG":
            imgui.text_wrapped("EMG Monitoring (Not implemented)")
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