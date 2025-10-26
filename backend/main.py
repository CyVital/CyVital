import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

for path in (PROJECT_ROOT, BASE_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

ESSENTIAL_DEPS = [
    ("setuptools", "pkg_resources"),
    ("pip", "pip"),
]

MAIN_DEPENDENCIES = [
    ("dwfpy", "dwfpy"),
    ("scipy", "scipy"),
    ("numpy", "numpy"),
    ("imgui-bundle", "imgui_bundle"),
    ("matplotlib", "matplotlib"),
]


def install_dependencies() -> bool:
    print("[!] Checking system essentials...")
    missing_essentials = []
    for package, import_name in ESSENTIAL_DEPS:
        try:
            __import__(import_name)
            print(f"[!] {package} already installed")
        except ImportError:
            missing_essentials.append(package)

    if missing_essentials:
        print(f"[!] Installing system essentials: {', '.join(missing_essentials)}")
        try:
            subprocess.check_call([sys.executable, "-m", "ensurepip", "--upgrade"])
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "--user", *missing_essentials]
            )
        except subprocess.CalledProcessError:
            print("[!] Failed to install essential dependencies. Please try manually:")
            print(f"    {sys.executable} -m ensurepip --upgrade")
            return False

    print("\n[!] Checking application dependencies...")
    missing_deps = []
    for package, import_name in MAIN_DEPENDENCIES:
        try:
            __import__(import_name)
            print(f"[!] {package} already installed")
        except ImportError:
            missing_deps.append(package)

    if not missing_deps:
        return True

    print(f"\n[!] Missing dependencies: {', '.join(missing_deps)}")
    print("[!] Attempting installation...")

    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--user", *missing_deps]
        )
        print("[!] Installation successful!")
        return True
    except subprocess.CalledProcessError:
        print("\n[!] Failed to install dependencies. Please try manually:")
        print(f"    {sys.executable} -m pip install --user {' '.join(missing_deps)}")
        return False


def main() -> int:
    banner = """
    #############################################
    #                 ISU CyVitals              #
    #############################################
    """
    print(banner)

    if not install_dependencies():
        return 1

    print("\n[!] Launching GUI...")
    try:
        from backend.gui.imguiHandler import main as gui_main
    except ImportError as exc:
        print(f"[!] Critical import error: {exc}")
        print("Possible solutions:")
        print("1. Check if backend/gui/imguiHandler.py exists")
        print("2. Verify the directory structure")
        print("3. Check file permissions")
        return 1

    gui_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
