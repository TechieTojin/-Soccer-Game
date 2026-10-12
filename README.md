# Soccer AR/VR Experience

A modern soccer game with Augmented Reality (AR) and Virtual Reality (VR) capabilities, developed by Tojin Varkey Simson and Jaiby Mariya Jospeh.

## Overview

This project brings soccer to life through multiple interactive experiences:
- 2D Soccer Game with realistic physics and player controls
- 3D Field Visualization
- AR Experience for table-top soccer
- VR Experience for immersive gameplay

## Features

### 2D Soccer Game
- Real-time player movement and ball physics
- Player roles and attributes (GK, LB, CB, RB, LM, CM, RM, ST)
- Stamina system affecting player performance
- Score tracking and match timer
- Realistic ball physics with gravity and air resistance
- Player switching and team management

### AR Experience
- Table-top soccer field visualization
- Camera-based field tracking
- Interactive ball physics
- Player animations and formations
- Goal celebrations and effects

### VR Experience
- Immersive 3D soccer field
- First-person perspective
- Realistic player models
- Interactive ball control
- Dynamic lighting and shadows

## Installation

1. Clone the repository:
```bash
git clone https://github.com/TechieTojin/-Soccer-Game.git
cd -Soccer-Game
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Download and extract the Barcelona dataset:
```bash
# The dataset will be automatically downloaded and extracted when running the game
```

## Usage

1. Run the main application:
```bash
python run_windows_version.py
```

2. Select your preferred mode from the menu:
   - 2D Soccer Game
   - 3D Field Visualization
   - AR Experience
   - VR Experience

### Controls

#### 2D Game Controls
- Arrow keys: Move selected player
- Space: Kick ball
- Tab: Switch between teams
- 1-9: Select specific players
- ESC: Return to menu

#### AR/VR Controls
- WASD: Move around the field
- Arrow keys: Look around
- Space: Kick ball
- V: Toggle VR mode
- A: Toggle AR mode
- ESC: Exit

## System Requirements

- Windows 10 or later
- Python 3.7+
- Webcam (for AR mode)
- OpenGL compatible graphics card
- Minimum 4GB RAM
- 2GB free disk space

## Project Structure

```
soccerontable/
├── barcelona/           # Dataset directory
├── utils/              # Utility functions
├── soccer3d/           # 3D visualization components
├── demo/               # Demo files
├── modern_interface.py # Modern UI implementation
├── ar_soccer_experience.py # AR experience
├── vr_soccer_experience.py # VR experience
├── soccer_game.py      # Main game logic
├── run_windows_version.py # Windows launcher
└── requirements.txt    # Dependencies
```

## Development

This project was developed by Tojin Varkey Simson and Jaiby Mariya Jospeh as part of their research in interactive gaming and augmented reality experiences.

### Key Technologies Used
- Python
- Pygame
- OpenGL
- OpenCV
- NumPy
- SciPy

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Barcelona dataset for player tracking
- OpenCV community for AR marker detection
- Pygame community for game development tools

## Contact

For any questions or suggestions, please contact:
- Tojin Varkey Simson
- Jaiby Mariya Jospeh
