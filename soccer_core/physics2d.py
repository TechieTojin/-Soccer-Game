"""Physics and rules for the top-down 2D match.

Velocities are expressed in pixels per 60 Hz frame, which is the convention
the game has always used. Every function takes an explicit `dt` (seconds)
and scales by `dt * 60`, so behaviour no longer depends on the real frame
rate. (Audit finding B5)

There is deliberately no vertical axis and therefore no gravity: this is a
top-down view, so "down the screen" is a direction on the grass, not
towards the floor.
"""

from __future__ import annotations

import math
from typing import Literal
from collections.abc import Iterable, Mapping, MutableSequence

from soccer_core.pitch import Pitch2D

# How much speed the ball keeps after bouncing off a wall or the net.
WALL_RESTITUTION = 0.8

# How much speed the ball keeps after bouncing off a player.
PLAYER_RESTITUTION = 0.6

# Below this separation, two bodies count as concentric and the collision
# normal is undefined. (Audit finding B6)
MIN_SEPARATION = 1e-6

Vec2 = MutableSequence[float]
GoalSide = Literal["left", "right"]


def frame_scale(dt: float) -> float:
    """Convert seconds into 60 Hz frames, the unit velocities use."""
    return dt * 60.0


def apply_damping(vel: Vec2, air_resistance: float, dt: float) -> None:
    """Slow the ball down, in place, by a time-based damping factor.

    `air_resistance` is the fraction of speed kept per 60 Hz frame; raising
    it to the power of the elapsed frames makes the loss frame-rate
    independent, so the ball coasts the same distance at 30 or 144 FPS.
    """
    damping = air_resistance ** frame_scale(dt)
    vel[0] *= damping
    vel[1] *= damping


def integrate(pos: Vec2, vel: Vec2, dt: float) -> None:
    """Advance a position by its velocity, in place."""
    scale = frame_scale(dt)
    pos[0] += vel[0] * scale
    pos[1] += vel[1] * scale


def resolve_wall_collisions(pos: Vec2, vel: Vec2, radius: float,
                            pitch: Pitch2D,
                            restitution: float = WALL_RESTITUTION) -> None:
    """Bounce the ball off the pitch boundary, in place.

    The goal mouths are gaps in the side walls: when the ball is between the
    posts it passes the goal line and bounces off the back of the net
    instead. Without that gap the ball would rebound off the goal line and
    no goal could ever be scored. (Audit finding B4)
    """
    if pitch.in_goal_mouth(pos[1]):
        left_limit, right_limit = pitch.net_left, pitch.net_right
    else:
        left_limit, right_limit = pitch.left, pitch.right

    if pos[0] < left_limit + radius:
        vel[0] *= -restitution
        pos[0] = left_limit + radius
    elif pos[0] > right_limit - radius:
        vel[0] *= -restitution
        pos[0] = right_limit - radius

    if pos[1] < pitch.top + radius:
        vel[1] *= -restitution
        pos[1] = pitch.top + radius
    elif pos[1] > pitch.bottom - radius:
        vel[1] *= -restitution
        pos[1] = pitch.bottom - radius


def resolve_player_collision(ball_pos: Vec2, ball_vel: Vec2,
                             ball_radius: float, player: Mapping,
                             restitution: float = PLAYER_RESTITUTION) -> bool:
    """Bounce the ball off one player, in place. Returns True on contact.

    A player is treated as a kinematic body: the ball bounces off them and
    their motion is imparted to it (so running into the ball pushes it),
    but the ball never shoves a player around. That is why only the ball's
    velocity changes here.

    Three things this gets right that the original did not (audit finding B6):

    * concentric bodies are skipped, because the collision normal would be a
      division by zero and would crash the game loop;
    * an impulse is only applied when the two are actually closing, so a
      ball already moving away is not dragged back in;
    * the bounce has a restitution. The old formula, with both masses at
      1.0, cancelled exactly the normal component of the velocity, so the
      ball stopped dead against a player - inconsistent with the lively 0.8
      bounce off the walls.

    The overlap is always pushed out, even when there is no impulse, so the
    ball can never come to rest inside a player.
    """
    dx = ball_pos[0] - player['pos'][0]
    dy = ball_pos[1] - player['pos'][1]
    distance = math.hypot(dx, dy)

    if distance < MIN_SEPARATION:
        return False

    contact_distance = player['radius'] + ball_radius
    if distance >= contact_distance:
        return False

    normal_x = dx / distance
    normal_y = dy / distance

    # Closing speed along the normal, relative to the player's own motion.
    relative_vel_x = ball_vel[0] - player['vel'][0]
    relative_vel_y = ball_vel[1] - player['vel'][1]
    approach_speed = relative_vel_x * normal_x + relative_vel_y * normal_y

    if approach_speed < 0:
        delta = -(1.0 + restitution) * approach_speed
        ball_vel[0] += delta * normal_x
        ball_vel[1] += delta * normal_y

    # Separate the overlap so the ball never rests inside a player.
    overlap = (contact_distance - distance) * 1.1
    ball_pos[0] += normal_x * overlap
    ball_pos[1] += normal_y * overlap
    return True


def step_ball(ball_pos: Vec2, ball_vel: Vec2, ball_radius: float,
              players: Iterable[Mapping], pitch: Pitch2D,
              air_resistance: float, dt: float) -> None:
    """Advance the ball by one tick: damping, motion, walls, then players."""
    apply_damping(ball_vel, air_resistance, dt)
    integrate(ball_pos, ball_vel, dt)
    resolve_wall_collisions(ball_pos, ball_vel, ball_radius, pitch)
    for player in players:
        resolve_player_collision(ball_pos, ball_vel, ball_radius, player)


def detect_goal(ball_pos: Vec2, ball_vel: Vec2,
                pitch: Pitch2D) -> GoalSide | None:
    """Return which goal the ball has entered, or None.

    A goal needs the ball between the posts, past the goal line, and still
    travelling into the goal - so a ball rebounding back out does not score
    twice. The goal line used here is the same one `draw_goals` draws.
    (Audit finding B4)
    """
    if not pitch.in_goal_mouth(ball_pos[1]):
        return None
    if ball_pos[0] < pitch.left and ball_vel[0] < 0:
        return "left"
    if ball_pos[0] > pitch.right and ball_vel[0] > 0:
        return "right"
    return None


def update_stamina(stamina: float, moving: bool, dt: float,
                   drain_rate: float, regen_rate: float) -> float:
    """Return the new stamina after `dt` seconds of running or resting.

    Rates are percent per second, so the result does not depend on frame
    rate, and the value is clamped to 0-100. (Audit finding B8)
    """
    if moving:
        return max(0.0, stamina - drain_rate * dt)
    return min(100.0, stamina + regen_rate * dt)


def speed_multiplier(stamina: float, floor: float = 0.3) -> float:
    """Scale a player's speed by stamina, never below `floor`.

    A completely exhausted player is slow but not frozen; at zero they could
    otherwise neither move nor recover. (Audit finding B8)
    """
    return max(floor, stamina / 100.0)
