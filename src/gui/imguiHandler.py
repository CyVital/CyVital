import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) 
from imgui_bundle import hello_imgui, imgui, implot
from sensors.HeartRate import HeartRateMonitor
from typing import List
from datetime import datetime

class AppState:
    def __init__(self):
        self.current_view = "Home"
        self.counter = 0
        self.input_text = "Type here"
        self.heart_monitor = HeartRateMonitor()
        self.device_error = ""
        self.discovered_devices = []
        self.selected_device_index = -1
        self.last_discovery_time = 0

def show_sidebar(app_state: AppState):
    imgui.begin_child("Sidebar", imgui.ImVec2(-1, -1), imgui.ChildFlags_.borders)
    views = ["ECG", "Blood O2", "EMG"]
    for view in views:
        if imgui.button(view, imgui.ImVec2(-1, 90)):
            app_state.current_view = view
    imgui.end_child()

log_messages = []
def add_to_logs(message: str):
    log_messages.append(f"[{datetime.now().strftime('%H:%M:%S')}]: {message}")
    if len(log_messages) > 1000:
        log_messages.pop(0)

def custom_log_gui():
    imgui.begin_child("Logs", imgui.ImVec2(0, 0), imgui.ChildFlags_.borders)
    imgui.push_style_color(imgui.Col_.text, imgui.get_color_u32((1.0, 1.0, 1.0, 1.0)))
    for msg in log_messages:
        imgui.text_unformatted(msg)
    imgui.pop_style_color()
    imgui.end_child()

def show_device_selection(app_state: AppState):
    add_to_logs("Scanning for devices...")
    
    # Auto-refresh every 2 seconds
    if time.time() - app_state.last_discovery_time > 2:
        try:
            app_state.discovered_devices = HeartRateMonitor.discover_devices()
            add_to_logs(f"Found {len(app_state.discovered_devices)} devices")
        except Exception as e:
            add_to_logs(f"Discovery error: {str(e)}")
        app_state.last_discovery_time = time.time()
    
    imgui.text_colored(imgui.ImVec4(0.5, 0.8, 1.0, 1.0), "Available Devices:")
    imgui.separator()
    
    if imgui.button("Refresh Devices"):
        app_state.discovered_devices = HeartRateMonitor.discover_devices()
        add_to_logs("Device list refreshed")
    
    # Style var stack fix
    imgui.push_style_var(imgui.StyleVar_.item_spacing, imgui.ImVec2(0, 5))
    try:
        for idx, device in enumerate(app_state.discovered_devices):
            label = f"{device.get('name', 'Unknown')} ({device.get('serial', 'N/A')})"
            if imgui.selectable(label, app_state.selected_device_index == idx)[0]:
                app_state.selected_device_index = idx
    finally:
        imgui.pop_style_var()  # Ensured pop
    
    if app_state.selected_device_index >= 0:
        imgui.spacing()
        if imgui.button("Connect to Selected Device", imgui.ImVec2(-1, 40)):
            try:
                selected = app_state.discovered_devices[app_state.selected_device_index]
                app_state.heart_monitor.stop()
                app_state.heart_monitor.start(selected.get('serial'))
                app_state.device_error = ""
                add_to_logs(f"Connected to {selected.get('name', 'device')}")
            except Exception as e:
                app_state.device_error = str(e)
                add_to_logs(f"Connection failed: {str(e)}")

