import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import webbrowser
from PIL import Image, ImageTk
import threading
import numpy as np
import cv2
from datetime import datetime

class ModernUI(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Soccer AR/VR Experience")
        self.geometry("1280x800")
        self.minsize(1024, 768)
        
        # Modern theme colors
        self.bg_color = "#121212"  # Dark background
        self.text_color = "#ffffff"
        self.accent_color = "#00ff88"  # Modern green
        self.button_color = "#1e1e1e"
        self.hover_color = "#2e2e2e"
        self.card_color = "#1e1e1e"
        
        # Configure the window
        self.configure(bg=self.bg_color)
        
        # Style configuration
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        
        # Configure the styles
        self.style.configure('TFrame', background=self.bg_color)
        self.style.configure('TLabel', background=self.bg_color, foreground=self.text_color, font=('Segoe UI', 10))
        self.style.configure('TButton', background=self.button_color, foreground=self.text_color, 
                            borderwidth=0, focusthickness=3, focuscolor=self.accent_color, font=('Segoe UI', 10))
        self.style.map('TButton', background=[('active', self.hover_color)])
        
        # Create main container
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Create header
        self.create_header()
        
        # Create main content area
        self.create_content_area()
        
        # Create status bar
        self.create_status_bar()
        
        # Check dependencies and data
        self.check_dependencies()
        self.check_data()
        
        # Initialize camera for AR preview
        self.init_camera()
        
        # Start camera preview thread
        self.camera_running = True
        self.camera_thread = threading.Thread(target=self.update_camera_preview, daemon=True)
        self.camera_thread.start()
    
    def create_header(self):
        """Create the modern header with logo and title"""
        header_frame = ttk.Frame(self.main_container)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Logo placeholder (you can add an actual logo image)
        logo_label = ttk.Label(header_frame, text="⚽", font=('Segoe UI', 36))
        logo_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Title and subtitle
        title_frame = ttk.Frame(header_frame)
        title_frame.pack(side=tk.LEFT)
        
        title_label = ttk.Label(title_frame, text="Soccer AR/VR Experience", 
                              font=('Segoe UI', 24, 'bold'), foreground=self.accent_color)
        title_label.pack(anchor=tk.W)
        
        subtitle_label = ttk.Label(title_frame, text="Experience soccer like never before", 
                                 font=('Segoe UI', 12), foreground=self.text_color)
        subtitle_label.pack(anchor=tk.W)
    
    def create_content_area(self):
        """Create the main content area with experience cards"""
        content_frame = ttk.Frame(self.main_container)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create experience cards
        self.create_experience_cards(content_frame)
        
        # Create preview area
        self.create_preview_area(content_frame)
    
    def create_experience_cards(self, parent):
        """Create modern experience cards"""
        cards_frame = ttk.Frame(parent)
        cards_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        
        # 2D Viewer Card
        self.create_card(cards_frame, "2D Viewer", "Watch soccer matches in high definition", 
                        "📺", self.run_2d_viewer)
        
        # 3D Field Card
        self.create_card(cards_frame, "3D Field", "Explore the soccer field in 3D", 
                        "🎮", self.run_3d_viewer)
        
        # AR Experience Card
        self.create_card(cards_frame, "AR Experience", "Bring soccer to your table", 
                        "📱", self.run_ar_viewer)
        
        # VR Experience Card
        self.create_card(cards_frame, "VR Experience", "Immerse yourself in the game", 
                        "👓", self.run_vr_viewer)
    
    def create_card(self, parent, title, description, icon, command):
        """Create a modern card with icon and description"""
        card = ttk.Frame(parent, style='Card.TFrame')
        card.pack(fill=tk.X, pady=5)
        
        # Card style
        self.style.configure('Card.TFrame', background=self.card_color)
        
        # Icon
        icon_label = ttk.Label(card, text=icon, font=('Segoe UI', 24))
        icon_label.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Content
        content_frame = ttk.Frame(card)
        content_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        title_label = ttk.Label(content_frame, text=title, 
                              font=('Segoe UI', 12, 'bold'), foreground=self.accent_color)
        title_label.pack(anchor=tk.W)
        
        desc_label = ttk.Label(content_frame, text=description, 
                             font=('Segoe UI', 9), wraplength=200)
        desc_label.pack(anchor=tk.W)
        
        # Button
        button = ttk.Button(card, text="Start", command=command)
        button.pack(side=tk.RIGHT, padx=10, pady=10)
    
    def create_preview_area(self, parent):
        """Create the preview area with camera feed"""
        preview_frame = ttk.Frame(parent)
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Preview label
        preview_label = ttk.Label(preview_frame, text="LIVE PREVIEW", 
                                font=('Segoe UI', 12, 'bold'), foreground=self.accent_color)
        preview_label.pack(pady=(0, 10))
        
        # Preview canvas
        self.preview_canvas = tk.Canvas(preview_frame, width=640, height=480, 
                                      bg=self.card_color, highlightthickness=0)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Controls frame
        controls_frame = ttk.Frame(preview_frame)
        controls_frame.pack(fill=tk.X, pady=10)
        
        # Camera controls
        self.create_camera_controls(controls_frame)
    
    def create_camera_controls(self, parent):
        """Create camera control buttons"""
        # Camera selection
        camera_label = ttk.Label(parent, text="Camera:")
        camera_label.pack(side=tk.LEFT, padx=5)
        
        self.camera_var = tk.StringVar(value="0")
        camera_menu = ttk.OptionMenu(parent, self.camera_var, "0", "0", "1", "2")
        camera_menu.pack(side=tk.LEFT, padx=5)
        
        # AR mode toggle
        self.ar_mode_var = tk.BooleanVar(value=True)
        ar_toggle = ttk.Checkbutton(parent, text="AR Mode", variable=self.ar_mode_var)
        ar_toggle.pack(side=tk.LEFT, padx=20)
        
        # Settings button
        settings_btn = ttk.Button(parent, text="⚙️", command=self.open_settings)
        settings_btn.pack(side=tk.RIGHT, padx=5)
    
    def create_status_bar(self):
        """Create a modern status bar"""
        status_frame = ttk.Frame(self)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)
        
        # Status message
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT)
        
        # Time
        self.time_var = tk.StringVar()
        time_label = ttk.Label(status_frame, textvariable=self.time_var)
        time_label.pack(side=tk.RIGHT)
        
        # Update time
        self.update_time()
    
    def update_time(self):
        """Update the time in the status bar"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_var.set(current_time)
        self.after(1000, self.update_time)
    
    def init_camera(self):
        """Initialize the camera for AR preview"""
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.status_var.set("No camera detected")
            return False
        return True
    
    def update_camera_preview(self):
        """Update the camera preview in the canvas"""
        while self.camera_running:
            ret, frame = self.cap.read()
            if ret:
                # Convert frame to PhotoImage
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (640, 480))
                photo = ImageTk.PhotoImage(image=Image.fromarray(frame))
                
                # Update canvas
                self.preview_canvas.create_image(0, 0, image=photo, anchor=tk.NW)
                self.preview_canvas.photo = photo  # Keep reference
            
            self.after(30)  # Update every 30ms
    
    def run_2d_viewer(self):
        """Run the 2D viewer application"""
        self.status_var.set("Starting 2D Viewer...")
        threading.Thread(target=self._run_script, args=('run_soccer_on_table.py',), daemon=True).start()
    
    def run_3d_viewer(self):
        """Run the 3D viewer application"""
        self.status_var.set("Starting 3D Field Visualization...")
        threading.Thread(target=self._run_script, args=('soccer3d_viewer.py',), daemon=True).start()
    
    def run_ar_viewer(self):
        """Run the AR viewer application"""
        self.status_var.set("Starting AR Experience...")
        threading.Thread(target=self._run_script, args=('ar_soccer_experience.py',), daemon=True).start()
    
    def run_vr_viewer(self):
        """Run the VR viewer application"""
        self.status_var.set("Starting VR Experience...")
        threading.Thread(target=self._run_script, args=('vr_soccer_experience.py',), daemon=True).start()
    
    def _run_script(self, script_name):
        """Internal method to run a Python script"""
        try:
            subprocess.run([sys.executable, script_name], check=True)
            self.status_var.set(f"Finished running {script_name}")
        except subprocess.CalledProcessError:
            self.status_var.set(f"Error running {script_name}")
        except FileNotFoundError:
            self.status_var.set(f"File not found: {script_name}")
            messagebox.showerror("File Not Found", f"The script {script_name} was not found.")
    
    def open_settings(self):
        """Open settings dialog"""
        settings_window = tk.Toplevel(self)
        settings_window.title("Settings")
        settings_window.geometry("400x300")
        settings_window.configure(bg=self.bg_color)
        
        # Add settings controls here
        ttk.Label(settings_window, text="Settings", font=('Segoe UI', 16, 'bold')).pack(pady=20)
    
    def check_dependencies(self):
        """Check if required dependencies are installed"""
        try:
            import numpy
            import matplotlib
            import PIL
            import pygame
            import OpenGL.GL
            self.status_var.set("All dependencies installed")
            return True
        except ImportError as e:
            self.status_var.set(f"Missing dependency: {e}")
            messagebox.showerror("Missing Dependency", 
                               f"Missing dependency: {e}\n\nPlease run:\npip install numpy matplotlib pillow pygame pyopengl")
            return False
    
    def check_data(self):
        """Check if barcelona dataset is available"""
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'barcelona', 'barcelona')
        if not os.path.exists(data_dir):
            self.status_var.set("Dataset not found")
            messagebox.warning("Missing Data", 
                             "Barcelona dataset not found. Some features may not work.\n\n" +
                             "Please download and extract the dataset using the commands in the documentation.")
            return False
        return True
    
    def on_closing(self):
        """Handle window closing"""
        self.camera_running = False
        if hasattr(self, 'cap'):
            self.cap.release()
        self.destroy()

if __name__ == "__main__":
    app = ModernUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop() 