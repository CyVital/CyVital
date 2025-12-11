import xlsxwriter
from matplotlib.patches import Rectangle
import numpy as np
from pathlib import Path

class PlotManager:

    def __init__(self):
        self.selected_samples = []
        self.selected_times = []
        self.selection_start = None
        self.selection_rect = None

    def zoom_around_cursor(self, ax):
        def on_scroll(event):
            if event.inaxes != ax:
                return

            base_scale = 1.1
            cur_xlim = ax.get_xlim()
            xdata = event.xdata  # Cursor x-position

            if event.button == 'up':
                scale_factor = 1 / base_scale
            elif event.button == 'down':
                scale_factor = base_scale
            else:
                scale_factor = 1

            left = xdata - (xdata - cur_xlim[0]) * scale_factor
            right = xdata + (cur_xlim[1] - xdata) * scale_factor

            ax.set_xlim([left, right])
            ax.figure.canvas.draw_idle()

        ax.figure.canvas.mpl_connect('scroll_event', on_scroll)

    def save_data(self, filename):
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        workbook = xlsxwriter.Workbook(filename)
        worksheet = workbook.add_worksheet()
        for i in range(0, len(self.selected_samples)):
            worksheet.write(i, 0, self.selected_times[i])
            worksheet.write(i, 1, self.selected_samples[i])
        workbook.close()
        return filename

    def on_press(self, event, ax):
        if event.button == 1:
            if event.inaxes == ax:
                self.selection_start = event.xdata
                print(f"Selection started at x = {self.selection_start}")
                if self.selection_rect:
                    self.selection_rect.remove()
                    self.selection_rect = None
        elif self.selection_rect:
            self.selection_rect.remove()
            self.selection_rect = None

    def on_release(self, event, ax, time, samples):
        if event.inaxes == ax and self.selection_start and event.button == 1:
            self.selection_end = event.xdata
            print(f"Selection ended at x = {self.selection_end}")

            # Get full height of the plot
            y_min, y_max = ax.get_ylim()

            # Calculate rectangle position and width
            x0 = min(self.selection_start, self.selection_end)
            width = abs(self.selection_end - self.selection_start)

            # # Extract selected data
            full_time_array = np.array(time)
            full_samples_array = np.array(samples)
            mask = (time >= x0) & (time <= x0 + width)
            self.selected_times = full_time_array[mask]
            self.selected_samples = full_samples_array[mask]

            # Draw rectangle spanning full height
            self.selection_rect = Rectangle((x0, y_min), width, y_max - y_min,
                                    linewidth=1, edgecolor='blue', facecolor='lightblue', alpha=0.5)
            ax.add_patch(self.selection_rect)

            return mask

    def on_scroll(self, event):
        if self.selection_rect:
            self.selection_rect.remove()
            self.selection_rect = None 

    def _create_workbook(self, filename: str):
        destination = self._prepare_export_path(filename)
        workbook = xlsxwriter.Workbook(str(destination))
        return workbook, destination
    
    def _prepare_export_path(self, filename: str) -> Path:
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        return downloads_dir / filename