def show_ecg_view(app_state: AppState):
    if not app_state.heart_monitor.running:
        show_device_selection(app_state)
        return
    
    # Device status display
    imgui.text_colored(imgui.ImVec4(0.4, 0.8, 1.0, 1.0), "Connected Device:")
    imgui.same_line()
    
    if app_state.device_error:
        imgui.text_colored(imgui.ImVec4(1.0, 0.0, 0.0, 1.0), f"● {app_state.device_error}")
        return
    
    try:
        monitor = app_state.heart_monitor
        status_color = imgui.ImVec4(0.0, 1.0, 0.0, 1.0) if monitor.running else imgui.ImVec4(1.0, 0.0, 0.0, 1.0)
        status_text = "● Monitoring" if monitor.running else "● Disconnected"
        
        imgui.text_colored(status_color, status_text)
        imgui.same_line()
        
        if monitor.device_info:
            info = f"{monitor.device_info.get('name', 'Device')} | SN: {monitor.device_info.get('serial', 'N/A')}"
            imgui.text(info)

        # Plotting section
        imgui.spacing()
        imgui.text_wrapped("Real-time ECG Monitoring")
        imgui.separator()
        
        if implot.begin_plot("ECG Signal", size=(-1, 300)):
            try:
                if monitor.raw_samples:
                    times = [t - monitor.start_time for t in monitor.time_values[-500:]]
                    implot.plot_line("ECG", times, monitor.raw_samples[-500:])
            finally:
                implot.end_plot()
        
        # BPM display
        imgui.spacing()
        if monitor.current_bpm > 30:
            imgui.text(f"Heart Rate: {monitor.current_bpm:.1f} BPM")
        else:
            imgui.text("Heart Rate: --")

        # Reset controls
        if imgui.button("Reset Monitoring", imgui.ImVec2(120, 40)):
            try:
                monitor.stop()
                app_state.heart_monitor = HeartRateMonitor()
                if monitor.device_info:
                    app_state.heart_monitor.start(monitor.device_info.get('serial'))
                add_to_logs("Monitoring reset")
            except Exception as e:
                app_state.device_error = f"Reset Failed: {str(e)}"
        imgui.same_line()
        imgui.text("Press to reset monitoring session")

    except Exception as e:
        app_state.device_error = str(e)
        add_to_logs(f"Device Error: {app_state.device_error}")
        app_state.heart_monitor.stop()

def show_bloodoxygen_view(app_state: AppState):
    imgui.text_wrapped("Application Settings")
    imgui.separator()
    _, app_state.input_text = imgui.input_text("Text Input", app_state.input_text, 256)

def show_emg_view(app_state: AppState):
    imgui.text_wrapped("Info View")
    imgui.separator()
    imgui.text(f"Counter value: {app_state.counter}")
    imgui.text(f"Input text: {app_state.input_text}")
    add_to_logs(app_state.input_text)

def show_main_content(app_state: AppState):
    try:
        current_view = app_state.current_view
        
        if current_view != "ECG" and app_state.heart_monitor.running:
            app_state.heart_monitor.stop()
            add_to_logs("Monitoring stopped")
        
        if current_view == "ECG":
            app_state.heart_monitor.update()
            show_ecg_view(app_state)
        elif current_view == "Blood O2":
            show_bloodoxygen_view(app_state)
        elif current_view == "EMG":
            show_emg_view(app_state)
            
    except Exception as e:
        app_state.device_error = str(e)
        add_to_logs(f"System Error: {app_state.device_error}")
        app_state.heart_monitor.stop()

def create_docking_layout(app_state: AppState) -> hello_imgui.DockingParams:
    docking_params = hello_imgui.DockingParams()
    
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
    implot.create_context()
    app_state = AppState()
    
    runner_params = hello_imgui.RunnerParams()
    runner_params.app_window_params.window_title = "ISU CyVitals Beta"
    runner_params.app_window_params.window_geometry.size = (1280, 720)
    
    runner_params.docking_params = create_docking_layout(app_state)
    runner_params.imgui_window_params.default_imgui_window_type = (
        hello_imgui.DefaultImGuiWindowType.provide_full_screen_dock_space
    )
    
    runner_params.imgui_window_params.show_menu_bar = True
    runner_params.imgui_window_params.show_menu_view_themes = False
    runner_params.imgui_window_params.show_menu_app = False
    
    hello_imgui.run(runner_params)
    
    implot.destroy_context()
    app_state.heart_monitor.stop()

if __name__ == "__main__":
    main()