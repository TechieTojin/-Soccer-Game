"""
Soccer AR/VR Experience - 2D game
Developed by Tojin Varkey Simson and Jaiby Mariya Jospeh
A modern soccer game with AR and VR capabilities
"""

import pygame
from pygame.locals import *
import math
import random
import cv2
import time

from soccer_core import formations, physics2d
from soccer_core.pitch import Pitch2D

# NOTE: this module previously imported OpenGL, numpy, sys and os, none of
# which it uses. Dropping them means the 2D game runs without PyOpenGL
# installed. (Audit finding B20)
#
# The rules (ball physics, collisions, scoring, stamina) live in
# soccer_core/physics2d.py so they can be tested without a display; this
# module owns the pygame window, input and drawing.

class SoccerGame:
    def __init__(self, enable_camera=True):
        # Initialize Pygame
        pygame.init()
        # Initialize display without OpenGL first
        self.width, self.height = 1280, 720  # Lower resolution
        pygame.display.set_mode((self.width, self.height), pygame.DOUBLEBUF)
        pygame.display.set_caption("Soccer AR/VR Game")

        # Game modes
        self.mode = "menu"  # menu, ar, vr, 2d
        self.running = True

        # Modern theme colors
        self.colors = {
            'background': (18, 20, 24),
            'panel': (28, 31, 38),
            'panel_light': (38, 42, 51),
            'accent': (0, 200, 110),
            'text': (235, 238, 242),
            'muted': (150, 158, 170),
            'button': (38, 42, 51),
            'button_hover': (54, 60, 72),
            'field': (34, 118, 52),
            'field_stripe': (38, 130, 58),
            'lines': (236, 244, 238),
            'red': (226, 74, 74),
            'blue': (74, 124, 232),
            'ball': (252, 252, 250),
            'shadow': (0, 0, 0),
        }

        # Initialize fonts. SysFont falls back to the default font when the
        # named families are missing, so this is safe on any platform.
        self.font_title = pygame.font.SysFont("segoeui,dejavusans,arial", 64, bold=True)
        self.font_large = pygame.font.SysFont("segoeui,dejavusans,arial", 44, bold=True)
        self.font_medium = pygame.font.SysFont("segoeui,dejavusans,arial", 28)
        self.font_small = pygame.font.SysFont("segoeui,dejavusans,arial", 20)
        self.font_tiny = pygame.font.SysFont("segoeui,dejavusans,arial", 15)
        self.font_mono = pygame.font.SysFont("consolas,dejavusansmono,couriernew", 30, bold=True)

        # Menu state: driven by both keyboard and mouse. (Audit finding B20)
        self.menu_items = [
            ("Play Match", "play"),
            ("How to Play", "help"),
            ("Quit", "quit"),
        ]
        self.menu_index = 0

        # Non-blocking overlays
        self.banner_text = None       # goal celebration text
        self.banner_timer = 0.0       # seconds remaining
        self.paused = False

        # Game state
        self.reset_game_state()
        self.clock = pygame.time.Clock()

        # Initialize camera for AR mode
        # `enable_camera=False` lets tests and headless tooling skip touching
        # a webcam device entirely.
        self.cap = None
        self.ar_available = False
        if enable_camera:
            try:
                self.cap = cv2.VideoCapture(0)
                if not self.cap.isOpened():
                    print("Warning: No camera found. AR mode will be disabled.")
                    self.ar_available = False
                else:
                    self.ar_available = True
            except Exception as e:
                print(f"Camera initialization failed ({e}). AR mode will be disabled.")
                self.ar_available = False

        # Print the controls this game actually implements
        # ASCII only: a Windows console using the cp1252 code page raises
        # UnicodeEncodeError on emoji, which crashed the game on start-up.
        print("\n=== Soccer 2D Game Controls ===")
        print("  Arrow keys: Move selected player")
        print("  Space: Kick ball")
        print("  Tab: Switch team")
        print("  1-9, 0, -: Select player 1-11")
        print("  ESC: Back to menu / exit")

    def reset_game_state(self):
        """Initialize or reset game state"""
        self.score = [0, 0]
        self.game_time = 90  # 90-second match

        # Pitch / goal geometry, shared by drawing and gameplay logic so the
        # scoring check always matches what is drawn on screen. (Audit finding B4)
        self.pitch = Pitch2D(width=self.width, height=self.height,
                             margin=100, goal_height=100, goal_depth=20)
        # Kept as attributes because the drawing code and tests read them.
        self.pitch_margin = self.pitch.margin
        self.goal_height = self.pitch.goal_height
        self.goal_depth = self.pitch.goal_depth

        # Ball properties
        self.ball_pos = [self.width//2, self.height//2]
        self.ball_vel = [0, 0]
        self.ball_radius = 8
        self.ball_mass = 1.0

        # Players
        self.players = {
            'red': [],   # Team 1 (left)
            'blue': []   # Team 2 (right)
        }

        # Create players in a 4-4-2 derived from the pitch, so the squads
        # line up like a football team rather than a grid in one corner.
        for team in ('red', 'blue'):
            for i, (x, y) in enumerate(formations.formation_442(self.pitch, team)):
                self.players[team].append({
                    'pos': [float(x), float(y)],
                    'vel': [0.0, 0.0],
                    'radius': 15,
                    'mass': 1.0,
                    'speed': 5.0,
                    'stamina': 100.0,
                    'role': self.get_player_role(i)
                })

        # Player control
        self.selected_team = 'red'
        self.selected_player = 0
        self.player_speed = 5
        self.ball_speed = 15
        # Air resistance is expressed as a per-frame (60 FPS) decay factor and
        # is converted to a time-based damping factor in update_ball_physics,
        # so ball speed loss no longer depends on the actual frame rate.
        self.air_resistance = 0.99
        # NOTE: there is no vertical ("up/down off the table") axis in this
        # top-down game, so there is no gravity on the ball. (Audit finding B5)

        # Stamina drain/regen rates, in percent per second
        self.stamina_drain_rate = 15.0
        self.stamina_regen_rate = 8.0

        # Game physics
        self.last_update = time.time()
        self.dt = 0.016  # Target time step (60 FPS)

    def get_player_role(self, index):
        """Assign player roles based on position"""
        roles = {
            0: "GK",  # Goalkeeper
            1: "LB",  # Left Back
            2: "CB",  # Center Back
            3: "CB",  # Center Back
            4: "RB",  # Right Back
            5: "LM",  # Left Midfielder
            6: "CM",  # Center Midfielder
            7: "CM",  # Center Midfielder
            8: "RM",  # Right Midfielder
            9: "ST",  # Striker
            10: "ST"  # Striker
        }
        return roles.get(index, "UNK")

    def update_player_stamina(self, player, moving):
        """Update a single player's stamina in place.

        Drains at `self.stamina_drain_rate` percent/second while moving, and
        recovers at `self.stamina_regen_rate` percent/second while idle.
        Delegates to soccer_core.physics2d so the rule is testable on its own.
        """
        player['stamina'] = physics2d.update_stamina(
            player['stamina'], moving, self.dt,
            self.stamina_drain_rate, self.stamina_regen_rate)

    # ------------------------------------------------------------------
    # Menu
    # ------------------------------------------------------------------

    def menu_button_rect(self, index):
        """Screen rectangle of menu entry `index`."""
        button_width, button_height, gap = 320, 58, 16
        top = 330 + index * (button_height + gap)
        return pygame.Rect(self.width // 2 - button_width // 2, top,
                           button_width, button_height)

    def activate_menu_item(self, index):
        """Run the action for menu entry `index`."""
        _, action = self.menu_items[index]
        if action == "play":
            self.reset_game_state()
            self.mode = "2d_game"
        elif action == "help":
            self.mode = "help"
        elif action == "quit":
            self.running = False

    def draw_menu(self):
        """Draw the main menu.

        The menu is driven by `self.menu_index`; both the mouse and the
        arrow keys move it, and activation happens on a key/button *press*
        rather than by polling the mouse every frame, which used to fire the
        same button many times in a row. (Audit finding B20)
        """
        self.display = pygame.display.get_surface()
        self.display.fill(self.colors['background'])

        # Decorative accent bar behind the title
        pygame.draw.rect(self.display, self.colors['panel'],
                         (0, 0, self.width, 250))
        pygame.draw.rect(self.display, self.colors['accent'],
                         (0, 248, self.width, 3))

        title = self.font_title.render("SOCCER", True, self.colors['text'])
        self.display.blit(title, title.get_rect(center=(self.width // 2, 110)))

        subtitle = self.font_medium.render("AR / VR Experience  -  2D Match",
                                           True, self.colors['accent'])
        self.display.blit(subtitle, subtitle.get_rect(center=(self.width // 2, 170)))

        for index, (label, _) in enumerate(self.menu_items):
            rect = self.menu_button_rect(index)
            selected = index == self.menu_index
            colour = self.colors['button_hover'] if selected else self.colors['button']
            pygame.draw.rect(self.display, colour, rect, border_radius=10)
            if selected:
                pygame.draw.rect(self.display, self.colors['accent'], rect, 2,
                                 border_radius=10)
                # Accent marker on the selected row
                pygame.draw.rect(self.display, self.colors['accent'],
                                 (rect.x + 8, rect.centery - 12, 4, 24),
                                 border_radius=2)

            text_colour = self.colors['text'] if selected else self.colors['muted']
            text = self.font_medium.render(label, True, text_colour)
            self.display.blit(text, text.get_rect(center=rect.center))

        hint = self.font_small.render(
            "Arrow keys or mouse to choose  -  Enter / click to select  -  Esc to quit",
            True, self.colors['muted'])
        self.display.blit(hint, hint.get_rect(center=(self.width // 2, self.height - 40)))

    def draw_help(self):
        """Draw the controls screen."""
        self.display = pygame.display.get_surface()
        self.display.fill(self.colors['background'])

        title = self.font_large.render("How to Play", True, self.colors['accent'])
        self.display.blit(title, title.get_rect(center=(self.width // 2, 90)))

        rows = [
            ("Arrow keys", "Move the selected player"),
            ("Space", "Kick the ball (must be close enough)"),
            ("Tab", "Switch to the other team"),
            ("1 - 9, 0, -", "Select player 1 to 11"),
            ("P", "Pause / resume"),
            ("R", "Restart the match"),
            ("Esc", "Back to the menu"),
        ]

        panel = pygame.Rect(self.width // 2 - 330, 150, 660, len(rows) * 46 + 40)
        pygame.draw.rect(self.display, self.colors['panel'], panel, border_radius=12)

        y = panel.y + 32
        for key, description in rows:
            key_text = self.font_medium.render(key, True, self.colors['accent'])
            self.display.blit(key_text, (panel.x + 32, y - key_text.get_height() // 2))
            description_text = self.font_medium.render(description, True, self.colors['text'])
            self.display.blit(description_text,
                              (panel.x + 230, y - description_text.get_height() // 2))
            y += 46

        note = self.font_small.render(
            "Stamina drains while running and recovers while standing still.",
            True, self.colors['muted'])
        self.display.blit(note, note.get_rect(center=(self.width // 2, panel.bottom + 40)))

        hint = self.font_small.render("Press Esc to go back", True, self.colors['muted'])
        self.display.blit(hint, hint.get_rect(center=(self.width // 2, self.height - 40)))

    def show_message(self, message, duration=2000):
        """Show a transient banner without blocking the game loop.

        This used to spin its own event loop for `duration` milliseconds,
        which froze the simulation and swallowed input. It now just arms the
        overlay that `draw_banner` renders. (Audit finding B20)
        """
        self.banner_text = message
        self.banner_timer = duration / 1000.0

    def draw_banner(self):
        """Draw the transient banner (goal celebration, notices)."""
        if not self.banner_text or self.banner_timer <= 0:
            return

        # Fade out over the last half second.
        alpha = int(255 * min(1.0, self.banner_timer / 0.5))
        text = self.font_large.render(self.banner_text, True, self.colors['text'])

        panel_width = text.get_width() + 80
        panel_height = text.get_height() + 40
        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel.fill((*self.colors['panel'], min(230, alpha)))
        pygame.draw.rect(panel, (*self.colors['accent'], alpha),
                         panel.get_rect(), 3, border_radius=12)
        panel.blit(text, text.get_rect(center=panel.get_rect().center))
        panel.set_alpha(alpha)

        self.display.blit(panel, panel.get_rect(
            center=(self.width // 2, self.height // 2 - 60)))

    def handle_events(self):
        """Handle pygame events for whichever screen is active."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.mode != "menu":
                        self.mode = "menu"
                        self.paused = False
                    else:
                        self.running = False
                elif self.mode == "menu":
                    self.handle_menu_key(event.key)
                elif self.mode == "2d_game":
                    self.handle_game_key(event.key)
            elif event.type == pygame.MOUSEMOTION and self.mode == "menu":
                # Hovering a button moves the selection, so mouse and
                # keyboard never disagree about what is highlighted.
                for index in range(len(self.menu_items)):
                    if self.menu_button_rect(index).collidepoint(event.pos):
                        self.menu_index = index
                        break
            elif (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                  and self.mode == "menu"):
                for index in range(len(self.menu_items)):
                    if self.menu_button_rect(index).collidepoint(event.pos):
                        self.menu_index = index
                        self.activate_menu_item(index)
                        break

    def handle_menu_key(self, key):
        """Keyboard navigation for the main menu."""
        if key in (pygame.K_UP, pygame.K_w):
            self.menu_index = (self.menu_index - 1) % len(self.menu_items)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.menu_index = (self.menu_index + 1) % len(self.menu_items)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.activate_menu_item(self.menu_index)

    def handle_game_key(self, key):
        """Keyboard controls during a match."""
        if key == pygame.K_SPACE:
            if not self.paused:
                self.handle_ball_kick()
        elif key == pygame.K_TAB:
            self.selected_team = 'blue' if self.selected_team == 'red' else 'red'
        elif key == pygame.K_p:
            self.paused = not self.paused
        elif key == pygame.K_r:
            self.reset_game_state()
            self.paused = False
        else:
            player_index = self.player_index_for_key(key)
            if player_index is not None:
                self.selected_player = player_index

    def player_index_for_key(self, key):
        """Map a pressed key to a squad index (0-10), or None if it doesn't
        select a player. There are 11 players per team but only 10 digit
        keys, so 0 selects the 10th player and '-' selects the 11th.
        (Audit finding B7: players 10-11 were previously unreachable.)
        """
        if pygame.K_1 <= key <= pygame.K_9:
            return key - pygame.K_1          # 1-9 -> players 0-8
        if key == pygame.K_0:
            return 9                          # 0 -> player 9 (10th player)
        if key == pygame.K_MINUS:
            return 10                         # - -> player 10 (11th player)
        return None

    def handle_ball_kick(self):
        """Handle ball kicking with more realistic physics"""
        player = self.players[self.selected_team][self.selected_player]
        dx = self.ball_pos[0] - player['pos'][0]
        dy = self.ball_pos[1] - player['pos'][1]
        dist = math.sqrt(dx*dx + dy*dy)

        # Only kick if close enough
        if dist < player['radius'] + self.ball_radius + 20:
            # Calculate kick power based on player's stamina and role
            power_multiplier = 1.0
            if player['role'] in ['ST', 'CM']:
                power_multiplier = 1.2
            elif player['role'] == 'GK':
                power_multiplier = 1.5

            # Calculate kick direction and power
            angle = math.atan2(dy, dx)
            power = player['stamina'] / 100.0 * power_multiplier

            # Apply kick force
            self.ball_vel[0] = math.cos(angle) * self.ball_speed * power
            self.ball_vel[1] = math.sin(angle) * self.ball_speed * power

            # Add some randomness based on player's stamina
            randomness = (100 - player['stamina']) / 100.0
            self.ball_vel[0] += random.uniform(-2, 2) * randomness
            self.ball_vel[1] += random.uniform(-2, 2) * randomness

            # Reduce player's stamina
            player['stamina'] = max(0, player['stamina'] - 10)

    def update_game_state(self):
        """Update game physics and state with more realistic movement"""
        current_time = time.time()
        self.dt = min(current_time - self.last_update, 0.1)  # Cap dt to prevent large jumps
        self.last_update = current_time

        # Update selected player position based on keyboard input
        keys = pygame.key.get_pressed()
        player = self.players[self.selected_team][self.selected_player]

        # Calculate movement direction
        move_x = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
        move_y = keys[pygame.K_DOWN] - keys[pygame.K_UP]

        # Normalize diagonal movement
        if move_x != 0 and move_y != 0:
            move_x *= 0.7071  # 1/sqrt(2)
            move_y *= 0.7071

        # Apply movement with stamina effect. A tired player is slower but
        # never fully immobilised, so they can still move back to recover.
        speed_multiplier = physics2d.speed_multiplier(player['stamina'])
        player['vel'][0] = move_x * self.player_speed * speed_multiplier
        player['vel'][1] = move_y * self.player_speed * speed_multiplier

        # Update player position
        player['pos'][0] += player['vel'][0] * self.dt * 60
        player['pos'][1] += player['vel'][1] * self.dt * 60

        # Keep player in bounds
        player['pos'][0] = max(0, min(self.width, player['pos'][0]))
        player['pos'][1] = max(0, min(self.height, player['pos'][1]))

        # Update stamina: drains while moving, recovers while idle, both
        # scaled by real elapsed time rather than a fixed per-frame amount.
        # (Audit finding B8: previously movement never drained stamina.)
        moving = move_x != 0 or move_y != 0
        self.update_player_stamina(player, moving)

        # Update ball physics
        self.update_ball_physics()

        # Check for goals
        self.check_goals()

        # Count the goal banner down (it is an overlay, not a pause)
        if self.banner_timer > 0:
            self.banner_timer = max(0.0, self.banner_timer - self.dt)
            if self.banner_timer == 0:
                self.banner_text = None

        # Update game time
        if self.game_time > 0:
            self.game_time -= self.dt

    def all_players(self):
        """Every player on the pitch, both teams."""
        return [player for team in ('red', 'blue') for player in self.players[team]]

    def update_ball_physics(self):
        """Advance the ball one tick.

        The rules live in soccer_core.physics2d: time-based damping, no
        gravity (this is a top-down view), walls with gaps at the goal
        mouths, and player collisions guarded against a zero-distance
        divide. (Audit findings B4, B5, B6)
        """
        physics2d.step_ball(
            self.ball_pos, self.ball_vel, self.ball_radius,
            self.all_players(), self.pitch, self.air_resistance, self.dt)

    def check_goals(self):
        """Score a goal when the ball crosses a goal line between the posts.

        The goal line used is exactly the one `draw_goals` draws, because
        both read the same Pitch2D. (Audit finding B4)
        """
        side = physics2d.detect_goal(self.ball_pos, self.ball_vel, self.pitch)
        if side is None:
            return

        if side == "left":
            self.score[1] += 1
            message = "Blue Team Scores!"
        else:
            self.score[0] += 1
            message = "Red Team Scores!"

        self.reset_ball()
        self.show_goal_message(message)

    def show_goal_message(self, message):
        """Celebrate a goal with a short, non-blocking overlay."""
        self.show_message(message, 1600)

    def reset_ball(self):
        """Put the ball on the centre spot and both teams back in shape."""
        self.ball_pos = [self.width//2, self.height//2]
        self.ball_vel = [0, 0]

        # Same formation helper as kick-off, so the two cannot drift apart.
        for team in ('red', 'blue'):
            positions = formations.formation_442(self.pitch, team)
            for player, (x, y) in zip(self.players[team], positions, strict=True):
                player['pos'] = [float(x), float(y)]
                player['vel'] = [0.0, 0.0]

    # ------------------------------------------------------------------
    # Match rendering
    # ------------------------------------------------------------------

    def draw_2d_game(self):
        """Draw the match: pitch, goals, players, ball and HUD."""
        self.display = pygame.display.get_surface()
        self.display.fill(self.colors['background'])

        self.draw_pitch()
        self.draw_field_lines()
        self.draw_goals()
        self.draw_players()
        self.draw_ball()
        self.draw_ui()
        self.draw_banner()

        if self.game_time <= 0:
            self.show_game_over()
        elif self.paused:
            self.draw_pause_overlay()

    def draw_pitch(self):
        """Draw the grass, with mowing stripes inside the playing area."""
        pitch = self.pitch

        # Grass surround, wide enough to sit behind the goals.
        surround = pygame.Rect(pitch.left, pitch.top,
                               pitch.right - pitch.left,
                               pitch.bottom - pitch.top).inflate(80, 80)
        pygame.draw.rect(self.display, self.colors['field'], surround)

        # Mowing stripes across the pitch itself.
        stripes = 10
        stripe_width = (pitch.right - pitch.left) / stripes
        for index in range(stripes):
            if index % 2 == 0:
                continue
            x = pitch.left + index * stripe_width
            pygame.draw.rect(self.display, self.colors['field_stripe'],
                             (x, pitch.top, math.ceil(stripe_width),
                              pitch.bottom - pitch.top))

    def draw_field_lines(self):
        """Draw the pitch markings.

        Everything is derived from the shared Pitch2D, so the lines always
        match where the ball actually bounces and scores. (Audit finding B4)
        """
        pitch = self.pitch
        lines = self.colors['lines']
        centre_x, centre_y = int(pitch.width / 2), int(pitch.height / 2)
        pitch_rect = pygame.Rect(pitch.left, pitch.top,
                                 pitch.right - pitch.left,
                                 pitch.bottom - pitch.top)

        pygame.draw.rect(self.display, lines, pitch_rect, 2)
        pygame.draw.line(self.display, lines,
                         (centre_x, pitch.top), (centre_x, pitch.bottom), 2)
        pygame.draw.circle(self.display, lines, (centre_x, centre_y), 70, 2)
        pygame.draw.circle(self.display, lines, (centre_x, centre_y), 4)

        # Penalty areas and six-yard boxes, both ends.
        penalty_depth, penalty_span = 120, 280
        goal_area_depth, goal_area_span = 50, 170
        for depth, span in ((penalty_depth, penalty_span),
                            (goal_area_depth, goal_area_span)):
            top = centre_y - span // 2
            pygame.draw.rect(self.display, lines,
                             (pitch.left, top, depth, span), 2)
            pygame.draw.rect(self.display, lines,
                             (pitch.right - depth, top, depth, span), 2)

        # Penalty spots
        pygame.draw.circle(self.display, lines, (int(pitch.left) + 80, centre_y), 3)
        pygame.draw.circle(self.display, lines, (int(pitch.right) - 80, centre_y), 3)

        # Corner arcs
        radius = 14
        for corner_x, corner_y, start, end in (
            (pitch.left, pitch.top, 0, math.pi / 2),
            (pitch.right, pitch.top, math.pi / 2, math.pi),
            (pitch.right, pitch.bottom, math.pi, 3 * math.pi / 2),
            (pitch.left, pitch.bottom, 3 * math.pi / 2, 2 * math.pi),
        ):
            box = pygame.Rect(corner_x - radius, corner_y - radius,
                              radius * 2, radius * 2)
            pygame.draw.arc(self.display, lines, box, start, end, 2)

    def draw_goals(self):
        """Draw both goals, including a simple net.

        Uses the same Pitch2D as the collision and scoring code, so what is
        drawn is exactly what scores. (Audit finding B4)
        """
        pitch = self.pitch
        net_colour = (210, 220, 215)
        goal_top = int(pitch.goal_y0)
        goal_height = int(pitch.goal_height)

        for net_x, post_x in ((pitch.net_left, pitch.left),
                              (pitch.right, pitch.right)):
            box = pygame.Rect(int(net_x), goal_top, pitch.goal_depth, goal_height)

            # Net shading
            net = pygame.Surface(box.size, pygame.SRCALPHA)
            net.fill((255, 255, 255, 28))
            for x in range(0, box.width, 5):
                pygame.draw.line(net, (*net_colour, 70), (x, 0), (x, box.height))
            for y in range(0, box.height, 5):
                pygame.draw.line(net, (*net_colour, 70), (0, y), (box.width, y))
            self.display.blit(net, box.topleft)

            pygame.draw.rect(self.display, self.colors['lines'], box, 2)
            # Goal line between the posts, drawn thicker
            pygame.draw.line(self.display, self.colors['lines'],
                             (post_x, goal_top), (post_x, goal_top + goal_height), 4)

    def draw_players(self):
        """Draw both teams, with shirt numbers and stamina indicators."""
        for team, colour in (('red', self.colors['red']),
                             ('blue', self.colors['blue'])):
            for index, player in enumerate(self.players[team]):
                x, y = int(player['pos'][0]), int(player['pos'][1])
                radius = player['radius']
                selected = (team == self.selected_team
                            and index == self.selected_player)

                # Drop shadow
                shadow = pygame.Surface((radius * 2 + 6, radius * 2 + 6),
                                        pygame.SRCALPHA)
                pygame.draw.circle(shadow, (0, 0, 0, 70),
                                   (radius + 3, radius + 3), radius)
                self.display.blit(shadow, (x - radius - 1, y - radius + 1))

                pygame.draw.circle(self.display, colour, (x, y), radius)
                pygame.draw.circle(self.display, (15, 18, 22), (x, y), radius, 1)

                # Shirt number
                number = self.font_tiny.render(str(index + 1), True, (255, 255, 255))
                self.display.blit(number, number.get_rect(center=(x, y)))

                # Stamina ring segment above the player, shown when tired or
                # when this is the player being controlled.
                if selected or player['stamina'] < 99:
                    self.draw_mini_stamina_bar(x, y - radius - 9, player['stamina'])

                if selected:
                    pygame.draw.circle(self.display, self.colors['accent'],
                                       (x, y), radius + 4, 2)
                    # Marker above the controlled player
                    pygame.draw.polygon(self.display, self.colors['accent'], [
                        (x, y - radius - 15), (x - 5, y - radius - 23),
                        (x + 5, y - radius - 23)])

    def draw_mini_stamina_bar(self, x, y, stamina):
        """Draw a small stamina bar centred on `x`."""
        width, height = 28, 4
        left = x - width // 2
        pygame.draw.rect(self.display, (20, 22, 26), (left, y, width, height),
                         border_radius=2)
        filled = int(width * max(0.0, min(100.0, stamina)) / 100)
        if filled > 0:
            pygame.draw.rect(self.display, self.stamina_colour(stamina),
                             (left, y, filled, height), border_radius=2)

    def stamina_colour(self, stamina):
        """Green when fresh, amber when tiring, red when exhausted."""
        if stamina > 60:
            return (80, 215, 120)
        if stamina > 30:
            return (235, 195, 80)
        return (230, 90, 80)

    def draw_ball(self):
        """Draw the ball with a soft shadow."""
        x, y = int(self.ball_pos[0]), int(self.ball_pos[1])
        radius = self.ball_radius

        shadow = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
        pygame.draw.circle(shadow, (0, 0, 0, 90), (radius * 2, radius * 2), radius)
        self.display.blit(shadow, (x - radius * 2 + 2, y - radius * 2 + 3))

        pygame.draw.circle(self.display, self.colors['ball'], (x, y), radius)
        pygame.draw.circle(self.display, (40, 44, 50), (x, y), radius, 1)
        # Suggestion of the classic panel pattern
        pygame.draw.circle(self.display, (40, 44, 50), (x, y), max(1, radius // 3))

    # ------------------------------------------------------------------
    # HUD
    # ------------------------------------------------------------------

    def format_clock(self):
        """Match clock as m:ss, never negative."""
        remaining = max(0, int(math.ceil(self.game_time)))
        return f"{remaining // 60}:{remaining % 60:02d}"

    def draw_ui(self):
        """Draw the scoreboard, the selected-player panel and key hints."""
        self.draw_scoreboard()
        self.draw_selected_player_panel()
        self.draw_control_hints()

    def draw_scoreboard(self):
        """Score and match clock, in a panel at the top of the screen."""
        panel = pygame.Rect(self.width // 2 - 170, 14, 340, 74)
        surface = pygame.Surface(panel.size, pygame.SRCALPHA)
        surface.fill((*self.colors['panel'], 225))
        self.display.blit(surface, panel.topleft)
        pygame.draw.rect(self.display, self.colors['panel_light'], panel, 1,
                         border_radius=8)

        # Team colour tabs
        pygame.draw.rect(self.display, self.colors['red'],
                         (panel.x, panel.y, 6, panel.height))
        pygame.draw.rect(self.display, self.colors['blue'],
                         (panel.right - 6, panel.y, 6, panel.height))

        score = self.font_mono.render(f"{self.score[0]}  -  {self.score[1]}",
                                      True, self.colors['text'])
        self.display.blit(score, score.get_rect(center=(panel.centerx, panel.y + 26)))

        clock_colour = (self.colors['accent'] if self.game_time > 10
                        else self.colors['red'])
        clock = self.font_small.render(self.format_clock(), True, clock_colour)
        self.display.blit(clock, clock.get_rect(center=(panel.centerx, panel.y + 55)))

        red_label = self.font_tiny.render("RED", True, self.colors['muted'])
        self.display.blit(red_label, (panel.x + 16, panel.y + 14))
        blue_label = self.font_tiny.render("BLUE", True, self.colors['muted'])
        self.display.blit(blue_label,
                          (panel.right - 16 - blue_label.get_width(), panel.y + 14))

    def draw_selected_player_panel(self):
        """Show who is being controlled and how much stamina they have."""
        player = self.players[self.selected_team][self.selected_player]
        panel = pygame.Rect(18, self.height - 104, 250, 86)

        surface = pygame.Surface(panel.size, pygame.SRCALPHA)
        surface.fill((*self.colors['panel'], 225))
        self.display.blit(surface, panel.topleft)
        pygame.draw.rect(self.display, self.colors['panel_light'], panel, 1,
                         border_radius=8)

        team_colour = self.colors[self.selected_team]
        pygame.draw.circle(self.display, team_colour, (panel.x + 26, panel.y + 26), 12)
        number = self.font_tiny.render(str(self.selected_player + 1), True,
                                       (255, 255, 255))
        self.display.blit(number, number.get_rect(center=(panel.x + 26, panel.y + 26)))

        title = self.font_small.render(
            f"{self.selected_team.upper()}  -  {player['role']}", True,
            self.colors['text'])
        self.display.blit(title, (panel.x + 50, panel.y + 13))

        # Stamina readout, then the bar below it (they used to overlap).
        label = self.font_tiny.render("STAMINA", True, self.colors['muted'])
        self.display.blit(label, (panel.x + 16, panel.y + 44))
        value = self.font_tiny.render(f"{int(player['stamina'])}%", True,
                                      self.colors['text'])
        self.display.blit(value, (panel.right - 16 - value.get_width(), panel.y + 44))

        bar = pygame.Rect(panel.x + 16, panel.y + 68, panel.width - 32, 7)
        pygame.draw.rect(self.display, (20, 22, 26), bar, border_radius=4)
        filled = int(bar.width * max(0.0, min(100.0, player['stamina'])) / 100)
        if filled > 0:
            pygame.draw.rect(self.display, self.stamina_colour(player['stamina']),
                             (bar.x, bar.y, filled, bar.height), border_radius=4)

    def draw_control_hints(self):
        """Compact key hints in the bottom-right corner."""
        hints = [
            "Arrows move   Space kick   Tab team",
            "1-9/0/- select   P pause   R restart   Esc menu",
        ]
        y = self.height - 44
        for hint in hints:
            text = self.font_tiny.render(hint, True, self.colors['muted'])
            self.display.blit(text, (self.width - text.get_width() - 18, y))
            y += 18

    # ------------------------------------------------------------------
    # Overlays
    # ------------------------------------------------------------------

    def dim_screen(self, alpha=150):
        """Dim the whole screen, for a modal overlay."""
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((8, 9, 11, alpha))
        self.display.blit(overlay, (0, 0))

    def draw_pause_overlay(self):
        """Draw the paused state."""
        self.dim_screen(140)
        title = self.font_large.render("PAUSED", True, self.colors['text'])
        self.display.blit(title, title.get_rect(
            center=(self.width // 2, self.height // 2 - 16)))
        hint = self.font_small.render("P resume   -   R restart   -   Esc menu",
                                      True, self.colors['muted'])
        self.display.blit(hint, hint.get_rect(
            center=(self.width // 2, self.height // 2 + 34)))

    def show_game_over(self):
        """Draw the full-time screen."""
        self.dim_screen(170)

        if self.score[0] > self.score[1]:
            winner, winner_colour = "Red Team Wins", self.colors['red']
        elif self.score[1] > self.score[0]:
            winner, winner_colour = "Blue Team Wins", self.colors['blue']
        else:
            winner, winner_colour = "It's a Draw", self.colors['text']

        panel = pygame.Rect(self.width // 2 - 230, self.height // 2 - 130, 460, 260)
        surface = pygame.Surface(panel.size, pygame.SRCALPHA)
        surface.fill((*self.colors['panel'], 240))
        self.display.blit(surface, panel.topleft)
        pygame.draw.rect(self.display, self.colors['accent'], panel, 2,
                         border_radius=12)

        full_time = self.font_small.render("FULL TIME", True, self.colors['muted'])
        self.display.blit(full_time, full_time.get_rect(
            center=(panel.centerx, panel.y + 36)))

        winner_text = self.font_large.render(winner, True, winner_colour)
        self.display.blit(winner_text, winner_text.get_rect(
            center=(panel.centerx, panel.y + 90)))

        score_text = self.font_mono.render(f"{self.score[0]}  -  {self.score[1]}",
                                           True, self.colors['text'])
        self.display.blit(score_text, score_text.get_rect(
            center=(panel.centerx, panel.y + 150)))

        hint = self.font_small.render("R restart   -   Esc menu", True,
                                      self.colors['muted'])
        self.display.blit(hint, hint.get_rect(center=(panel.centerx, panel.y + 212)))

    def run(self):
        """Main game loop.

        Note the loop never blocks: the goal celebration is an overlay with
        a countdown rather than a nested event loop, so the match keeps
        simulating and input keeps responding. (Audit finding B20)
        """
        # Start the clock fresh, so time spent in the menu is not counted
        # as a huge first frame.
        self.last_update = time.time()

        while self.running:
            self.handle_events()

            if self.mode == "menu":
                self.draw_menu()
            elif self.mode == "help":
                self.draw_help()
            elif self.mode == "2d_game":
                if self.game_time > 0 and not self.paused:
                    self.update_game_state()
                else:
                    # Keep the timebase current so unpausing or restarting
                    # does not jump the simulation forward.
                    self.last_update = time.time()
                self.draw_2d_game()

            pygame.display.flip()
            self.clock.tick(60)

        # Cleanup
        if self.cap is not None:
            self.cap.release()
        pygame.quit()

if __name__ == "__main__":
    game = SoccerGame()
    game.run()
