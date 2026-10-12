"""Unified launcher for the Soccer AR/VR Experience.

Gives access to every mode that exists in this repository:

    1. 2D Soccer Game        -> soccer_game.py
    2. 3D Field Viewer       -> soccer3d_viewer.py
    3. AR Prototype          -> ar_soccer_experience.py
    4. VR Stereo Prototype   -> vr_soccer_experience.py
    5. Dataset Image Viewer  -> run_soccer_on_table.py

Usage:
    python run_windows_version.py              # interactive menu
    python run_windows_version.py --mode 2d    # launch one mode directly
    python run_windows_version.py --list       # list modes and exit

All script paths are resolved relative to this file, so the launcher works
regardless of the current working directory. (Audit findings B3, B18)
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# Directory containing this launcher - all modes are resolved against it.
BASE_DIR = Path(__file__).resolve().parent

# mode key -> (menu label, script filename, short description)
MODES = {
    "2d": ("2D Soccer Game", "soccer_game.py",
           "Playable top-down match with physics, stamina and scoring"),
    "3d": ("3D Field Viewer", "soccer3d_viewer.py",
           "Orbiting OpenGL view of the pitch and formations"),
    "ar": ("AR Prototype", "ar_soccer_experience.py",
           "EXPERIMENTAL - webcam + printed ArUco marker (no physical-marker test yet)"),
    "vr": ("VR Stereo Prototype", "vr_soccer_experience.py",
           "EXPERIMENTAL - side-by-side stereo preview, no headset support"),
    "markers": ("Generate AR Markers", "tools/make_markers.py",
                "Write printable ArUco markers to ar_markers/ (needed for AR)"),
    "viewer": ("Dataset Image Viewer", "run_soccer_on_table.py",
               "Browse the Barcelona dataset frames (needs the dataset)"),
}

# Order used by the interactive menu
MENU_ORDER = ["2d", "3d", "ar", "vr", "markers", "viewer"]


def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Display the project header"""
    clear_screen()
    print("\n" + "=" * 80)
    print(" " * 26 + "SOCCER AR/VR EXPERIENCE")
    print(" " * 34 + "Launcher")
    print("=" * 80 + "\n")


def check_dependencies():
    """Check that the core runtime dependencies are importable.

    Returns a list of missing package names (empty when everything is present).
    PyOpenGL and OpenCV are only needed by some modes, so a missing one is
    reported but does not block the launcher.
    """
    missing = []
    for module_name, package_name in [
        ("pygame", "pygame"),
        ("numpy", "numpy"),
        ("cv2", "opencv-contrib-python"),
        ("OpenGL.GL", "PyOpenGL"),
        ("PIL", "Pillow"),
        ("matplotlib", "matplotlib"),
    ]:
        try:
            __import__(module_name)
        except ImportError:
            missing.append(package_name)
    return missing


def script_path(mode):
    """Absolute path to the script implementing `mode`."""
    return BASE_DIR / MODES[mode][1]


def run_mode(mode, pause=True):
    """Launch the script for `mode` as a child process.

    Returns True when the script exited cleanly.
    """
    label, filename, _ = MODES[mode]
    path = script_path(mode)

    if not path.exists():
        print(f"\nError: {filename} was not found at {path}")
        if pause:
            input("\nPress Enter to continue...")
        return False

    clear_screen()
    print(f"Starting {label} ({filename})...\n")
    ok = False
    try:
        # cwd is set to the project root so modes that use relative asset
        # paths behave the same however the launcher was started.
        subprocess.run([sys.executable, str(path)], check=True, cwd=str(BASE_DIR))
        ok = True
    except subprocess.CalledProcessError as e:
        print(f"\n{label} exited with an error (code {e.returncode}).")
        print("See the console output above for details.")
    except KeyboardInterrupt:
        print("\nTerminated by user.")
    except OSError as e:
        print(f"\nCould not start {filename}: {e}")

    if pause:
        print("\nPress Enter to return to the main menu...")
        input()
    return ok


def display_menu():
    """Display the main menu"""
    print("Please select an option:\n")
    for i, mode in enumerate(MENU_ORDER, start=1):
        label, _, description = MODES[mode]
        print(f"{i}. {label}")
        print(f"   {description}")
    print(f"{len(MENU_ORDER) + 1}. Exit")
    print(f"\nEnter your choice [1-{len(MENU_ORDER) + 1}]: ", end="")


def interactive_menu():
    """Run the interactive launcher menu"""
    while True:
        print_header()
        display_menu()

        try:
            choice = input().strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nExiting Soccer AR/VR Experience...")
            return

        if choice == str(len(MENU_ORDER) + 1):
            print("\nExiting Soccer AR/VR Experience...")
            return

        if choice.isdigit() and 1 <= int(choice) <= len(MENU_ORDER):
            run_mode(MENU_ORDER[int(choice) - 1])
        else:
            print(f"\nInvalid choice. Please enter a number between 1 and "
                  f"{len(MENU_ORDER) + 1}.")
            time.sleep(1.5)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Launcher for the Soccer AR/VR Experience.")
    parser.add_argument(
        "--mode", choices=sorted(MODES),
        help="Launch a mode directly instead of showing the menu.")
    parser.add_argument(
        "--list", action="store_true",
        help="List the available modes and exit.")
    parser.add_argument(
        "--skip-checks", action="store_true",
        help="Skip the dependency check on start-up.")
    args = parser.parse_args()

    if args.list:
        for mode in MENU_ORDER:
            label, filename, description = MODES[mode]
            print(f"{mode:<7} {label:<22} {filename:<26} {description}")
        return 0

    if not args.skip_checks:
        missing = check_dependencies()
        if missing:
            print("Warning: missing packages: " + ", ".join(missing))
            print("Some modes will not start. Install them with:")
            print("    pip install -r requirements.txt\n")

    if args.mode:
        # Direct launch: no menu, no "press Enter", propagate the exit status.
        return 0 if run_mode(args.mode, pause=False) else 1

    print_header()
    interactive_menu()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nProgram terminated by user.")
        sys.exit(0)
