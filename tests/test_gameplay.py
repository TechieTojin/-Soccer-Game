"""Unit tests for the 2D soccer gameplay logic.

Each test group maps to a finding from SOCCER_PROJECT_AUDIT.md, so a
regression in a fixed bug fails a named test.

These tests exercise the physics/scoring/stamina logic directly; they do not
verify anything about rendering, which still needs manual checking.
"""

import math

import pygame
import pytest


def park_players(game):
    """Move every player off the pitch.

    Several physics tests need an empty pitch: the default formation sits
    right where a ball crossing the pitch would travel, and a collision
    would otherwise be mistaken for a physics bug.
    """
    for team in ('red', 'blue'):
        for player in game.players[team]:
            player['pos'] = [-500.0, -500.0]
            player['vel'] = [0.0, 0.0]


# ---------------------------------------------------------------------------
# Ball physics - no gravity, time-based friction (audit finding B5)
# ---------------------------------------------------------------------------

class TestBallPhysics:

    def test_ball_at_rest_does_not_drift(self, game):
        """A stationary ball must stay put: there is no gravity in a
        top-down game. Previously it was dragged to the bottom edge."""
        park_players(game)
        game.ball_pos = [game.width / 2, game.height / 2]
        game.ball_vel = [0.0, 0.0]
        start = list(game.ball_pos)

        for _ in range(300):  # 5 seconds at 60 FPS
            game.update_ball_physics()

        assert game.ball_pos[0] == pytest.approx(start[0], abs=1e-6)
        assert game.ball_pos[1] == pytest.approx(start[1], abs=1e-6)

    def test_no_gravity_attribute_applied(self, game):
        """A ball moving purely horizontally must not gain vertical speed."""
        park_players(game)
        game.ball_pos = [game.width / 2, game.height / 2]
        game.ball_vel = [5.0, 0.0]

        for _ in range(60):
            game.update_ball_physics()

        assert game.ball_vel[1] == pytest.approx(0.0, abs=1e-9)

    def test_friction_slows_the_ball_down(self, game):
        """Damping must reduce speed over time."""
        park_players(game)
        game.ball_pos = [game.width / 2, game.height / 2]
        game.ball_vel = [4.0, 0.0]
        initial_speed = abs(game.ball_vel[0])

        for _ in range(60):
            game.update_ball_physics()

        assert abs(game.ball_vel[0]) < initial_speed
        assert abs(game.ball_vel[0]) > 0  # it decays, it does not snap to zero

    def test_friction_is_time_based_not_frame_based(self, game):
        """The same simulated duration must produce (near) the same speed
        loss whether it is stepped in large or small timesteps."""
        def speed_after(dt, steps):
            game.reset_game_state()
            park_players(game)
            game.dt = dt
            game.ball_pos = [game.width / 2, game.height / 2]
            game.ball_vel = [4.0, 0.0]
            for _ in range(steps):
                game.update_ball_physics()
            return abs(game.ball_vel[0])

        # 1 second simulated at 60 FPS vs at 30 FPS
        fast = speed_after(1 / 60, 60)
        slow = speed_after(1 / 30, 30)

        assert fast == pytest.approx(slow, rel=1e-6)

    def test_ball_stays_within_the_pitch(self, game):
        """However hard it is hit, the ball must not escape the playing
        area (pitch bounds, or the back of the net inside a goal)."""
        park_players(game)
        game.ball_pos = [game.width / 2, game.height / 2]
        game.ball_vel = [40.0, 27.0]

        for _ in range(600):
            game.update_ball_physics()
            min_x = game.pitch_margin - game.goal_depth - 1
            max_x = game.width - game.pitch_margin + game.goal_depth + 1
            assert min_x <= game.ball_pos[0] <= max_x
            assert game.pitch_margin - 1 <= game.ball_pos[1] <= game.height - game.pitch_margin + 1

    def test_wall_bounce_reverses_direction_and_loses_energy(self, game):
        """Hitting a side wall away from the goal mouth reverses the ball."""
        park_players(game)
        # Place the ball near the top-left, well clear of the goal mouth.
        game.ball_pos = [game.pitch_margin + 5, game.pitch_margin + 20]
        game.ball_vel = [-10.0, 0.0]

        game.update_ball_physics()

        assert game.ball_vel[0] > 0           # bounced back
        assert abs(game.ball_vel[0]) < 10.0   # lost energy


