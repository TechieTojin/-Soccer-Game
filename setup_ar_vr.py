import os
import sys
import subprocess
import platform
import urllib.request
import zipfile
import time

def print_header(text):
    """Print a formatted header"""
    width = 70
    print("\n" + "=" * width)
    print(" " * ((width - len(text)) // 2) + text)
    print("=" * width + "\n")

def check_python_version():
    """Check if Python version is compatible"""
    print("Checking Python version...")
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 8):
        print(f"Error: This project requires Python 3.8+ (you have {major}.{minor})")
        print("Please upgrade your Python installation.")
        return False
    print(f"✓ Python version {major}.{minor} is compatible")
    return True

def install_dependencies():
    """Install required Python packages"""
    print_header("Installing Dependencies")
    
    packages = [
        "numpy",
        "scipy",
        "matplotlib",
        "pillow",
        "pygame",
        "pyopengl",
        "opencv-python",
        "opencv-contrib-python",
    ]
    
    if platform.system() == "Windows":
        packages.append("tk")
    else:
        packages.append("python-tk")
    
    for package in packages:
        print(f"Installing {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✓ Successfully installed {package}")
        except subprocess.CalledProcessError:
            print(f"× Failed to install {package}")
            return False
    
    print("\nAll packages installed successfully!")
    return True

def download_dataset():
    """Download the Barcelona dataset if not already present"""
    print_header("Downloading Dataset")
    
    # Check if dataset already exists
    if os.path.exists("barcelona") and os.path.exists(os.path.join("barcelona", "barcelona", "images")):
        print("Dataset already exists. Skipping download.")
        return True
    
    # Dataset URL
    url = "http://grail.cs.washington.edu/projects/soccer/barcelona.zip"
    
    print(f"Downloading dataset from {url}...")
    print("This may take some time depending on your internet connection.")
    
    try:
        # Download the zip file
        zip_path = "barcelona.zip"
        print("Downloading... (this might take a while)")
        urllib.request.urlretrieve(url, zip_path)
        
        # Extract the zip file
        print("Extracting files...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall("barcelona")
        
        # Remove the zip file
        os.remove(zip_path)
        
        print("✓ Dataset downloaded and extracted successfully!")
        return True
    
    except Exception as e:
        print(f"× Failed to download dataset: {e}")
        print("You can download it manually from:")
        print(url)
        print("and extract it to a folder named 'barcelona' in the project directory.")
        return False

def download_aruco_markers():
    """Generate ArUco markers for AR experience"""
    print_header("Setting up AR Markers")
    
    try:
        import cv2
        import cv2.aruco as aruco
        import numpy as np
        
        # Create markers directory if it doesn't exist
        markers_dir = "ar_markers"
        if not os.path.exists(markers_dir):
            os.makedirs(markers_dir)
        
        # Generate and save ArUco markers (ID 0-4)
        print("Generating ArUco markers...")
        aruco_dict = aruco.Dictionary_get(aruco.DICT_4X4_50)
        
        for marker_id in range(5):
            # Generate the marker
            marker_size = 700
            marker_img = np.zeros((marker_size, marker_size), dtype=np.uint8)
            marker_img = aruco.drawMarker(aruco_dict, marker_id, marker_size, marker_img, 1)
            
            # Add a white border around the marker
            border_size = 50
            bordered_img = np.ones((marker_size + 2*border_size, marker_size + 2*border_size), dtype=np.uint8) * 255
            bordered_img[border_size:border_size+marker_size, border_size:border_size+marker_size] = marker_img
            
            # Save the marker
            marker_path = os.path.join(markers_dir, f"marker_{marker_id}.png")
            cv2.imwrite(marker_path, bordered_img)
        
        print(f"✓ ArUco markers generated and saved to {markers_dir}/")
        print("Print these markers to use with the AR experience.")
        
        # Create an HTML file with usage instructions
        with open(os.path.join(markers_dir, "README.html"), "w") as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>AR Markers Instructions</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #2c3e50; }
        .marker { border: 1px solid #ccc; margin: 10px; display: inline-block; }
        .instructions { background-color: #f8f9fa; padding: 15px; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>AR Markers for Soccer AR Experience</h1>
    
    <div class="instructions">
        <h2>How to use</h2>
        <ol>
            <li>Print the markers on regular paper (preferably letter/A4 size)</li>
            <li>Cut out the markers leaving some white border</li>
            <li>Place the marker with ID 0 on a flat surface</li>
            <li>Run the AR experience: <code>python ar_soccer_experience.py</code></li>
            <li>Point your webcam at the marker</li>
            <li>The 3D soccer field should appear on top of the marker</li>
        </ol>
        
        <h2>Tips</h2>
        <ul>
            <li>Ensure good lighting conditions for better marker detection</li>
            <li>Keep the marker flat and avoid bending</li>
            <li>The bigger the printed marker, the better the detection</li>
            <li>Press 'A' to toggle AR mode on/off</li>
        </ul>
    </div>
    
    <h2>Available Markers</h2>
    <p>The main marker used is Marker 0, but others can be used for future extensions.</p>
</body>
</html>""")
        
        return True
    
    except Exception as e:
        print(f"× Failed to generate AR markers: {e}")
        print("You can still run the application, but AR functionality might be limited.")
        return False

def create_launcher():
    """Create a launcher file"""
    print_header("Creating Launcher")
    
    # Check which OS we're on
    if platform.system() == "Windows":
        # Create a batch file for Windows
        with open("launch_soccer_experience.bat", "w") as f:
            f.write('@echo off\n')
            f.write('echo Starting Soccer AR/VR Experience...\n')
            f.write('python modern_interface.py\n')
            f.write('if %ERRORLEVEL% NEQ 0 (\n')
            f.write('  echo Error starting application\n')
            f.write('  pause\n')
            f.write(')\n')
        
        print("✓ Launcher created: launch_soccer_experience.bat")
    
    else:
        # Create a shell script for Linux/Mac
        with open("launch_soccer_experience.sh", "w") as f:
            f.write('#!/bin/bash\n')
            f.write('echo "Starting Soccer AR/VR Experience..."\n')
            f.write('python3 modern_interface.py\n')
        
        # Make the shell script executable
        os.chmod("launch_soccer_experience.sh", 0o755)
        
        print("✓ Launcher created: launch_soccer_experience.sh")
    
    return True

def main():
    """Main function"""
    print_header("Soccer AR/VR Experience Setup")
    
    print("This script will set up all dependencies for the Soccer AR/VR Experience.")
    print("It will install required Python packages, download the dataset,")
    print("generate AR markers, and create a launcher.")
    
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    input()
    
    # Check Python version
    if not check_python_version():
        print("\nSetup failed. Please fix the issues and try again.")
        return
    
    # Install dependencies
    if not install_dependencies():
        print("\nSome dependencies could not be installed.")
        print("You may need to install them manually.")
    
    # Download dataset
    download_dataset()
    
    # Download ArUco markers
    download_aruco_markers()
    
    # Create launcher
    create_launcher()
    
    print_header("Setup Complete!")
    print("You can now run the application using:")
    
    if platform.system() == "Windows":
        print("  - Double-click launch_soccer_experience.bat")
        print("  - OR run: python modern_interface.py")
    else:
        print("  - Run: ./launch_soccer_experience.sh")
        print("  - OR run: python3 modern_interface.py")
    
    print("\nEnjoy the Soccer AR/VR Experience!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup canceled.")
    except Exception as e:
        print(f"\n\nAn error occurred: {e}")
    
    if platform.system() == "Windows":
        print("\nPress Enter to exit...")
        input() 