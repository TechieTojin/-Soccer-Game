"""Soccer 3D Field Viewer.

An orbiting view of a 3D pitch with both teams in formation. It is a
visualisation of the pitch and formations, not a reconstruction from video -
the inherited `soccer3d/` research pipeline is what does that, and this
viewer does not use it.

Phase 2 fixes (see SOCCER_PROJECT_AUDIT.md, finding B16):

* The viewer used to `sys.exit()` when the Barcelona dataset was missing,
  even though it never read the dataset - all the positions were hard-coded.
  That check is gone, so the viewer runs on a fresh clone.
* The initial `gluLookAt` was immediately discarded by the `glLoadIdentity()`
  at the top of the draw loop, leaving the camera at the origin in the plane
  of the pitch, looking edge-on. The camera is now rebuilt every frame from
  explicit orbit parameters.
* Players were extruded along +Z with no rotation, so they lay on their
  sides. They now use the shared, upright model in soccer_gl.

Controls (unchanged):
    Arrow keys  orbit the camera
    W / S       zoom in and out
    Esc         quit
"""

import math

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

import soccer_gl
from soccer_core.formations import scene_players
from soccer_core.pitch import Pitch3D

# NOTE: matplotlib and PIL were imported here but never used; dropping them
# means the 3D viewer starts without those packages installed.
# (Audit finding B20)


class SoccerFieldViewer:
    """An orbit-camera view of the pitch."""

    def __init__(self, width=1024, height=720):
        pygame.init()
        self.width, self.height = width, height
        pygame.display.set_mode((width, height), DOUBLEBUF | OPENGL)
        pygame.display.set_caption("Soccer On Your Tabletop - 3D Field Viewer")

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(0.45, 0.65, 0.88, 1.0)
        glLightfv(GL_LIGHT0, GL_POSITION, (0, 120, 80, 1))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.35, 0.35, 0.35, 1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.85, 0.85, 0.85, 1))

        self.pitch = Pitch3D()
        self.field_texture = soccer_gl.create_field_texture(self.pitch)
        self.players = scene_players(self.pitch)
        self.ball_pos = [0.0, 0.2, 0.0]

        # Orbit camera: angle around the pitch, height angle and distance.
        self.orbit = 0.0
        self.elevation = 35.0
        self.distance = 110.0

        self.animation_time = 0.0
        self.clock = pygame.time.Clock()
        self.running = True

        print("\n=== Soccer 3D Viewer Controls ===")
        print("  Arrow keys: Orbit the camera")
        print("  W/S: Zoom in / out")
        print("  ESC: Quit")

    def camera_position(self):
        """World position of the orbiting camera."""
        orbit = math.radians(self.orbit)
        elevation = math.radians(self.elevation)
        horizontal = math.cos(elevation) * self.distance
        return (math.sin(orbit) * horizontal,
                math.sin(elevation) * self.distance,
                math.cos(orbit) * horizontal)

    def apply_camera(self):
        """Build the projection and view matrices for this frame.

        Done every frame, because the draw loop resets the modelview matrix;
        setting the camera only once at start-up (as the original did) had
        no effect at all.
        """
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, self.width / float(self.height), 0.5, 600.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        eye = self.camera_position()
        gluLookAt(eye[0], eye[1], eye[2], 0.0, 0.0, 0.0, 0.0, 1.0, 0.0)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False

    def handle_input(self, dt):
        keys = pygame.key.get_pressed()
        self.orbit += (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * 60.0 * dt
        self.elevation = max(5.0, min(89.0, self.elevation
                                      + (keys[pygame.K_UP] - keys[pygame.K_DOWN])
                                      * 45.0 * dt))
        zoom = (keys[pygame.K_s] - keys[pygame.K_w]) * 60.0 * dt
        self.distance = max(25.0, min(320.0, self.distance + zoom))

    def draw(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glViewport(0, 0, self.width, self.height)
        self.apply_camera()

        soccer_gl.draw_field(self.field_texture, self.pitch)
        soccer_gl.draw_goals(self.pitch)
        soccer_gl.draw_players(self.players, self.animation_time)
        soccer_gl.draw_ball(self.ball_pos)

        pygame.display.flip()

    def run(self):
        while self.running:
            dt = min(self.clock.tick(60) / 1000.0, 0.05)
            self.handle_events()
            self.handle_input(dt)
            self.animation_time += dt
            self.draw()
        pygame.quit()


def main():
    viewer = SoccerFieldViewer()
    viewer.run()


if __name__ == "__main__":
    main()
