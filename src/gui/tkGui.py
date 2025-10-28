import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
import sys
import os
from oscilloscope.Scope import Scope
from plots.ReactionPlot import ReactionPlot


sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    try:
        scope = Scope()
        reaction_plot_manager = ReactionPlot()
        root = tk.Tk()
        root.title("CyVital")

        # Embed matplotlib in Tkinter
        canvas = FigureCanvasTkAgg(reaction_plot_manager.fig, master=root)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        def update(frame):
            samples = scope.get__reaction_samples()
            t_axis = scope.get_reaction_time_axis(samples)
            return reaction_plot_manager.update_plot(t_axis, samples)
        
        def save_reaction():
            reaction_plot_manager.save_data('reaction_data.xlsx')

        ani = FuncAnimation(reaction_plot_manager.fig, update, interval=50, blit=False)

        def stop_animation():
            ani.event_source.stop()

        # buttons
        stopBtn = tk.Button(root, text="Stop", command = stop_animation)
        stopBtn.pack()
        saveBtn = tk.Button(root, text="Save", command = save_reaction)
        saveBtn.pack()

        def on_closing():
            reaction_plot_manager._close_plot()
            root.quit()
            root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_closing)
        root.mainloop()

    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        try:
            scope.reset()
            scope.close()
        except:
            pass

if __name__ == "__main__":
    main()