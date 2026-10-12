"""Shared pytest fixtures for the Soccer AR/VR Experience tests.

The tests run headless: SDL is forced onto its dummy video/audio drivers
before pygame is imported, so a real window is never created and no webcam
is opened. This lets the gameplay logic be tested in CI.
"""

import os
import sys
from pathlib import Path

# Must be set before pygame is imported by the game module.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

# Make the project root importable regardless of where pytest is started.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def game():
    """A SoccerGame instance with no webcam, in a fresh 2D-game state."""
    from soccer_game import SoccerGame

    g = SoccerGame(enable_camera=False)
    g.reset_game_state()
    # Fixed timestep keeps physics assertions deterministic.
    g.dt = 1 / 60
    yield g

    import pygame
    pygame.quit()
