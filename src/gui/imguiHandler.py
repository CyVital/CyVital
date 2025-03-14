from imgui_bundle import hello_imgui, imgui
from typing import List

from datetime import datetime

# DEFINE APPSTATES
class AppState:
    current_view: str
    counter: int
    input_text: str

    def __init__(self):
        self.current_view = "Home"
        self.counter = 0
        self.input_text = "Type here"

# REQUIRED IMPORTS
from imgui_bundle import imgui  

def show_sidebar(app_state: AppState):
    imgui.begin_child("Sidebar", 
                     imgui.ImVec2(-1, -1),  
                     imgui.ChildFlags_.borders)  
    views = ["ECG", "Blood O2", "EMG"] 
    for view in views:
        if imgui.button(view, imgui.ImVec2(-1, 50)):
            app_state.current_view = view
            current_view = view
    imgui.end_child()

# CUSTOMARY FUNCTIONS
log_messages = []
def add_to_logs(message: str):
    log_messages.append("[" + datetime.now().strftime("%H:%M:%S") + "]: " + message)

    # REMOVE OLD LOGS
    if len(log_messages) > 1000:  
        log_messages.pop(0) 

def custom_log_gui():
    imgui.begin_child("Logs", imgui.ImVec2(0, 0), imgui.ChildFlags_.borders)
    
    imgui.push_style_color(imgui.Col_.text, imgui.get_color_u32((1.0, 1.0, 1.0, 1.0)))  # Set neutral white color
    for msg in log_messages:
        imgui.text_unformatted(msg)
    imgui.pop_style_color()

    imgui.end_child()
    
# AVAILABLE VIEWS FOR SENSORS
def show_ecg_view(app_state: AppState):
    imgui.text_wrapped("Welcome to the Home View!")
    imgui.separator()
    _, app_state.counter = imgui.slider_int("Counter", app_state.counter, 0, 100)
    if imgui.button("Reset Counter"):
        app_state.counter = 0

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

# SWAP TO NEW VIEW USING APPSTATE
def show_main_content(app_state: AppState):
    if app_state.current_view == "ECG":
        show_ecg_view(app_state)
    elif app_state.current_view == "Blood O2":
        show_bloodoxygen_view(app_state)
    elif app_state.current_view == "EMG":
        show_emg_view(app_state)

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