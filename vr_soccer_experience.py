"""Soccer VR Experience - side-by-side stereo preview.

Developed by Tojin Varkey Simson and Jaiby Mariya Jospeh.

EXPERIMENTAL / PROTOTYPE. This renders the pitch twice, once per eye, side
by side on a normal monitor. It is *not* headset support: there is no head
tracking, no OpenXR/SteamVR integration and no lens distortion correction.
It is meant to be viewed on a flat screen or in a phone-holder style viewer.

Phase 2 fixes (see SOCCER_PROJECT_AUDIT.md, finding B13 and B14):

* each eye's aspect ratio is computed from its own half-width viewport,
  instead of `width / (height/2)`, which squashed the picture horizontally;
* the eyes are separated along the camera's right vector rather than world
  X, so the stereo effect survives turning;
* the view is stored as yaw/pitch angles, clamped and re-derived each frame,
  so it cannot drift or flip past vertical;
* the VR toggle fires once per key press instead of every frame it is held;
* goalposts and player limbs are the right way up (shared soccer_gl module);
* the pitch texture is built with NumPy/OpenCV rather than a million-step
  Python loop.

Controls (unchanged):
    WASD        move around the pitch
    Arrow keys  look around
    V           toggle stereo / single view
    + / -       adjust eye separation
    Space       kick the ball
    Esc         exit
"""

import math

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

import soccer_gl
from soccer_core import physics3d, stereo
from soccer_core.formations import scene_players
from soccer_core.pitch import Pitch3D

# Kick strength, metres/second (the legacy per-frame values x 60).
KICK_SPEED = 30.0
KICK_LIFT = 18.0
KICK_RANGE = 5.0


