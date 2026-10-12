"""Unit tests for the display-independent physics in soccer_core.

These exercise the extracted modules directly (no pygame, no window), which
is the point of having extracted them.
"""

import math

import pytest

from soccer_core import physics2d, physics3d
from soccer_core.pitch import Pitch2D, Pitch3D


@pytest.fixture
def pitch2d():
    return Pitch2D(width=1280, height=720, margin=100,
                   goal_height=100, goal_depth=20)


@pytest.fixture
def pitch3d():
    return Pitch3D()


def make_player(x, y, vx=0.0, vy=0.0, radius=15, mass=1.0):
    return {'pos': [x, y], 'vel': [vx, vy], 'radius': radius, 'mass': mass}


# ---------------------------------------------------------------------------
# Pitch geometry
# ---------------------------------------------------------------------------

class TestPitch2D:

    def test_lines_are_inset_by_the_margin(self, pitch2d):
        assert pitch2d.left == 100
        assert pitch2d.right == 1180
        assert pitch2d.top == 100
        assert pitch2d.bottom == 620

    def test_goal_mouth_is_centred(self, pitch2d):
        assert pitch2d.goal_y0 == 310
        assert pitch2d.goal_y1 == 410
        assert pitch2d.in_goal_mouth(360)
        assert not pitch2d.in_goal_mouth(200)

    def test_nets_sit_outside_the_goal_lines(self, pitch2d):
        assert pitch2d.net_left < pitch2d.left
        assert pitch2d.net_right > pitch2d.right


class TestPitch3D:

    def test_long_axis_is_x(self, pitch3d):
        """X runs goal-to-goal, Z touchline-to-touchline. Getting this the
        wrong way round is what put players off the pitch. (B9)"""
        assert pitch3d.half_length > pitch3d.half_width
        assert pitch3d.half_length == pytest.approx(52.5)
        assert pitch3d.half_width == pytest.approx(34.0)

    def test_contains_and_posts(self, pitch3d):
        assert pitch3d.contains(0, 0)
        assert not pitch3d.contains(60, 0)      # beyond the goal line
        assert not pitch3d.contains(0, 40)      # beyond the touchline
        assert pitch3d.is_between_posts(0.0)
        assert not pitch3d.is_between_posts(10.0)


# ---------------------------------------------------------------------------
# 2D physics
# ---------------------------------------------------------------------------

class TestDamping:

    def test_damping_is_frame_rate_independent(self):
        """One simulated second loses the same speed at any step size."""
        def remaining(dt, steps):
            vel = [10.0, 0.0]
            for _ in range(steps):
                physics2d.apply_damping(vel, 0.99, dt)
            return vel[0]

        assert remaining(1 / 60, 60) == pytest.approx(remaining(1 / 240, 240),
                                                      rel=1e-9)

    def test_damping_never_reverses_direction(self):
        vel = [5.0, -3.0]
        for _ in range(600):
            physics2d.apply_damping(vel, 0.99, 1 / 60)
        assert vel[0] > 0
        assert vel[1] < 0


class TestWallCollisions:

    def test_ball_bounces_off_a_touchline(self, pitch2d):
        pos, vel = [600.0, pitch2d.top - 5], [0.0, -4.0]
        physics2d.resolve_wall_collisions(pos, vel, 8, pitch2d)
        assert vel[1] > 0
        assert pos[1] == pytest.approx(pitch2d.top + 8)

    def test_goal_mouth_is_open(self, pitch2d):
        """Between the posts the ball passes the goal line. (B4)"""
        pos, vel = [pitch2d.left - 5, 360.0], [-4.0, 0.0]
        physics2d.resolve_wall_collisions(pos, vel, 8, pitch2d)
        assert vel[0] < 0, "the ball should not bounce off an open goal mouth"

    def test_ball_bounces_off_the_back_of_the_net(self, pitch2d):
        pos, vel = [pitch2d.net_left - 2, 360.0], [-4.0, 0.0]
        physics2d.resolve_wall_collisions(pos, vel, 8, pitch2d)
        assert vel[0] > 0
        assert pos[0] >= pitch2d.net_left

    def test_goal_line_is_solid_outside_the_mouth(self, pitch2d):
        pos, vel = [pitch2d.left - 5, 200.0], [-4.0, 0.0]
        physics2d.resolve_wall_collisions(pos, vel, 8, pitch2d)
        assert vel[0] > 0
        assert pos[0] == pytest.approx(pitch2d.left + 8)


class TestPlayerCollision:

    def test_concentric_bodies_are_skipped(self):
        """Would be a divide-by-zero without the guard. (B6)"""
        player = make_player(100.0, 100.0)
        pos, vel = [100.0, 100.0], [1.0, 0.0]
        assert physics2d.resolve_player_collision(pos, vel, 8, player) is False

    def test_approaching_ball_bounces_back(self):
        player = make_player(100.0, 100.0)
        pos, vel = [110.0, 100.0], [-5.0, 0.0]   # heading into the player
        assert physics2d.resolve_player_collision(pos, vel, 8, player)
        assert vel[0] > 0, "an approaching ball should bounce away"
        assert abs(vel[0]) < 5.0, "the bounce should lose some energy"

    def test_bounce_respects_restitution(self):
        player = make_player(100.0, 100.0)
        pos, vel = [110.0, 100.0], [-10.0, 0.0]
        physics2d.resolve_player_collision(pos, vel, 8, player, restitution=0.5)
        assert vel[0] == pytest.approx(5.0)

    def test_separating_ball_is_not_dragged_back(self):
        """The old impulse applied regardless of direction, so a ball
        already moving away was pulled back into the player. (B6)"""
        player = make_player(100.0, 100.0)
        pos, vel = [110.0, 100.0], [5.0, 0.0]    # already moving away
        physics2d.resolve_player_collision(pos, vel, 8, player)
        assert vel[0] == pytest.approx(5.0)

    def test_moving_player_pushes_the_ball(self):
        """Running into a stationary ball should move it."""
        player = make_player(100.0, 100.0, vx=4.0)
        pos, vel = [110.0, 100.0], [0.0, 0.0]
        physics2d.resolve_player_collision(pos, vel, 8, player)
        assert vel[0] > 0

    def test_overlap_is_always_separated(self):
        player = make_player(100.0, 100.0)
        pos, vel = [105.0, 100.0], [0.0, 0.0]
        physics2d.resolve_player_collision(pos, vel, 8, player)
        assert math.dist(pos, player['pos']) >= player['radius'] + 8

    def test_distant_player_is_ignored(self):
        player = make_player(500.0, 500.0)
        pos, vel = [100.0, 100.0], [1.0, 2.0]
        assert physics2d.resolve_player_collision(pos, vel, 8, player) is False
        assert vel == [1.0, 2.0]


