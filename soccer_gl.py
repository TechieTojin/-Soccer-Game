"""Shared OpenGL drawing for the 3D scenes (AR and VR).

The AR and VR modules each carried their own copy of the field texture,
player model, ball and particle effects - roughly 300 near-identical lines.
They now share this module, so a fix lands in both scenes at once.

Two classes of bug are fixed here (audit finding B14):

* **Orientation.** `gluCylinder` extrudes along +Z. The old code rotated by
  +90 degrees about X, which maps +Z to *-Y*, so goalposts and torsos grew
  downwards through the ground. Standing parts now rotate by -90 (+Z -> +Y)
  and parts that should hang down (legs, arms) keep +90 and start from the
  correct joint height, so nothing ends up below the pitch.
* **Crossbars** were rotated about Y, putting them along X - across the goal
  mouth instead of spanning it. A crossbar spans Z, which is the quadric's
  natural axis, so it needs no rotation at all.

It also stops allocating a fresh GLU quadric for every limb of every player
on every frame (22 players x ~7 parts x 60 FPS); one quadric is reused.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
import cv2
from OpenGL.GL import *
from OpenGL.GLU import *

from soccer_core.pitch import Pitch3D

# One reusable quadric instead of thousands per second.
_QUADRIC = None


def quadric():
    """Return the shared GLU quadric, creating it on first use."""
    global _QUADRIC
    if _QUADRIC is None:
        _QUADRIC = gluNewQuadric()
        gluQuadricNormals(_QUADRIC, GLU_SMOOTH)
    return _QUADRIC


# ---------------------------------------------------------------------------
# Field texture
# ---------------------------------------------------------------------------

def build_field_image(pitch: Pitch3D, width: int = 1024) -> np.ndarray:
    """Render the pitch markings into an RGB image.

    Everything is drawn with OpenCV on a NumPy array. The VR scene used to
    build the centre circle with a Python loop over 1024x1024 pixels -
    more than a million iterations with a `sqrt` each, several seconds of
    start-up - and drew it on a square texture, which stretched the circle
    into an ellipse once it was mapped onto a 105x68 pitch.
    (Audit finding B15)
    """
    # Texture proportioned like the pitch, so circles stay circular.
    height = max(1, int(round(width * pitch.width_z / pitch.length_x)))
    image = np.zeros((height, width, 3), dtype=np.uint8)

    # Grass, with mowing stripes.
    image[:, :] = (36, 120, 46)
    stripes = 12
    stripe_width = width / stripes
    for index in range(stripes):
        if index % 2:
            x0 = int(index * stripe_width)
            x1 = int((index + 1) * stripe_width)
            image[:, x0:x1] = (42, 132, 54)

    white = (242, 246, 240)
    thickness = max(2, width // 340)
    margin = int(width * 0.03)

    def to_px(x_m: float, z_m: float) -> tuple[int, int]:
        """Pitch metres -> texture pixels."""
        u = (x_m / pitch.length_x + 0.5) * (width - 2 * margin) + margin
        v = (z_m / pitch.width_z + 0.5) * (height - 2 * margin) + margin
        return int(round(u)), int(round(v))

    # Touchlines and goal lines
    cv2.rectangle(image, to_px(-pitch.half_length, -pitch.half_width),
                  to_px(pitch.half_length, pitch.half_width), white, thickness)
    # Halfway line
    cv2.line(image, to_px(0, -pitch.half_width), to_px(0, pitch.half_width),
             white, thickness)
    # Centre circle (9.15 m radius) and spot
    centre = to_px(0, 0)
    radius_px = int(round(9.15 / pitch.length_x * (width - 2 * margin)))
    cv2.circle(image, centre, radius_px, white, thickness)
    cv2.circle(image, centre, max(2, thickness), white, -1)

    # Penalty areas (16.5 m deep, 40.3 m wide) and six-yard boxes
    for depth, span in ((16.5, 40.3), (5.5, 18.3)):
        cv2.rectangle(image,
                      to_px(-pitch.half_length, -span / 2),
                      to_px(-pitch.half_length + depth, span / 2),
                      white, thickness)
        cv2.rectangle(image,
                      to_px(pitch.half_length - depth, -span / 2),
                      to_px(pitch.half_length, span / 2),
                      white, thickness)

    # Penalty spots
    cv2.circle(image, to_px(-pitch.half_length + 11.0, 0), max(2, thickness), white, -1)
    cv2.circle(image, to_px(pitch.half_length - 11.0, 0), max(2, thickness), white, -1)

    return image


def create_field_texture(pitch: Pitch3D, width: int = 1024) -> int:
    """Upload the pitch markings as an OpenGL texture and return its id."""
    image = build_field_image(pitch, width)
    height = image.shape[0]

    texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0,
                 GL_RGB, GL_UNSIGNED_BYTE, image)
    glGenerateMipmap(GL_TEXTURE_2D)
    return texture_id


# ---------------------------------------------------------------------------
# Scene elements
# ---------------------------------------------------------------------------

def draw_field(texture_id: int, pitch: Pitch3D) -> None:
    """Draw the textured pitch in the XZ plane."""
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    glColor3f(1.0, 1.0, 1.0)
    glMaterialfv(GL_FRONT, GL_AMBIENT, (0.35, 0.35, 0.35, 1.0))
    glMaterialfv(GL_FRONT, GL_DIFFUSE, (0.9, 0.9, 0.9, 1.0))
    glMaterialfv(GL_FRONT, GL_SPECULAR, (0.0, 0.0, 0.0, 1.0))

    glBegin(GL_QUADS)
    glNormal3f(0, 1, 0)
    glTexCoord2f(0, 0); glVertex3f(-pitch.half_length, 0.0, -pitch.half_width)
    glTexCoord2f(1, 0); glVertex3f(pitch.half_length, 0.0, -pitch.half_width)
    glTexCoord2f(1, 1); glVertex3f(pitch.half_length, 0.0, pitch.half_width)
    glTexCoord2f(0, 1); glVertex3f(-pitch.half_length, 0.0, pitch.half_width)
    glEnd()

    glDisable(GL_TEXTURE_2D)


def draw_goal(pitch: Pitch3D, at_negative_x: bool) -> None:
    """Draw one goal: two uprights, a crossbar and a translucent net.

    The uprights stand *up* from the goal line and the crossbar spans the
    goal mouth, which is what the original rotations got wrong. (B14)
    """
    quad = quadric()
    post_radius = 0.1
    half_goal = pitch.goal_width / 2.0
    x = -pitch.half_length if at_negative_x else pitch.half_length
    # The net extends away from the pitch centre.
    depth_direction = -1.0 if at_negative_x else 1.0

    glColor3f(1.0, 1.0, 1.0)
    glMaterialfv(GL_FRONT, GL_AMBIENT, (0.5, 0.5, 0.5, 1.0))
    glMaterialfv(GL_FRONT, GL_DIFFUSE, (1.0, 1.0, 1.0, 1.0))

    # Uprights: +Z extruded to +Y by rotating -90 about X.
    for z in (-half_goal, half_goal):
        glPushMatrix()
        glTranslatef(x, 0.0, z)
        glRotatef(-90, 1, 0, 0)
        gluCylinder(quad, post_radius, post_radius, pitch.goal_height, 12, 1)
        glPopMatrix()

    # Crossbar: spans Z, the quadric's own axis, so no rotation.
    glPushMatrix()
    glTranslatef(x, pitch.goal_height, -half_goal)
    gluCylinder(quad, post_radius, post_radius, pitch.goal_width, 12, 1)
    glPopMatrix()

    # Net: a translucent back and two sides.
    back_x = x + depth_direction * pitch.goal_depth
    glEnable(GL_BLEND)
    glColor4f(0.92, 0.92, 0.92, 0.25)
    glMaterialfv(GL_FRONT, GL_AMBIENT, (0.9, 0.9, 0.9, 0.25))
    glMaterialfv(GL_FRONT, GL_DIFFUSE, (0.9, 0.9, 0.9, 0.25))

    glBegin(GL_QUADS)
    glNormal3f(-depth_direction, 0, 0)
    glVertex3f(back_x, 0.0, -half_goal)
    glVertex3f(back_x, pitch.goal_height, -half_goal)
    glVertex3f(back_x, pitch.goal_height, half_goal)
    glVertex3f(back_x, 0.0, half_goal)
    glEnd()

    for z in (-half_goal, half_goal):
        glBegin(GL_QUADS)
        glNormal3f(0, 0, 1 if z < 0 else -1)
        glVertex3f(x, 0.0, z)
        glVertex3f(x, pitch.goal_height, z)
        glVertex3f(back_x, pitch.goal_height, z)
        glVertex3f(back_x, 0.0, z)
        glEnd()

    glBegin(GL_QUADS)
    glNormal3f(0, 1, 0)
    glVertex3f(x, pitch.goal_height, -half_goal)
    glVertex3f(back_x, pitch.goal_height, -half_goal)
    glVertex3f(back_x, pitch.goal_height, half_goal)
    glVertex3f(x, pitch.goal_height, half_goal)
    glEnd()
    glDisable(GL_BLEND)


def draw_goals(pitch: Pitch3D) -> None:
    """Draw the goals at both ends."""
    draw_goal(pitch, at_negative_x=True)
    draw_goal(pitch, at_negative_x=False)


def draw_player(x: float, z: float, jersey: Sequence[float],
                animation_time: float = 0.0) -> None:
    """Draw one player standing on the pitch at (x, z).

    The model is built upwards from the grass: legs from hip to foot, torso
    on top, then head and arms. Every part is above y = 0.
    """
    quad = quadric()
    swing = math.sin(animation_time + x * 0.3)

    hip_height = 0.8
    leg_length = 0.8
    torso_height = 1.0
    shoulder_height = hip_height + torso_height * 0.85

    glPushMatrix()
    glTranslatef(x, 0.0, z)

    glColor3f(*jersey)
    glMaterialfv(GL_FRONT, GL_AMBIENT, (*jersey, 1.0))
    glMaterialfv(GL_FRONT, GL_DIFFUSE, (*jersey, 1.0))

    # Torso: stands up from the hips (-90 about X maps +Z to +Y).
    glPushMatrix()
    glTranslatef(0.0, hip_height, 0.0)
    glRotatef(-90, 1, 0, 0)
    gluCylinder(quad, 0.28, 0.24, torso_height, 12, 1)
    glPopMatrix()

    # Head
    glPushMatrix()
    glTranslatef(0.0, hip_height + torso_height + 0.18, 0.0)
    gluSphere(quad, 0.18, 12, 12)
    glPopMatrix()

    # Legs hang downwards from the hips (+90 about X maps +Z to -Y), so the
    # feet land on the grass rather than under it.
    for side, phase in ((-0.14, 1.0), (0.14, -1.0)):
        glPushMatrix()
        glTranslatef(side, hip_height, 0.0)
        glRotatef(90, 1, 0, 0)
        glRotatef(22.0 * swing * phase, 1, 0, 0)
        gluCylinder(quad, 0.09, 0.07, leg_length, 10, 1)
        glPopMatrix()

    # Arms hang down from the shoulders with a small swing.
    for side, phase in ((-0.32, -1.0), (0.32, 1.0)):
        glPushMatrix()
        glTranslatef(side, shoulder_height, 0.0)
        glRotatef(90, 1, 0, 0)
        glRotatef(25.0 * swing * phase, 1, 0, 0)
        gluCylinder(quad, 0.07, 0.055, 0.62, 8, 1)
        glPopMatrix()

    glPopMatrix()


def draw_players(players, animation_time: float = 0.0) -> None:
    """Draw every `(x, z, rgb)` player in the scene."""
    for x, z, colour in players:
        draw_player(x, z, colour, animation_time)


def draw_ball(position: Sequence[float], radius: float = 0.2) -> None:
    """Draw the ball at `position`."""
    quad = quadric()
    glPushMatrix()
    glTranslatef(position[0], position[1], position[2])
    glColor3f(1.0, 1.0, 1.0)
    glMaterialfv(GL_FRONT, GL_AMBIENT, (0.75, 0.75, 0.75, 1.0))
    glMaterialfv(GL_FRONT, GL_DIFFUSE, (0.95, 0.95, 0.95, 1.0))
    gluSphere(quad, radius, 20, 20)
    glPopMatrix()


# ---------------------------------------------------------------------------
# Particle effects
# ---------------------------------------------------------------------------

def add_effect(effects: list, effect_type: str, position: Sequence[float],
               duration: float = 1.0) -> None:
    """Queue a short-lived visual effect at `position`."""
    effects.append({
        'type': effect_type,
        'position': list(position),
        'time': 0.0,
        'max_time': duration,
    })


def update_effects(effects: list, dt: float) -> None:
    """Age effects by `dt` seconds and drop the finished ones.

    Ageing is time-based rather than a fixed 0.016 per frame, and is kept
    separate from drawing so the two cannot disagree.
    """
    for effect in effects:
        effect['time'] += dt
    effects[:] = [e for e in effects if e['time'] < e['max_time']]


def draw_effects(effects: list) -> None:
    """Draw queued effects (currently just the goal celebration)."""
    quad = quadric()
    glEnable(GL_BLEND)
    for effect in effects:
        if effect['type'] != 'goal':
            continue
        progress = effect['time'] / effect['max_time']
        alpha = max(0.0, 1.0 - progress)
        glColor4f(1.0, 0.95, 0.25, alpha)
        glMaterialfv(GL_FRONT, GL_AMBIENT, (1.0, 0.95, 0.25, alpha))
        glMaterialfv(GL_FRONT, GL_DIFFUSE, (1.0, 0.95, 0.25, alpha))

        glPushMatrix()
        glTranslatef(*effect['position'])
        # A deterministic burst: particles spread out as the effect ages.
        spread = progress * 3.0
        for index in range(12):
            angle = index * (2 * math.pi / 12)
            glPushMatrix()
            glTranslatef(math.cos(angle) * spread,
                         abs(math.sin(angle)) * spread * 0.6,
                         math.sin(angle) * spread)
            gluSphere(quad, 0.12, 6, 6)
            glPopMatrix()
        glPopMatrix()
    glDisable(GL_BLEND)
