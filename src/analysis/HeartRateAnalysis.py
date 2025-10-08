import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Cursor
from matplotlib.patches import Rectangle
from mpl_interactions import ioff, panhandler, zoom_factory
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Create the main window
root = tk.Tk()
root.title("IR Plot GUI")

def on_closing():
    plt.close(fig)
    root.quit()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

#measurements
delta_t = tk.Label(root, text="Delta t: ", font=("Arial", 14))
delta_t.pack(pady=10)

#matplotlib
fig, ax = plt.subplots()
time_ms = [
    0, 10, 20, 30, 40, 50, 60, 70, 80, 90,
    100, 110, 120, 130, 140, 150, 160, 170, 180, 190,
    200, 210, 220, 230, 240, 250, 260, 270, 280, 290,
    300, 310, 320, 330, 340, 350, 360, 370, 380, 390,
    400, 410, 420, 430, 440, 450, 460, 470, 480, 490
]

ir_values = [
    52000, 52100, 52300, 52600, 53000,  
    52500, 52200, 52000, 51900, 51850,
    51900, 52100, 52400, 52800, 53300,  
    52700, 52300, 52000, 51800, 51750,
    51850, 52050, 52350, 52750, 53250,  
    52650, 52250, 51950, 51750, 51650,
    51750, 51950, 52250, 52650, 53150,  
    52550, 52150, 51850, 51650, 51550,
    51650, 51850, 52150, 52550, 53050,  
    52450, 52050, 51750, 51550, 51450
]


ax.plot(time_ms, ir_values)

# Store the coordinates of the selection
selection_start = None
selection_rect = None

cursor = Cursor(ax, useblit=True, color='red', linewidth=2)
disconnect_zoom = zoom_factory(ax)
pan_handler = panhandler(fig)

def on_press(event):
    global selection_start, selection_rect
    if event.inaxes == ax:
        selection_start = event.xdata
        print(f"Selection started at x = {selection_start}")
        if selection_rect:
            selection_rect.remove()
            selection_rect = None

def on_release(event):
    global selection_start, selection_rect
    if event.inaxes == ax and selection_start is not None:
        selection_end = event.xdata
        print(f"Selection ended at x = {selection_end}")

        delta_t_num = selection_end - selection_start

        delta_t.config(text="Delta t: " + str(delta_t_num))

        # Get full height of the plot
        y_min, y_max = ax.get_ylim()

        # Calculate rectangle position and width
        x0 = min(selection_start, selection_end)
        width = abs(selection_end - selection_start)

        # Draw rectangle spanning full height
        selection_rect = Rectangle((x0, y_min), width, y_max - y_min,
                                   linewidth=1, edgecolor='blue', facecolor='lightblue', alpha=0.5)
        ax.add_patch(selection_rect)
        fig.canvas.draw()

        selection_start = None  # Reset for next selection

fig.canvas.mpl_connect('button_press_event', on_press)
fig.canvas.mpl_connect('button_release_event', on_release)

# Embed the plot in the Tkinter window
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.draw()
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

# Run the GUI loop
root.mainloop()
