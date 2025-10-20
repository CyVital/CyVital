from oscilloscope.Scope import Scope
from plots.ReactionPlot import ReactionPlot
from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    try:
        scope = Scope()
        plot_manager = ReactionPlot()

        def update(frame):
            samples = scope.get_samples()
            t_axis = scope.get_time_axis(samples)
            return plot_manager.update_plot(t_axis, samples)

        ani = FuncAnimation(plot_manager.fig, update, interval=50, blit=False)
        plt.tight_layout()
        plt.show()

    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        try:
            scope.reset()
            scope.close()
        except:
            pass