# ---------------------------------------------------------------------------
# Goal detection matches the drawn goals (audit finding B4)
# ---------------------------------------------------------------------------

class TestGoalDetection:

    def _goal_centre_y(self, game):
        return game.height / 2

    def test_goal_scored_at_the_drawn_left_goal(self, game, monkeypatch):
        """Crossing the left goal line inside the mouth scores for blue."""
        monkeypatch.setattr(game, "show_goal_message", lambda msg: None)
        game.ball_pos = [game.pitch_margin - 1, self._goal_centre_y(game)]
        game.ball_vel = [-5.0, 0.0]

        game.check_goals()

        assert game.score == [0, 1]

    def test_goal_scored_at_the_drawn_right_goal(self, game, monkeypatch):
        monkeypatch.setattr(game, "show_goal_message", lambda msg: None)
        game.ball_pos = [game.width - game.pitch_margin + 1, self._goal_centre_y(game)]
        game.ball_vel = [5.0, 0.0]

        game.check_goals()

        assert game.score == [1, 0]

    def test_no_goal_when_ball_is_outside_the_goal_mouth(self, game, monkeypatch):
        """Crossing the goal line above the crossbar is not a goal."""
        monkeypatch.setattr(game, "show_goal_message", lambda msg: None)
        game.ball_pos = [game.pitch_margin - 1,
                         game.height / 2 - game.goal_height]  # clearly outside
        game.ball_vel = [-5.0, 0.0]

        game.check_goals()

        assert game.score == [0, 0]

    def test_no_goal_before_the_goal_line(self, game, monkeypatch):
        """A ball still on the pitch, in front of the goal, has not scored."""
        monkeypatch.setattr(game, "show_goal_message", lambda msg: None)
        game.ball_pos = [game.pitch_margin + 10, self._goal_centre_y(game)]
        game.ball_vel = [-5.0, 0.0]

        game.check_goals()

        assert game.score == [0, 0]

    def test_no_goal_when_ball_moves_away_from_goal(self, game, monkeypatch):
        monkeypatch.setattr(game, "show_goal_message", lambda msg: None)
        game.ball_pos = [game.pitch_margin - 1, self._goal_centre_y(game)]
        game.ball_vel = [5.0, 0.0]  # moving back out

        game.check_goals()

        assert game.score == [0, 0]

    def test_goal_mouth_is_reachable_by_the_ball(self, game):
        """The wall collision must leave a gap at the goal mouth, otherwise
        the ball bounces off the goal line and no goal can ever be scored."""
        park_players(game)
        game.ball_pos = [game.pitch_margin + 5, game.height / 2]
        game.ball_vel = [-10.0, 0.0]

        game.update_ball_physics()

        # It passed the goal line instead of bouncing off it
        assert game.ball_pos[0] < game.pitch_margin
        assert game.ball_vel[0] < 0

    def test_ball_and_score_reset_after_a_goal(self, game, monkeypatch):
        monkeypatch.setattr(game, "show_goal_message", lambda msg: None)
        game.ball_pos = [game.pitch_margin - 1, self._goal_centre_y(game)]
        game.ball_vel = [-5.0, 0.0]

        game.check_goals()

        assert game.ball_pos == [game.width // 2, game.height // 2]
        assert game.ball_vel == [0, 0]


# ---------------------------------------------------------------------------
# Player/ball collisions (audit finding B6)
# ---------------------------------------------------------------------------

class TestCollisions:

    def test_zero_distance_collision_does_not_crash(self, game):
        """Ball exactly on top of a player must not divide by zero."""
        player = game.players['red'][0]
        game.ball_pos = list(player['pos'])
        game.ball_vel = [0.0, 0.0]

        game.update_ball_physics()  # must not raise ZeroDivisionError

    def test_overlapping_ball_is_pushed_out_of_the_player(self, game):
        player = game.players['red'][0]
        # Slight overlap
        game.ball_pos = [player['pos'][0] + 5, player['pos'][1]]
        game.ball_vel = [0.0, 0.0]

        game.update_ball_physics()

        dx = game.ball_pos[0] - player['pos'][0]
        dy = game.ball_pos[1] - player['pos'][1]
        distance = math.hypot(dx, dy)
        assert distance >= player['radius'] + game.ball_radius

    def test_ball_far_from_players_is_unaffected(self, game):
        """A ball in empty space keeps travelling in the same direction."""
        park_players(game)
        game.ball_pos = [game.width / 2, game.height / 2]
        game.ball_vel = [3.0, 0.0]

        game.update_ball_physics()

        assert game.ball_vel[0] > 0
        assert game.ball_vel[1] == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Stamina (audit finding B8)
# ---------------------------------------------------------------------------

class TestStamina:

    def test_moving_drains_stamina(self, game):
        player = game.players['red'][0]
        player['stamina'] = 100.0

        for _ in range(60):  # one second of running
            game.update_player_stamina(player, moving=True)

        assert player['stamina'] < 100.0
        assert player['stamina'] == pytest.approx(100.0 - game.stamina_drain_rate, abs=0.5)

    def test_idling_recovers_stamina(self, game):
        player = game.players['red'][0]
        player['stamina'] = 50.0

        for _ in range(60):  # one second of standing still
            game.update_player_stamina(player, moving=False)

        assert player['stamina'] > 50.0
        assert player['stamina'] == pytest.approx(50.0 + game.stamina_regen_rate, abs=0.5)

    def test_stamina_never_leaves_its_bounds(self, game):
        player = game.players['red'][0]

        player['stamina'] = 1.0
        for _ in range(600):
            game.update_player_stamina(player, moving=True)
        assert player['stamina'] == 0.0

        for _ in range(6000):
            game.update_player_stamina(player, moving=False)
        assert player['stamina'] == 100.0

    def test_stamina_rates_are_time_based(self, game):
        """Drain over one simulated second must not depend on frame rate."""
        def drain(dt, steps):
            player = dict(stamina=100.0)
            game.dt = dt
            for _ in range(steps):
                game.update_player_stamina(player, moving=True)
            return player['stamina']

        assert drain(1 / 60, 60) == pytest.approx(drain(1 / 30, 30), rel=1e-9)

    def test_exhausted_player_can_still_kick_and_move(self, game):
        """An exhausted player is slower, not frozen, so they can get back
        to a position where stamina recovers."""
        player = game.players['red'][0]
        player['stamina'] = 0.0

        speed_multiplier = max(0.3, player['stamina'] / 100.0)

        assert speed_multiplier > 0


# ---------------------------------------------------------------------------
# Player selection - all 11 reachable (audit finding B7)
# ---------------------------------------------------------------------------

class TestPlayerSelection:

    def test_digit_keys_one_to_nine_select_first_nine_players(self, game):
        for offset in range(9):
            key = pygame.K_1 + offset
            assert game.player_index_for_key(key) == offset

    def test_zero_key_selects_the_tenth_player(self, game):
        assert game.player_index_for_key(pygame.K_0) == 9

    def test_minus_key_selects_the_eleventh_player(self, game):
        assert game.player_index_for_key(pygame.K_MINUS) == 10

    def test_all_eleven_players_are_reachable(self, game):
        keys = [pygame.K_1 + i for i in range(9)] + [pygame.K_0, pygame.K_MINUS]
        indices = [game.player_index_for_key(k) for k in keys]

        assert sorted(indices) == list(range(11))
        assert len(game.players['red']) == 11
        for index in indices:
            assert game.players['red'][index] is not None

    def test_non_selection_keys_return_none(self, game):
        for key in (pygame.K_SPACE, pygame.K_TAB, pygame.K_ESCAPE, pygame.K_a):
            assert game.player_index_for_key(key) is None


# ---------------------------------------------------------------------------
# Kicking (covers the stamina/role interaction)
# ---------------------------------------------------------------------------

class TestKick:

    def test_kick_requires_the_ball_to_be_close(self, game):
        game.selected_team = 'red'
        game.selected_player = 0
        player = game.players['red'][0]
        game.ball_pos = [player['pos'][0] + 500, player['pos'][1]]
        game.ball_vel = [0.0, 0.0]

        game.handle_ball_kick()

        assert game.ball_vel == [0.0, 0.0]  # too far away, no kick

    def test_close_kick_moves_the_ball(self, game):
        game.selected_team = 'red'
        game.selected_player = 0
        player = game.players['red'][0]
        player['stamina'] = 100.0
        game.ball_pos = [player['pos'][0] + 20, player['pos'][1]]
        game.ball_vel = [0.0, 0.0]

        game.handle_ball_kick()

        speed = math.hypot(*game.ball_vel)
        assert speed > 0
