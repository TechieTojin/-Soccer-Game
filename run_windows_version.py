import os
import sys
import subprocess
import time

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Display the project header"""
    clear_screen()
    print("\n" + "=" * 80)
    print(" " * 28 + "SOCCER ON YOUR TABLETOP")
    print(" " * 32 + "Windows Version")
    print("=" * 80 + "\n")

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import numpy
        import matplotlib
        import PIL
        import pygame
        import OpenGL.GL
        return True
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("\nPlease install all required dependencies:")
        print("py -m pip install numpy matplotlib pillow pygame pyopengl")
        return False

def check_data():
    """Check if barcelona dataset is available"""
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'barcelona', 'barcelona')
    if not os.path.exists(data_dir):
        print("Dataset not found!")
        print("Please download and extract the barcelona.zip dataset.")
        print("\nDownload command:")
        print("Invoke-WebRequest -Uri \"http://grail.cs.washington.edu/projects/soccer/barcelona.zip\" -OutFile \"barcelona.zip\"")
        print("\nExtract command:")
        print("Expand-Archive -Path barcelona.zip -DestinationPath barcelona")
        return False
    return True

def display_menu():
    """Display the main menu"""
    print("Please select an option:\n")
    print("1. Run Image Viewer (displays soccer frames)")
    print("2. Run 3D Field Visualization (displays 3D soccer field)")
    print("3. Read Documentation")
    print("4. Exit")
    print("\nEnter your choice [1-4]: ", end="")

def run_script(script_name):
    """Run the specified Python script"""
    clear_screen()
    print(f"Starting {script_name}...\n")
    try:
        subprocess.run([sys.executable, script_name], check=True)
    except subprocess.CalledProcessError:
        print(f"\nError running {script_name}. Please check the console output above.")
    except KeyboardInterrupt:
        print("\nScript was terminated by user.")
    
    print("\nPress Enter to return to the main menu...")
    input()

def show_documentation():
    """Display the documentation"""
    clear_screen()
    try:
        with open("README_WINDOWS.md", "r") as f:
            content = f.read()
        print(content)
    except FileNotFoundError:
        print("Documentation file not found.")
    
    print("\nPress Enter to return to the main menu...")
    input()

def main():
    """Main function"""
    print_header()
    
    # Check dependencies
    if not check_dependencies():
        print("\nPress Enter to exit...")
        input()
        return
    
    # Check for dataset
    if not check_data():
        print("\nPress Enter to continue anyway or Ctrl+C to exit...")
        try:
            input()
        except KeyboardInterrupt:
            return
    
    while True:
        print_header()
        display_menu()
        
        try:
            choice = input().strip()
            
            if choice == '1':
                run_script('run_soccer_on_table.py')
            elif choice == '2':
                run_script('soccer3d_viewer.py')
            elif choice == '3':
                show_documentation()
            elif choice == '4':
                print("\nExiting Soccer On Your Tabletop - Windows Version...")
                break
            else:
                print("\nInvalid choice. Please enter a number between 1 and 4.")
                time.sleep(1.5)
        except KeyboardInterrupt:
            print("\n\nExiting Soccer On Your Tabletop - Windows Version...")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProgram terminated by user.")
        sys.exit(0) 