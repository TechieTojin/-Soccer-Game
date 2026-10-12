import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import glob
from PIL import Image

class SoccerViewer:
    def __init__(self, data_path):
        self.data_path = data_path
        self.image_dir = os.path.join(data_path, 'images')
        self.image_files = sorted(glob.glob(os.path.join(self.image_dir, '*.jpg')))
        
        if not self.image_files:
            print(f"No images found in {self.image_dir}")
            sys.exit(1)
            
        self.current_idx = 0
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        plt.subplots_adjust(bottom=0.2)
        
        # Display first image
        self.img_display = self.ax.imshow(self.load_image(self.current_idx))
        self.ax.set_title(f"Frame: {os.path.basename(self.image_files[self.current_idx])}")
        
        # Add navigation buttons
        ax_prev = plt.axes([0.3, 0.05, 0.1, 0.075])
        ax_next = plt.axes([0.6, 0.05, 0.1, 0.075])
        self.btn_prev = Button(ax_prev, 'Previous')
        self.btn_next = Button(ax_next, 'Next')
        
        self.btn_prev.on_clicked(self.prev_image)
        self.btn_next.on_clicked(self.next_image)

    def load_image(self, idx):
        return np.array(Image.open(self.image_files[idx]))
    
    def prev_image(self, event):
        self.current_idx = max(0, self.current_idx - 1)
        self.update_display()
    
    def next_image(self, event):
        self.current_idx = min(len(self.image_files) - 1, self.current_idx + 1)
        self.update_display()
    
    def update_display(self):
        self.img_display.set_data(self.load_image(self.current_idx))
        self.ax.set_title(f"Frame: {os.path.basename(self.image_files[self.current_idx])}")
        self.fig.canvas.draw_idle()
    
    def run(self):
        plt.show()

def detect_players(sample_img_path):
    """Placeholder for player detection functionality"""
    img = np.array(Image.open(sample_img_path))
    
    # Simulated detection - in a real scenario, this would use a model like Detectron
    # For now, we'll just display a template message
    plt.figure(figsize=(8, 6))
    plt.imshow(img)
    plt.title("Player Detection Simulation")
    plt.text(10, 30, "In the full pipeline, this would use Detectron for player detection", 
             color='white', backgroundcolor='black')
    plt.show()

def main():
    # Setup paths - adjust based on where you extracted the barcelona dataset
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'barcelona', 'barcelona')
    
    if not os.path.exists(data_dir):
        print(f"Error: Data directory not found: {data_dir}")
        print("Please make sure you've downloaded and extracted the barcelona.zip file")
        sys.exit(1)
    
    print("\n=== Soccer On Your Tabletop - Windows Version ===")
    print(f"Data directory: {data_dir}")
    
    # Menu options
    while True:
        print("\nChoose an option:")
        print("1. View soccer images")
        print("2. Simulate player detection")
        print("3. About this project")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ")
        
        if choice == '1':
            viewer = SoccerViewer(data_dir)
            viewer.run()
        elif choice == '2':
            images_dir = os.path.join(data_dir, 'images')
            sample_img = sorted(glob.glob(os.path.join(images_dir, '*.jpg')))[0]
            detect_players(sample_img)
        elif choice == '3':
            print("\nSoccer On Your Tabletop")
            print("This is a simplified Windows version of the project from:")
            print("http://grail.cs.washington.edu/projects/soccer/")
            print("\nThe original project converts YouTube soccer videos to 3D models")
            print("and was developed by Konstantinos Rematas, Ira Kemelmacher-Shlizerman,")
            print("Brian Curless, and Steve Seitz at CVPR 2018.")
        elif choice == '4':
            print("Exiting...")
            break
        else:
            print("Invalid choice, please try again.")

if __name__ == "__main__":
    main() 