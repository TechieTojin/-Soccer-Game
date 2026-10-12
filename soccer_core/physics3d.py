"""Ball physics for the 3D scenes, shared by the AR and VR front-ends.

The AR and VR modules each carried their own identical copy of this logic;
it now lives here once. (Audit finding: ~300 duplicated lines between
ar_soccer_experience.py and vr_soccer_experience.py.)

Unlike the 2D game this really is a 3D world, so gravity is meaningful: the
pitch lies in the XZ plane with Y up.

Units
-----
Positions are metres and velocities are **metres per second**. The original
code stored velocities per rendered frame and assumed exactly 60 FPS. The
constants below are the per-second equivalents of those per-frame values, so
stepping this module at dt = 1/60 reproduces the original motion exactly
while any other frame rate now behaves correctly.
"""

from __future__ import annotations

import math
from typing import Literal
from collections.abc import MutableSequence

from soccer_core.pitch import Pitch3D

# Legacy per-frame constants, converted to per-second:
#   0.01 units/frame^2 * 60^2 frames^2/s^2 = 36 units/s^2
GRAVITY = 36.0
# Fraction of horizontal speed kept per 60 Hz frame.
GROUND_FRICTION = 0.99
# Speed kept after a bounce.
RESTITUTION = 0.8
# Legacy kick-off velocity [0.1, 0, 0.1] units/frame, in units/second.
KICKOFF_VELOCITY = (6.0, 0.0, 6.0)

Vec3 = MutableSequence[float]
GoalSide = Literal["left", "right"]


def step_ball(pos: Vec3, vel: Vec3, dt: float, pitch: Pitch3D,
              radius: float = 0.2) -> None:
    """Advance the 3D ball by `dt` seconds, in place.

    Applies gravity, integrates, bounces off the ground and the pitch
    boundary, and damps horizontal speed with ground friction.
    """
    # Gravity acts on the vertical (Y) axis only.
    vel[1] -= GRAVITY * dt

    pos[0] += vel[0] * dt
    pos[1] += vel[1] * dt
    pos[2] += vel[2] * dt

    # Ground
    if pos[1] < radius:
        pos[1] = radius
        vel[1] = -vel[1] * RESTITUTION

    # Pitch boundary: bounce back inside, just short of the line.
    if abs(pos[0]) > pitch.half_length:
        vel[0] = -vel[0] * RESTITUTION
        pos[0] = math.copysign(pitch.half_length - 0.1, pos[0])

    if abs(pos[2]) > pitch.half_width:
        vel[2] = -vel[2] * RESTITUTION
        pos[2] = math.copysign(pitch.half_width - 0.1, pos[2])

    # Rolling/air friction on the horizontal axes, time-based.
    damping = GROUND_FRICTION ** (dt * 60.0)
    vel[0] *= damping
    vel[2] *= damping


def detect_goal(pos: Vec3, pitch: Pitch3D) -> GoalSide | None:
    """Return which goal the ball is in, or None.

    "left" is the goal at negative X, "right" the goal at positive X.
    """
    if not pitch.is_between_posts(pos[2]):
        return None
    if abs(pos[0]) <= pitch.half_length - 1.0:
        return None
    return "left" if pos[0] < 0 else "right"


def kickoff_state(height: float = 0.5) -> tuple[list[float], list[float]]:
    """Return the ball's (position, velocity) for a kick-off."""
    return [0.0, height, 0.0], list(KICKOFF_VELOCITY)
