import xlsxwriter

class PlotManager:

    def __init__(self):
        pass

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
        workbook = xlsxwriter.Workbook(filename)
        worksheet = workbook.add_worksheet()
        for i in range(0, len(self.selected_samples)):
            worksheet.write(i, 0, self.selected_times[i])
            worksheet.write(i, 1, self.selected_samples[i])
        workbook.close()