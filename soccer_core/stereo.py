"""Camera maths for the side-by-side stereo (VR) view.

Three defects in the original VR code are fixed here, and because none of
this needs OpenGL it is all unit-tested. (Audit finding B13)

1. The aspect ratio was computed as `width / (height / 2)` while each eye
   actually renders into a `width/2 x height` viewport, so the picture was
   horizontally squashed.
2. The eye separation was applied along world X. After turning, the two eyes
   ended up separated along the view direction instead of across it, which
   destroys the stereo effect.
3. Look direction was stored as a vector and repeatedly rotated, so it drifted
   from unit length and the pitch could flip past vertical. Angles are kept
   here and the direction is derived from them.

This is a stereo *preview* for a flat screen. It is not headset support:
there is no head tracking and no lens distortion correction.
"""

from __future__ import annotations

import math
from typing import Literal
from collections.abc import Sequence

Vec3 = Sequence[float]
Eye = Literal["left", "right", "centre"]

# Looking more steeply than this would flip the view upside down.
MAX_PITCH_DEGREES = 89.0


def viewport_aspect(width: int, height: int, split_screen: bool) -> float:
    """Aspect ratio for one eye's viewport.

    In split-screen stereo each eye occupies the left or right half of the
    window, so its viewport is `width/2` by `height`.
    """
    eye_width = width / 2 if split_screen else width
    return eye_width / float(height)


def clamp_pitch(pitch_degrees: float,
                limit: float = MAX_PITCH_DEGREES) -> float:
    """Clamp a pitch angle so the view can never flip over."""
    return max(-limit, min(limit, pitch_degrees))


def direction_from_angles(yaw_degrees: float, pitch_degrees: float) -> tuple[float, float, float]:
    """Unit look direction for a yaw/pitch pair.

    Yaw 0 and pitch 0 looks down -Z, matching the scene's starting view.
    Positive yaw turns left-to-right, positive pitch looks up. The result is
    always unit length, so repeated turning cannot make it drift.
    """
    yaw = math.radians(yaw_degrees)
    pitch = math.radians(clamp_pitch(pitch_degrees))
    cos_pitch = math.cos(pitch)
    return (
        math.sin(yaw) * cos_pitch,
        math.sin(pitch),
        -math.cos(yaw) * cos_pitch,
    )


def normalise(vector: Vec3) -> tuple[float, float, float]:
    """Return `vector` scaled to unit length (unchanged if degenerate)."""
    length = math.sqrt(sum(component * component for component in vector))
    if length < 1e-9:
        return (vector[0], vector[1], vector[2])
    return (vector[0] / length, vector[1] / length, vector[2] / length)


def cross(a: Vec3, b: Vec3) -> tuple[float, float, float]:
    """Cross product of two 3-vectors."""
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def right_vector(look_dir: Vec3, up: Vec3 = (0.0, 1.0, 0.0)) -> tuple[float, float, float]:
    """Unit vector pointing to the camera's right.

    This is the axis the eyes are separated along, which is what makes the
    stereo effect survive turning the camera.
    """
    return normalise(cross(look_dir, up))


def eye_position(camera_pos: Vec3, look_dir: Vec3, ipd: float, eye: Eye,
                 up: Vec3 = (0.0, 1.0, 0.0)) -> tuple[float, float, float]:
    """Position of one eye, offset across the view direction.

    `ipd` is the interpupillary distance in metres; each eye sits half of it
    either side of `camera_pos`.
    """
    if eye == "centre":
        return (camera_pos[0], camera_pos[1], camera_pos[2])

    right = right_vector(look_dir, up)
    offset = (ipd / 2.0) if eye == "right" else (-ipd / 2.0)
    return (
        camera_pos[0] + right[0] * offset,
        camera_pos[1] + right[1] * offset,
        camera_pos[2] + right[2] * offset,
    )


def move(camera_pos: Vec3, look_dir: Vec3, forward: float, strafe: float,
         up: Vec3 = (0.0, 1.0, 0.0)) -> list[float]:
    """Walk the camera over the ground plane.

    Movement stays horizontal (Y is untouched) so looking up or down does
    not lift the viewer off the pitch.
    """
    flat_look = normalise((look_dir[0], 0.0, look_dir[2]))
    right = right_vector(look_dir, up)
    return [
        camera_pos[0] + flat_look[0] * forward + right[0] * strafe,
        camera_pos[1],
        camera_pos[2] + flat_look[2] * forward + right[2] * strafe,
    ]
