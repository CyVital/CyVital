import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Cursor
from matplotlib.patches import Rectangle
from mpl_interactions import ioff, panhandler, zoom_factory

fig, ax = plt.subplots()
ax.plot(np.random.rand(10), 'o-')

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

plt.show()