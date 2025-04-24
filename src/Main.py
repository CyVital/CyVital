import sys
import os
import subprocess

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def install_dependencies():
    # First check for essential setup tools
    essential_deps = [
        ('setuptools', 'pkg_resources'),
        ('pip', 'pip')
    ]
    
    # Main application dependencies
    main_dependencies = [
        ('dwfpy', 'dwfpy'),
        ('scipy', 'scipy'),
        ('numpy', 'numpy'),
        ('imgui-bundle', 'imgui_bundle'),
        ('matplotlib', 'matplotlib')
    ]

    print("[!] Checking system essentials...")
    missing_essentials = []
    for package, import_name in essential_deps:
        try:
            __import__(import_name)
            print(f"[!] ✓ {package} already installed")
        except ImportError:
            missing_essentials.append(package)
    
    if missing_essentials:
        print(f"[!] Installing system essentials: {', '.join(missing_essentials)}")
        try:
            subprocess.check_call([sys.executable, "-m", "ensurepip", "--upgrade"])
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", *missing_essentials])
        except subprocess.CalledProcessError:
            print("[!] Failed to install essential dependencies. Please try manually:")
            print(f"  {sys.executable} -m ensurepip --upgrade")
            return False

    missing_deps = []
    print("\n[!] Checking application dependencies...")
    for package, import_name in main_dependencies:
        try:
            __import__(import_name)
            print(f"[!] ✓ {package} already installed")
        except ImportError:
            missing_deps.append(package)
    
    if not missing_deps:
        return True
    
    print(f"\n[!] Missing dependencies: {', '.join(missing_deps)}")
    print("[!] Attempting installation...")
    
    try:
        subprocess.check_call([
            sys.executable,
            "-m", "pip", "install",
            "--user",
            *missing_deps
        ])
        print("[!] Installation successful!")
        return True
    except subprocess.CalledProcessError:
        print("\n[!] Failed to install dependencies. Please try manually:")
        print(f"  {sys.executable} -m pip install --user {' '.join(missing_deps)}")
        return False

if __name__ == "__main__":
    print("""
    #############################################
    #                 ISU CyVitals              #
    #############################################
    """)
    
    if not install_dependencies():
        sys.exit(1)
    
    print("\n[!] Launching GUI...")
    try:
        # Correct import path based on typical structure
        from gui.imguiHandler import main as gui_main
        gui_main()
    except ImportError as e:
        print(f"[!] Critical import error: {e}")
        print("Possible solutions:")
        print("1. Check if gui/imguiHandler.py exists")
        print("2. Verify the directory structure")
        print("3. Check file permissions")
        sys.exit(1)