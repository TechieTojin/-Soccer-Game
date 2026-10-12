"""Unit tests for the VR stereo camera maths and the team formations.

Both modules are pure maths, so the VR fixes (audit finding B13) and the
formation fix (B9) are verifiable without opening a window.
"""

import math

import pytest

from soccer_core import formations, stereo
from soccer_core.pitch import Pitch2D, Pitch3D


# ---------------------------------------------------------------------------
# Stereo camera (audit finding B13)
# ---------------------------------------------------------------------------

class TestViewportAspect:

    def test_split_screen_uses_half_the_width(self):
        """Each eye renders into a width/2 x height viewport.

        The original computed width / (height/2) = 3.56 for 1920x1080,
        while the real viewport aspect is 0.89 - a badly squashed picture.
        """
        assert stereo.viewport_aspect(1920, 1080, split_screen=True) == pytest.approx(
            (1920 / 2) / 1080)

    def test_mono_uses_the_full_width(self):
        assert stereo.viewport_aspect(1920, 1080, split_screen=False) == pytest.approx(
            1920 / 1080)

    def test_split_aspect_is_half_the_mono_aspect(self):
        split = stereo.viewport_aspect(1280, 720, split_screen=True)
        mono = stereo.viewport_aspect(1280, 720, split_screen=False)
        assert split == pytest.approx(mono / 2)


class TestLookDirection:

    def test_default_looks_down_negative_z(self):
        x, y, z = stereo.direction_from_angles(0.0, 0.0)
        assert (x, y, z) == pytest.approx((0.0, 0.0, -1.0), abs=1e-9)

    def test_direction_is_always_unit_length(self):
        for yaw in range(0, 360, 23):
            for pitch in (-89, -45, 0, 30, 89):
                direction = stereo.direction_from_angles(yaw, pitch)
                assert math.sqrt(sum(c * c for c in direction)) == pytest.approx(1.0)

    def test_yaw_turns_horizontally(self):
        direction = stereo.direction_from_angles(90.0, 0.0)
        assert direction[0] == pytest.approx(1.0, abs=1e-9)
        assert direction[2] == pytest.approx(0.0, abs=1e-9)

    def test_pitch_is_clamped_so_the_view_cannot_flip(self):
        assert stereo.clamp_pitch(120.0) == stereo.MAX_PITCH_DEGREES
        assert stereo.clamp_pitch(-120.0) == -stereo.MAX_PITCH_DEGREES
        # Even an out-of-range request stays unit length and upright
        direction = stereo.direction_from_angles(0.0, 200.0)
        assert direction[1] < 1.0


class TestEyeSeparation:

    def test_eyes_are_separated_across_the_view_not_along_it(self):
        """The original offset the eyes along world X. After turning 90
        degrees that is the view direction, which destroys stereo."""
        look = stereo.direction_from_angles(90.0, 0.0)   # looking down +X
        left = stereo.eye_position([0, 1.7, 0], look, 0.064, "left")
        right = stereo.eye_position([0, 1.7, 0], look, 0.064, "right")

        separation = [r - l for r, l in zip(right, left, strict=True)]
        along_view = sum(s * d for s, d in zip(separation, look, strict=True))
        assert along_view == pytest.approx(0.0, abs=1e-9)

    def test_eyes_are_symmetric_about_the_camera(self):
        look = stereo.direction_from_angles(33.0, -12.0)
        camera = [4.0, 1.7, -8.0]
        left = stereo.eye_position(camera, look, 0.064, "left")
        right = stereo.eye_position(camera, look, 0.064, "right")
        midpoint = [(l + r) / 2 for l, r in zip(left, right, strict=True)]
        assert midpoint == pytest.approx(camera, abs=1e-9)

    def test_separation_equals_the_ipd(self):
        look = stereo.direction_from_angles(10.0, 5.0)
        left = stereo.eye_position([0, 1.7, 0], look, 0.064, "left")
        right = stereo.eye_position([0, 1.7, 0], look, 0.064, "right")
        assert math.dist(left, right) == pytest.approx(0.064)

    def test_centre_eye_is_the_camera_itself(self):
        camera = [1.0, 1.7, 2.0]
        look = stereo.direction_from_angles(0.0, 0.0)
        assert stereo.eye_position(camera, look, 0.064, "centre") == pytest.approx(camera)

    def test_right_vector_is_perpendicular_to_the_view(self):
        look = stereo.direction_from_angles(47.0, 20.0)
        right = stereo.right_vector(look)
        assert sum(r * l for r, l in zip(right, look, strict=True)) == pytest.approx(0.0, abs=1e-9)
        assert math.sqrt(sum(r * r for r in right)) == pytest.approx(1.0)


