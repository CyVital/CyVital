from oscilloscope import Scope
from plots import ReactionPlot
from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt

if __name__ == "__main__":
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