class VRSoccerExperience:
    def __init__(self, width=1280, height=720, fullscreen=False):
        pygame.init()
        self.width, self.height = width, height

        flags = DOUBLEBUF | OPENGL
        if fullscreen:
            flags |= pygame.FULLSCREEN
        self.display = pygame.display.set_mode((self.width, self.height), flags)
        pygame.display.set_caption("Soccer VR Experience (experimental)")

        # OpenGL settings
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHT1)
        glEnable(GL_COLOR_MATERIAL)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(0.45, 0.65, 0.88, 1.0)  # sky

        glLightfv(GL_LIGHT0, GL_POSITION, (0, 100, 100, 1))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.3, 0.3, 0.3, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.8, 0.8, 0.8, 1))
        glLightfv(GL_LIGHT1, GL_POSITION, (0, 100, -100, 1))
        glLightfv(GL_LIGHT1, GL_AMBIENT, (0.15, 0.15, 0.15, 1))
        glLightfv(GL_LIGHT1, GL_DIFFUSE, (0.6, 0.6, 0.6, 1))

        # Scene
        self.pitch = Pitch3D()
        self.field_texture = soccer_gl.create_field_texture(self.pitch)
        self.player_positions = scene_players(self.pitch)

        self.ball_pos, self.ball_vel = physics3d.kickoff_state()
        self.ball_radius = 0.2

        # Camera: position plus yaw/pitch angles. Storing angles (rather
        # than repeatedly rotating a vector) keeps the look direction unit
        # length and lets the pitch be clamped. (Audit finding B13)
        self.camera_pos = [0.0, 1.7, 25.0]
        self.yaw = 180.0      # look back towards the centre of the pitch
        self.pitch_angle = -5.0
        self.move_speed = 12.0        # metres per second
        self.rot_speed = 90.0         # degrees per second

        self.vr_mode = True
        self.ipd = 0.064              # interpupillary distance, metres

        self.score = [0, 0]
        self.game_time = 0.0
        self.effects = []
        self.animation_time = 0.0

        self.running = True
        self.clock = pygame.time.Clock()

        print("\n=== Soccer VR Experience Controls (experimental) ===")
        print("  WASD: Move around the field")
        print("  Arrow keys: Look around")
        print("  V: Toggle stereo / single view")
        print("  +/-: Adjust eye separation")
        print("  Space: Kick ball")
        print("  ESC: Exit")
        print("\nNote: this is a side-by-side stereo preview, not headset support.")

    # ------------------------------------------------------------------
    # Camera
    # ------------------------------------------------------------------

    @property
    def look_dir(self):
        """Current unit look direction, derived from yaw/pitch."""
        return stereo.direction_from_angles(self.yaw, self.pitch_angle)

    def set_3d_camera(self, eye):
        """Set projection and view matrices for one eye.

        `eye` is "left", "right" or "centre".
        """
        aspect = stereo.viewport_aspect(self.width, self.height,
                                        split_screen=self.vr_mode)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(60, aspect, 0.1, 400.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        look = self.look_dir
        eye_pos = stereo.eye_position(self.camera_pos, look, self.ipd, eye)
        gluLookAt(eye_pos[0], eye_pos[1], eye_pos[2],
                  eye_pos[0] + look[0], eye_pos[1] + look[1], eye_pos[2] + look[2],
                  0.0, 1.0, 0.0)

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_events(self):
        """Discrete key presses (toggles and one-shot actions)."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_v:
                    # Edge-triggered: polling this with get_pressed() used to
                    # flip the mode on every frame the key was held down.
                    self.vr_mode = not self.vr_mode
                elif event.key == pygame.K_SPACE:
                    self.kick_ball()

    def handle_input(self, dt):
        """Continuous movement and look controls."""
        keys = pygame.key.get_pressed()

        forward = (keys[pygame.K_w] - keys[pygame.K_s]) * self.move_speed * dt
        strafe = (keys[pygame.K_d] - keys[pygame.K_a]) * self.move_speed * dt
        if forward or strafe:
            self.camera_pos = stereo.move(self.camera_pos, self.look_dir,
                                          forward, strafe)
            # Stay within sight of the pitch.
            limit_x = self.pitch.half_length + 15.0
            limit_z = self.pitch.half_width + 15.0
            self.camera_pos[0] = max(-limit_x, min(limit_x, self.camera_pos[0]))
            self.camera_pos[2] = max(-limit_z, min(limit_z, self.camera_pos[2]))

        self.yaw += (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * self.rot_speed * dt
        self.pitch_angle = stereo.clamp_pitch(
            self.pitch_angle + (keys[pygame.K_UP] - keys[pygame.K_DOWN])
            * self.rot_speed * dt)

        if keys[pygame.K_PLUS] or keys[pygame.K_EQUALS]:
            self.ipd = min(0.2, self.ipd + 0.02 * dt)
        if keys[pygame.K_MINUS]:
            self.ipd = max(0.01, self.ipd - 0.02 * dt)

    def kick_ball(self):
        """Kick the ball away from the viewer, if close enough."""
        dx = self.ball_pos[0] - self.camera_pos[0]
        dz = self.ball_pos[2] - self.camera_pos[2]
        distance = math.hypot(dx, dz)
        if 0 < distance < KICK_RANGE:
            self.ball_vel = [dx / distance * KICK_SPEED,
                             KICK_LIFT,
                             dz / distance * KICK_SPEED]

    # ------------------------------------------------------------------
    # Simulation and drawing
    # ------------------------------------------------------------------

    def update(self, dt):
        """Advance ball physics, goals and effects by `dt` seconds."""
        physics3d.step_ball(self.ball_pos, self.ball_vel, dt, self.pitch,
                            self.ball_radius)

        side = physics3d.detect_goal(self.ball_pos, self.pitch)
        if side is not None:
            self.score[1 if side == "left" else 0] += 1
            soccer_gl.add_effect(self.effects, 'goal', self.ball_pos)
            self.ball_pos, self.ball_vel = physics3d.kickoff_state()

        soccer_gl.update_effects(self.effects, dt)
        self.animation_time += dt
        self.game_time += dt

    def draw_scene(self):
        """Draw the whole scene from the current camera."""
        soccer_gl.draw_field(self.field_texture, self.pitch)
        soccer_gl.draw_goals(self.pitch)
        soccer_gl.draw_players(self.player_positions, self.animation_time)
        soccer_gl.draw_ball(self.ball_pos, self.ball_radius)
        soccer_gl.draw_effects(self.effects)

    def render(self):
        """Render one frame, in stereo or mono."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        if self.vr_mode:
            half_width = self.width // 2
            glViewport(0, 0, half_width, self.height)
            self.set_3d_camera("left")
            self.draw_scene()

            glViewport(half_width, 0, half_width, self.height)
            self.set_3d_camera("right")
            self.draw_scene()
        else:
            glViewport(0, 0, self.width, self.height)
            self.set_3d_camera("centre")
            self.draw_scene()

        pygame.display.flip()

    def run(self):
        """Main loop."""
        while self.running:
            # Cap dt so a stall cannot teleport the ball.
            dt = min(self.clock.tick(60) / 1000.0, 0.05)
            self.handle_events()
            self.handle_input(dt)
            self.update(dt)
            self.render()

        pygame.quit()


if __name__ == "__main__":
    app = VRSoccerExperience()
    app.run()