class TestMovement:

    def test_walking_forward_follows_the_view(self):
        look = stereo.direction_from_angles(0.0, 0.0)     # down -Z
        moved = stereo.move([0.0, 1.7, 0.0], look, forward=5.0, strafe=0.0)
        assert moved[2] == pytest.approx(-5.0)
        assert moved[0] == pytest.approx(0.0, abs=1e-9)

    def test_movement_stays_at_a_constant_height(self):
        """Looking up or down must not lift the viewer off the ground."""
        look = stereo.direction_from_angles(0.0, 60.0)
        moved = stereo.move([0.0, 1.7, 0.0], look, forward=5.0, strafe=0.0)
        assert moved[1] == pytest.approx(1.7)

    def test_strafing_moves_sideways(self):
        look = stereo.direction_from_angles(0.0, 0.0)
        moved = stereo.move([0.0, 1.7, 0.0], look, forward=0.0, strafe=3.0)
        assert moved[0] == pytest.approx(3.0)
        assert moved[2] == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Formations (audit finding B9)
# ---------------------------------------------------------------------------

class TestFormations3D:

    def test_each_team_has_eleven_players(self):
        pitch = Pitch3D()
        assert len(formations.formation_433(pitch, "red")) == 11
        assert len(formations.formation_433(pitch, "blue")) == 11

    def test_every_player_is_inside_the_pitch(self):
        """Goalkeepers used to stand at x = +-60 on a +-52.5 pitch. (B9)"""
        pitch = Pitch3D()
        for team in ("red", "blue"):
            for x, z in formations.formation_433(pitch, team):
                assert pitch.contains(x, z), f"{team} player at ({x}, {z}) is off the pitch"

    def test_teams_defend_opposite_ends(self):
        pitch = Pitch3D()
        red = formations.formation_433(pitch, "red")
        blue = formations.formation_433(pitch, "blue")
        assert all(x < 0 for x, _ in red)
        assert all(x > 0 for x, _ in blue)

    def test_goalkeepers_are_nearest_their_own_goal_line(self):
        pitch = Pitch3D()
        red = formations.formation_433(pitch, "red")
        keeper_x = red[-1][0]
        assert keeper_x == min(x for x, _ in red)
        assert abs(keeper_x) < pitch.half_length

    def test_scene_players_returns_both_teams_with_colours(self):
        pitch = Pitch3D()
        players = formations.scene_players(pitch)
        assert len(players) == 22
        colours = {colour for _, _, colour in players}
        assert colours == {formations.RED, formations.BLUE}


class TestFormations2D:

    def test_eleven_players_per_team(self):
        pitch = Pitch2D()
        assert len(formations.formation_442(pitch, "red")) == 11
        assert len(formations.formation_442(pitch, "blue")) == 11

    def test_every_player_is_inside_the_pitch_markings(self):
        pitch = Pitch2D()
        for team in ("red", "blue"):
            for x, y in formations.formation_442(pitch, team):
                assert pitch.left <= x <= pitch.right
                assert pitch.top <= y <= pitch.bottom

    def test_teams_start_in_their_own_half(self):
        pitch = Pitch2D()
        centre_x = pitch.width / 2
        assert all(x < centre_x for x, _ in formations.formation_442(pitch, "red"))
        assert all(x > centre_x for x, _ in formations.formation_442(pitch, "blue"))

    def test_formation_is_spread_over_the_pitch(self):
        """The old grid layout bunched everyone into the top half."""
        pitch = Pitch2D()
        ys = [y for _, y in formations.formation_442(pitch, "red")]
        assert max(ys) - min(ys) > (pitch.bottom - pitch.top) * 0.5

    def test_goalkeeper_is_the_deepest_player(self):
        pitch = Pitch2D()
        red = formations.formation_442(pitch, "red")
        assert red[0][0] == min(x for x, _ in red)   # index 0 is the GK