class TestGoalDetection:

    def test_goal_each_side(self, pitch2d):
        assert physics2d.detect_goal([pitch2d.left - 1, 360], [-5, 0], pitch2d) == "left"
        assert physics2d.detect_goal([pitch2d.right + 1, 360], [5, 0], pitch2d) == "right"

    def test_no_goal_outside_the_mouth_or_moving_out(self, pitch2d):
        assert physics2d.detect_goal([pitch2d.left - 1, 150], [-5, 0], pitch2d) is None
        assert physics2d.detect_goal([pitch2d.left - 1, 360], [5, 0], pitch2d) is None
        assert physics2d.detect_goal([640, 360], [-5, 0], pitch2d) is None


class TestStamina:

    def test_rates_are_per_second(self):
        assert physics2d.update_stamina(100.0, True, 1.0, 15.0, 8.0) == 85.0
        assert physics2d.update_stamina(50.0, False, 1.0, 15.0, 8.0) == 58.0

    def test_clamped_to_range(self):
        assert physics2d.update_stamina(1.0, True, 10.0, 15.0, 8.0) == 0.0
        assert physics2d.update_stamina(99.0, False, 10.0, 15.0, 8.0) == 100.0

    def test_speed_multiplier_has_a_floor(self):
        """An exhausted player must still be able to move. (B8)"""
        assert physics2d.speed_multiplier(0.0) == 0.3
        assert physics2d.speed_multiplier(100.0) == 1.0
        assert physics2d.speed_multiplier(50.0) == 0.5


# ---------------------------------------------------------------------------
# 3D physics (AR / VR)
# ---------------------------------------------------------------------------

class TestPhysics3D:

    def test_matches_the_legacy_per_frame_simulation(self, pitch3d):
        """The dt-based rewrite must reproduce the original 60 FPS motion.

        The original stepped per frame: vel[1] -= 0.01, pos += vel,
        friction *= 0.99. Velocities here are per second (60x larger), so
        stepping at dt = 1/60 should land in the same place.
        """
        legacy_pos = [0.0, 5.0, 0.0]
        legacy_vel = [0.1, 0.0, 0.05]       # per frame
        for _ in range(120):
            legacy_vel[1] -= 0.01
            for axis in range(3):
                legacy_pos[axis] += legacy_vel[axis]
            if legacy_pos[1] < 0.2:
                legacy_pos[1] = 0.2
                legacy_vel[1] = -legacy_vel[1] * 0.8
            legacy_vel[0] *= 0.99
            legacy_vel[2] *= 0.99

        pos = [0.0, 5.0, 0.0]
        vel = [0.1 * 60, 0.0, 0.05 * 60]    # per second
        for _ in range(120):
            physics3d.step_ball(pos, vel, 1 / 60, pitch3d, radius=0.2)

        assert pos[0] == pytest.approx(legacy_pos[0], rel=1e-6)
        assert pos[1] == pytest.approx(legacy_pos[1], rel=1e-6)
        assert pos[2] == pytest.approx(legacy_pos[2], rel=1e-6)

    def test_ball_settles_on_the_ground(self, pitch3d):
        pos, vel = [0.0, 6.0, 0.0], [0.0, 0.0, 0.0]
        for _ in range(900):
            physics3d.step_ball(pos, vel, 1 / 60, pitch3d, radius=0.2)
        assert pos[1] >= 0.2 - 1e-9
        assert pos[1] < 0.5, "the ball should have stopped bouncing high"

    def test_ball_stays_inside_the_pitch(self, pitch3d):
        pos, vel = [0.0, 0.2, 0.0], [80.0, 5.0, 60.0]
        for _ in range(1200):
            physics3d.step_ball(pos, vel, 1 / 60, pitch3d, radius=0.2)
            assert abs(pos[0]) <= pitch3d.half_length + 1e-6
            assert abs(pos[2]) <= pitch3d.half_width + 1e-6

    def test_goal_detection(self, pitch3d):
        assert physics3d.detect_goal([-pitch3d.half_length + 0.5, 0.2, 0.0],
                                     pitch3d) == "left"
        assert physics3d.detect_goal([pitch3d.half_length - 0.5, 0.2, 0.0],
                                     pitch3d) == "right"
        # Between the posts but still out on the pitch
        assert physics3d.detect_goal([0.0, 0.2, 0.0], pitch3d) is None
        # Past the goal line but wide of the posts
        assert physics3d.detect_goal([-pitch3d.half_length + 0.5, 0.2, 20.0],
                                     pitch3d) is None

    def test_kickoff_state_is_on_the_centre_spot(self, pitch3d):
        pos, vel = physics3d.kickoff_state()
        assert pos[0] == 0.0 and pos[2] == 0.0
        assert pos[1] > 0
        assert any(vel)
