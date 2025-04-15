import sys
import subprocess
import os
import platform

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
        ('glfw', 'glfw')
    ]

    # Check/install essential dependencies first
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
            subprocess.check_call([
                sys.executable, 
                "-m", "ensurepip", "--upgrade"
            ])
            subprocess.check_call([
                sys.executable, 
                "-m", "pip", "install", "--user", *missing_essentials
            ])
        except subprocess.CalledProcessError:
            print("[!] Failed to install essential dependencies. Please try:")
            print(f"  {sys.executable} -m ensurepip --upgrade")
            return False

    # Check for WaveForms SDK
    print("\n[!] Checking for WaveForms SDK...")
    dwf_path = "/Library/Frameworks/dwf.framework/dwf"
    if not os.path.exists(dwf_path):
        print("""[!] WaveForms SDK not found!
    Please download and install from:
    https://digilent.com/reference/software/waveforms/waveforms3
    The free version is sufficient.
    """)
        return False

    # Now check main dependencies
    try:
        from pkg_resources import DistributionNotFound
    except ImportError:
        print("[!] Failed to load package resources after installation")
        return False

    missing_deps = []
    print("\n[!] Checking application dependencies...")
    for package, import_name in main_dependencies:
        try:
            __import__(import_name)
            print(f"[!] ✓ {package} already installed")
        except (ImportError, DistributionNotFound):
            missing_deps.append(package)
    
    if not missing_deps:
        return True
    
    print(f"\n[!] Missing dependencies: {', '.join(missing_deps)}")
    print("[!] Attempting installation...")
    
    try:
        # Special handling for macOS binary installations
        env = os.environ.copy()
        if platform.system() == "Darwin":
            env["SYSTEM_VERSION_COMPAT"] = "0"
            
        subprocess.check_call([
            sys.executable, 
            "-m", "pip", "install",
            "--user",
            "--only-binary=:all:",
            *missing_deps
        ], env=env)
        
        print("[!] Installation successful!")
        return True
    except subprocess.CalledProcessError:
        print("\n[!] Failed to install dependencies. Please try manually:")
        mac_note = "SYSTEM_VERSION_COMPAT=0 " if platform.system() == "Darwin" else ""
        print(f"  {mac_note}{sys.executable} -m pip install --user --only-binary=:all: {' '.join(missing_deps)}")
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
        from gui.imguiHandler import main as gui_main
        gui_main()
    except ImportError as e:
        print(f"[!] Import error: {e}")
        sys.exit(1)