from imgui_bundle import imgui, immapp

def gui():
    imgui.text("Hello, world!")

immapp.run(
    gui_function=gui,  # The Gui function to run
    window_title="CyVitals 1.0.0",  # the window title
    window_restore_previous_geometry=True  # Restore window position and size from previous run
)