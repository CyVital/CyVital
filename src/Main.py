import sys
import os
import subprocess

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("""
    #############################################
    #                 ISU CyVitals              #
    #############################################
    """)
    
    print("\n[!] Launching GUI...")
    try:
        # Correct import path based on typical structure
        from gui.tkGui import main as gui_main
        gui_main()
    except ImportError as e:
        print(f"[!] Critical import error: {e}")
        print("Possible solutions:")
        print("1. Check if gui/tkGui.py exists")
        print("2. Verify the directory structure")
        print("3. Check file permissions")
        sys.exit(1)