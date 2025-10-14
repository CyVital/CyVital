import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Cursor
from matplotlib.patches import Rectangle
from mpl_interactions import ioff, panhandler, zoom_factory
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import csv
from scipy.signal import butter, filtfilt, find_peaks

# Create the main window
root = tk.Tk()
root.title("IR Plot GUI")

def on_closing():
    plt.close(fig)
    root.quit()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

#measurements
delta_t_label = tk.Label(root, text="Delta t: ", font=("Arial", 14))
delta_t_label.pack(pady=10)

ptp_label = tk.Label(root, text="PTP: ", font=("Arial", 14))
ptp_label.pack(pady=10)

bpm_label = tk.Label(root, text="BPM: ", font=("Arial", 14))
bpm_label.pack(pady=10)

rate_mean_label = tk.Label(root, text="Rate Mean: ", font=("Arial", 14))
rate_mean_label.pack(pady=10)

#matplotlib
fig, ax = plt.subplots()

time_ms = []
red_values = []
ir_values = []

# with open('pulse_data.csv', 'r') as f:
#     reader = csv.reader(f)
#     next(reader)  # Skip header row
#     for row in reader:
#         time_ms.append(float(row[1]))
#         red_values.append(float(row[2]))
#         ir_values.append(float(row[3]))


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

time_ms = np.array(time_ms)
ir_values = np.array(ir_values)

fs = 10  # sampling rate (Hz)
min_peak_distance = int(0.5 * fs) 
# --- Band‑pass filter design --- 
lowcut, highcut = 0.7, 4.0  # Hz
nyq = fs / 2.0
b, a = butter(2, [lowcut/nyq, highcut/nyq], btype='band')

def filtered_ir(buf):
    return filtfilt(b, a, np.array(buf))

def estimate_bpm(ir_buf):
    x = filtered_ir(ir_buf)
    # require peaks with some prominence to avoid noise
    prom = np.std(x) * 0.5
    peaks, _ = find_peaks(x, distance=min_peak_distance, prominence=prom)
    if len(peaks) >= 5:
        # use last 4 intervals (5 peaks → 4 intervals)
        intervals = np.diff(peaks[-5:])
        avg_period = np.mean(intervals)
        return 60.0 * fs / avg_period
    return None

def compute_rate_mean(ir_buf): #is this a proper rate mean calculation?
    x = filtered_ir(ir_buf)
    prom = np.std(x) * 0.5
    peaks, _ = find_peaks(x, distance=min_peak_distance, prominence=prom)
    if len(peaks) >= 2:
        intervals = np.diff(peaks)  # in samples
        rates = 60.0 * fs / intervals  # convert to BPM
        return np.mean(rates)
    return None

ax.plot(time_ms, ir_values)

# Store the coordinates of the selection
selection_start = None
selection_rect = None

cursor = Cursor(ax, useblit=True, color='red', linewidth=2)
disconnect_zoom = zoom_factory(ax)
# pan_handler = panhandler(fig)

# ax.text(0.05, 0.95, "delta t: ", fontsize=10, transform=ax.transAxes, verticalalignment='top')

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

        # Extract selected data
        mask = (time_ms >= x0) & (time_ms <= x0 + width)
        selected_times = time_ms[mask]
        selected_ir = ir_values[mask]

        # Draw rectangle spanning full height
        selection_rect = Rectangle((x0, y_min), width, y_max - y_min,
                                   linewidth=1, edgecolor='blue', facecolor='lightblue', alpha=0.5)
        ax.add_patch(selection_rect)
        fig.canvas.draw()

        if len(selected_ir) > 2:
            # Peak-to-Peak
            ptp = np.ptp(selected_ir)
            ptp_label.config(text="Peak-to-Peak: {:.2f}".format(ptp))

            #Delta t
            delta_t = selected_times[-1] - selected_times[0]
            delta_t_label.config(text="Delta t: " + str(delta_t))
        else:
            ptp_label.config(text="Peak-to-Peak: N/A")
            delta_t_label.config(text="Delta t: N/A")

        #BPM
        bpm = estimate_bpm(selected_ir)
        if bpm is not None:
            bpm_label.config(text="BPM: {:.0f}".format(bpm))
        else:
            bpm_label.config(text="BPM: N/A")

        #Rate Mean
        rate_mean = compute_rate_mean(selected_ir)
        if rate_mean is not None:
            rate_mean_label.config(text="Rate Mean: {:.2f}".format(rate_mean))
        else:
            rate_mean_label.config(text="Rate Mean: N/A")

        selection_start = None  # Reset for next selection

fig.canvas.mpl_connect('button_press_event', on_press)
fig.canvas.mpl_connect('button_release_event', on_release)

# Embed the plot in the Tkinter window
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.draw()
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

# Run the GUI loop
root.mainloop()
