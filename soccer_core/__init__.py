"""Display-independent gameplay logic for the Soccer AR/VR Experience.

Nothing in this package imports pygame or OpenGL, so every rule in here -
ball physics, collisions, scoring, stamina, formations and the VR stereo
camera maths - can be unit-tested without a window, a GPU or a webcam.

The rendering front-ends (soccer_game.py, ar_soccer_experience.py,
vr_soccer_experience.py, soccer3d_viewer.py) own the drawing and input; they
delegate the rules to this package.
"""

from soccer_core.pitch import Pitch2D, Pitch3D
from soccer_core import physics2d, physics3d, formations, stereo

__all__ = ["Pitch2D", "Pitch3D", "physics2d", "physics3d", "formations", "stereo"]
