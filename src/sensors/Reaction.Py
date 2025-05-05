import time
import random
import numpy as np
import dwfpy as dwf
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# Constants
sample_rate = 10000
buffer_size = 512
threshold_voltage = 2.5  
mux_channel = 1

# Global state
reaction_times = []
cue_active = False
reaction_start = None
signal_time = 0.0
last_cue_time = time.time()
random_delay = random.uniform(2, 5)

# Setup plot
fig, (ax_signal, ax_reaction) = plt.subplots(2, 1, figsize=(10, 6))
fig.suptitle("Reaction Time Tracker")

line_signal, = ax_signal.plot([], [], lw=1)
ax_signal.set_ylim(0, 3.5)
ax_signal.set_ylabel("Button Voltage (V)")
ax_signal.set_xlim(0, buffer_size / sample_rate)
ax_signal.grid(True)

reaction_scatter = ax_reaction.scatter([], [])
ax_reaction.set_ylim(0, 1000)
ax_reaction.set_xlim(0, 10)
ax_reaction.set_ylabel("Reaction Time (ms)")
ax_reaction.set_xlabel("Trial")
ax_reaction.grid(True)

cue_text = ax_signal.text(0.02, 0.9, '', transform=ax_signal.transAxes, fontsize=14, color='red')


   

try:
    with dwf.Device() as device:
        print(f"Connected to {device.name} ({device.serial_number})")

        device.analog_io[0][1].value = 3.3
        device.analog_io[0][0].value = True
        device.analog_io.master_enable = True

        device.digital_io.reset()
        for i in range(4):
            device.digital_io.channels[i].enabled = True
            device.digital_io.channels[i].output_state = bool((1 >> i) & 1)
        device.digital_io.configure()
        scope = device.analog_input
        scope[0].setup(range=3.3)
        scope.scan_shift(sample_rate=sample_rate, buffer_size=buffer_size, configure=True, start=True)

        def update(frame):
            global cue_active, reaction_start, signal_time
            global last_cue_time, random_delay, reaction_times

            scope.read_status(read_data=True)
            samples = np.array(scope.channels[0].get_data())
            signal_time += len(samples) / sample_rate

            t_axis = np.linspace(signal_time - len(samples) / sample_rate, signal_time, len(samples))
            line_signal.set_data(t_axis, samples)
            ax_signal.set_xlim(t_axis[0], t_axis[-1])

            now = time.time()

            # Start cue if delay has passed
            if not cue_active and (now - last_cue_time > random_delay):
                cue_active = True
                reaction_start = now
                cue_text.set_text("GO!")

            # Detect button press
            if cue_active and np.any(samples > threshold_voltage):
                rt_ms = (time.time() - reaction_start) * 1000
                reaction_times.append(rt_ms)
                cue_active = False
                last_cue_time = time.time()
                random_delay = random.uniform(2, 5)

                cue_text.set_text(f"Reaction: {rt_ms:.1f} ms (Avg: {np.mean(reaction_times):.1f} ms)")

                ax_reaction.clear()
                ax_reaction.set_ylim(0, 1000)
                ax_reaction.set_xlim(0, max(10, len(reaction_times)))
                ax_reaction.set_ylabel("Reaction Time (ms)")
                ax_reaction.set_xlabel("Trial")
                ax_reaction.grid(True)
                ax_reaction.scatter(range(1, len(reaction_times) + 1), reaction_times, color='blue')

            return line_signal, cue_text

        ani = FuncAnimation(fig, update, interval=50, blit=False)
        plt.tight_layout()
        plt.show()

except KeyboardInterrupt:
    print("Stopped by user.")
finally:
    try:
        device.digital_io.reset()
        device.digital_io.configure()
    except:
        pass
