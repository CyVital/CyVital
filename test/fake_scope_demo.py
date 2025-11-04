"""Manual/dev harness to exercise the GUI with synthetic scope data.

Launches the CyVital app with FakeScope and automatically toggles pause/resume
and export actions so the workflow can be tested without hardware.
"""

from __future__ import annotations

import os
import sys
import threading
import time
import tkinter as tk

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "src"))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from gui import tkGui
from oscilloscope.FakeScope import FakeScope


def run_demo() -> None:
    scope = FakeScope()
    root = tk.Tk()
    app = tkGui.CyVitalApp(root, scope)

    def drive_controls() -> None:
        time.sleep(2)
        root.after(0, app.toggle_animation)
        time.sleep(2)
        root.after(0, app.toggle_animation)
        time.sleep(2)
        root.after(0, app.export_data)
        time.sleep(2)
        root.after(0, app.shutdown)

    threading.Thread(target=drive_controls, daemon=True).start()
    root.mainloop()


if __name__ == "__main__":
    run_demo()
