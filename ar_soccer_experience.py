"""Soccer AR Experience - tabletop pitch on a printed ArUco marker.

Developed by Tojin Varkey Simson and Jaiby Mariya Jospeh.

EXPERIMENTAL / PROTOTYPE - NOT YET VERIFIED ON HARDWARE.
The pose pipeline, projection and scaling have been reworked and the pure
maths is unit-tested, but at the time of writing this has not been run
against a real webcam and a printed marker. Treat the alignment quality as
unverified until it has been.

Print a marker first:
    python tools/make_markers.py --ids 0 --size-mm 100

Phase 2 fixes (see SOCCER_PROJECT_AUDIT.md):

* B10 - the webcam frame is now actually drawn, as a background behind the
  3D scene. Previously the frame was only used for detection and the scene
  floated on black, so "AR" never showed the real world at all.
* B11 - the OpenCV pose is converted into the OpenGL frame (Y/Z flip), the
  GL projection is derived from the same intrinsics given to solvePnP, the
  marker is measured in real metres, and the pitch is scaled to a few
  marker-widths instead of being ~10x the marker. solvePnP's return value
  is checked.
* B12 - view controls kept their own state and were wiped by the matrix
  reload each frame; the fallback camera now stores yaw/pitch/distance.
* B1 - the modern ArUco API, created lazily rather than at import time.
* Missing markers keep the last good pose briefly instead of freezing, and
  a missing camera falls back to an orbiting desktop view.

Controls:
    A           toggle AR overlay / desktop view
    C           cycle to the next camera
    Arrow keys  orbit the desktop view
    + / -       grow or shrink the pitch on the marker
    Space       kick the ball
    Esc         exit
"""

import argparse
import math

import numpy as np
import cv2
import cv2.aruco as aruco
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

import soccer_gl
from soccer_core import ar_pose, physics3d
from soccer_core.formations import scene_players
from soccer_core.pitch import Pitch3D

# ArUco dictionary used for field tracking
ARUCO_DICT_ID = aruco.DICT_4X4_50
FIELD_MARKER_ID = 0

# How long a lost marker keeps its last pose before the overlay gives up.
POSE_MEMORY_SECONDS = 0.5

KICK_SPEED = 30.0
KICK_LIFT = 18.0


def create_aruco_detector():
    """Create an ArUco dictionary and detector.

    OpenCV 4.7 removed the old factory functions (`aruco.Dictionary_get`,
    `aruco.DetectorParameters_create`) in favour of `getPredefinedDictionary`
    and the `ArucoDetector` class. This helper uses the current API and falls
    back to the legacy one for older OpenCV installs, so AR works on both.
    Returns `(dictionary, detector_or_None)`; when the detector is None the
    caller must use the legacy `aruco.detectMarkers` function.
    (Audit finding B1: the module used to crash on import with OpenCV >= 4.7.)
    """
    if hasattr(aruco, "ArucoDetector"):
        dictionary = aruco.getPredefinedDictionary(ARUCO_DICT_ID)
        params = aruco.DetectorParameters()
        return dictionary, aruco.ArucoDetector(dictionary, params)
    # Legacy OpenCV (< 4.7)
    dictionary = aruco.Dictionary_get(ARUCO_DICT_ID)
    return dictionary, None


def detect_aruco_markers(gray, dictionary, detector):
    """Detect ArUco markers using whichever OpenCV API is available."""
    if detector is not None:
        return detector.detectMarkers(gray)
    params = aruco.DetectorParameters_create()
    return aruco.detectMarkers(gray, dictionary, parameters=params)


class ARSoccerExperience:
    def __init__(self, width=1280, height=720, camera_index=0,
                 marker_length=0.10, pitch_spans=6.0, fullscreen=False):
        pygame.init()
        self.width, self.height = width, height

        flags = DOUBLEBUF | OPENGL
        if fullscreen:
            flags |= pygame.FULLSCREEN
        self.display = pygame.display.set_mode((self.width, self.height), flags)
        pygame.display.set_caption("Soccer AR Experience (experimental)")

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_COLOR_MATERIAL)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(0.08, 0.09, 0.11, 1.0)
        self.setup_lighting()

        # ArUco detector, created here rather than at import time so an
        # OpenCV API problem cannot stop the module from being imported.
        self.aruco_dict, self.aruco_detector = create_aruco_detector()

        # Real printed size of the marker, in metres, and how many marker
        # widths the pitch should span on the table.
        self.marker_length = marker_length
        self.pitch_spans = pitch_spans

        # Camera
        self.camera_index = camera_index
        self.cap = None
        self.frame_size = (640, 480)
        self.camera_texture = glGenTextures(1)
        self.init_camera()

        # Scene
        self.pitch = Pitch3D()
        self.field_texture = soccer_gl.create_field_texture(self.pitch)
        self.player_positions = scene_players(self.pitch)
        self.ball_pos, self.ball_vel = physics3d.kickoff_state()
        self.ball_radius = 0.2
        self.effects = []
        self.score = [0, 0]
        self.animation_time = 0.0

        # Tracking state
        self.ar_mode = self.cap is not None
        self.last_modelview = None
        self.time_since_seen = POSE_MEMORY_SECONDS * 2
        self.marker_visible = False

        # Desktop (non-AR) camera, with its own persistent state. The
        # original rotated the GL matrix directly in the event handler, and
        # the next frame's matrix reload threw that away. (Audit finding B12)
        self.orbit = 0.0
        self.elevation = 30.0
        self.distance = 150.0

        # HUD
        self.hud_font = pygame.font.SysFont("segoeui,dejavusans,arial", 20, bold=True)
        self.hud_texture = glGenTextures(1)

        self.running = True
        self.clock = pygame.time.Clock()

        print("\n=== Soccer AR Experience Controls (experimental) ===")
        print("  A: Toggle AR overlay / desktop view")
        print("  C: Change camera")
        print("  Arrow keys: Orbit the desktop view")
        print("  +/-: Grow / shrink the pitch on the marker")
        print("  Space: Kick ball")
        print("  ESC: Exit")
        print(f"\n-> Print marker ID {FIELD_MARKER_ID} at {marker_length * 1000:.0f} mm "
              f"and place it flat in view of the camera.")
        print("   Generate one with: python tools/make_markers.py")

    def setup_lighting(self):
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, (0.0, 1.0, 0.5, 0.0))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.45, 0.45, 0.45, 1.0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.85, 0.85, 0.85, 1.0))

    # ------------------------------------------------------------------
    # Camera
    # ------------------------------------------------------------------

    def init_camera(self):
        """Open the webcam, tolerating its absence.

        A missing or busy camera is not fatal: the app falls back to the
        desktop view rather than showing a black screen.
        """
        if self.cap is not None:
            self.cap.release()
            self.cap = None

        try:
            cap = cv2.VideoCapture(self.camera_index)
            if not cap.isOpened():
                cap.release()
                print(f"Camera {self.camera_index} is not available - "
                      "running in desktop view (press A to retry AR).")
                self.ar_mode = False
                return

            self.cap = cap
            ok, frame = self.cap.read()
            if ok and frame is not None:
                self.frame_size = (frame.shape[1], frame.shape[0])
            print(f"Camera {self.camera_index} opened at "
                  f"{self.frame_size[0]}x{self.frame_size[1]}.")
        except Exception as e:
            print(f"Could not open camera {self.camera_index}: {e}")
            self.cap = None
            self.ar_mode = False

    def read_frame(self):
        """Grab one frame, or None when there is no usable camera."""
        if self.cap is None:
            return None
        ok, frame = self.cap.read()
        if not ok or frame is None:
            return None
        self.frame_size = (frame.shape[1], frame.shape[0])
        return frame

    # ------------------------------------------------------------------
    # Tracking
    # ------------------------------------------------------------------

    def intrinsics(self):
        """Approximate intrinsics for the current frame size."""
        return ar_pose.approximate_intrinsics(*self.frame_size)

    def estimate_pose(self, frame):
        """Return the GL modelview matrix for the marker, or None.

        Detects marker `FIELD_MARKER_ID`, solves for its pose, then converts
        that pose from OpenCV's coordinate frame into OpenGL's.
        (Audit finding B11)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        corners, ids, _ = detect_aruco_markers(gray, self.aruco_dict,
                                               self.aruco_detector)
        if ids is None:
            return None

        ids = ids.flatten()
        matches = np.where(ids == FIELD_MARKER_ID)[0]
        if len(matches) == 0:
            return None

        image_points = np.asarray(corners[matches[0]][0], dtype=np.float64)
        object_points = ar_pose.marker_object_points(self.marker_length)
        fx, fy, cx, cy = self.intrinsics()

        ok, rvec, tvec = cv2.solvePnP(
            object_points, image_points,
            ar_pose.camera_matrix(fx, fy, cx, cy),
            np.zeros((4, 1)),               # assume no lens distortion
            flags=cv2.SOLVEPNP_IPPE_SQUARE)  # the right solver for a square
        if not ok:                           # the original ignored this
            return None

        rotation, _ = cv2.Rodrigues(rvec)
        return ar_pose.cv_pose_to_gl_modelview(rotation, tvec)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw_camera_background(self, frame):
        """Draw the webcam frame as a full-screen background.

        This is what makes the mode actually augmented reality: without it
        the 3D scene floats on an empty background. (Audit finding B10)
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb = np.flipud(rgb)                 # GL textures start bottom-left
        height, width = rgb.shape[:2]

        glBindTexture(GL_TEXTURE_2D, self.camera_texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0,
                     GL_RGB, GL_UNSIGNED_BYTE, np.ascontiguousarray(rgb))

        self.draw_fullscreen_quad(self.camera_texture)

    def draw_fullscreen_quad(self, texture_id, alpha=1.0):
        """Draw a textured quad over the whole window, ignoring depth."""
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, 1, 0, 1, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glColor4f(1.0, 1.0, 1.0, alpha)

        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(0, 0)
        glTexCoord2f(1, 0); glVertex2f(1, 0)
        glTexCoord2f(1, 1); glVertex2f(1, 1)
        glTexCoord2f(0, 1); glVertex2f(0, 1)
        glEnd()

        glDisable(GL_BLEND)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_LIGHTING)
        glEnable(GL_DEPTH_TEST)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def draw_hud(self, message, colour=(235, 238, 242)):
        """Draw a one-line status message in the top-left corner."""
        surface = self.hud_font.render(message, True, colour, (18, 20, 24))
        data = pygame.image.tostring(surface, "RGBA", True)
        width, height = surface.get_size()

        glBindTexture(GL_TEXTURE_2D, self.hud_texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0,
                     GL_RGBA, GL_UNSIGNED_BYTE, data)

        # Position it in normalised window coordinates.
        x0, y0 = 0.012, 1.0 - 0.018 - height / self.height
        x1, y1 = x0 + width / self.width, y0 + height / self.height

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, 1, 0, 1, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glColor4f(1, 1, 1, 0.92)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(x0, y0)
        glTexCoord2f(1, 0); glVertex2f(x1, y0)
        glTexCoord2f(1, 1); glVertex2f(x1, y1)
        glTexCoord2f(0, 1); glVertex2f(x0, y1)
        glEnd()
        glDisable(GL_BLEND)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_LIGHTING)
        glEnable(GL_DEPTH_TEST)

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def draw_scene_on_marker(self, modelview):
        """Draw the pitch anchored to the marker pose."""
        fx, fy, cx, cy = self.intrinsics()
        projection = ar_pose.projection_from_intrinsics(
            fx, fy, cx, cy, self.frame_size[0], self.frame_size[1],
            near=0.01, far=100.0)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glLoadMatrixf(projection.T.astype(np.float32))

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glLoadMatrixf(modelview.T.astype(np.float32))

        # Shrink the life-size pitch down onto the table.
        scale = ar_pose.scene_scale(self.marker_length, self.pitch.length_x,
                                    self.pitch_spans)
        glPushMatrix()
        glScalef(scale, scale, scale)
        self.draw_scene()
        glPopMatrix()

    def draw_scene_desktop(self):
        """Draw the pitch from the orbiting desktop camera."""
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, self.width / float(self.height), 0.5, 600.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        orbit = math.radians(self.orbit)
        elevation = math.radians(self.elevation)
        horizontal = math.cos(elevation) * self.distance
        gluLookAt(math.sin(orbit) * horizontal,
                  math.sin(elevation) * self.distance,
                  math.cos(orbit) * horizontal,
                  0, 0, 0, 0, 1, 0)
        self.draw_scene()

    def draw_scene(self):
        soccer_gl.draw_field(self.field_texture, self.pitch)
        soccer_gl.draw_goals(self.pitch)
        soccer_gl.draw_players(self.player_positions, self.animation_time)
        soccer_gl.draw_ball(self.ball_pos, self.ball_radius)
        soccer_gl.draw_effects(self.effects)

    # ------------------------------------------------------------------
    # Input and simulation
    # ------------------------------------------------------------------

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_a:
                    self.ar_mode = not self.ar_mode
                    if self.ar_mode and self.cap is None:
                        self.init_camera()
                elif event.key == pygame.K_c:
                    self.camera_index = (self.camera_index + 1) % 3
                    self.init_camera()
                elif event.key == pygame.K_SPACE:
                    self.kick_ball()

    def handle_input(self, dt):
        """Continuous controls, held between frames. (Audit finding B12)"""
        keys = pygame.key.get_pressed()
        self.orbit += (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * 60.0 * dt
        self.elevation = max(5.0, min(89.0, self.elevation
                                      + (keys[pygame.K_UP] - keys[pygame.K_DOWN])
                                      * 45.0 * dt))
        if keys[pygame.K_PLUS] or keys[pygame.K_EQUALS]:
            self.pitch_spans = min(30.0, self.pitch_spans + 4.0 * dt)
            self.distance = max(25.0, self.distance - 60.0 * dt)
        if keys[pygame.K_MINUS]:
            self.pitch_spans = max(1.0, self.pitch_spans - 4.0 * dt)
            self.distance = min(400.0, self.distance + 60.0 * dt)

    def kick_ball(self):
        """Give the ball a nudge towards a random part of the pitch."""
        angle = np.random.uniform(0, 2 * math.pi)
        self.ball_vel = [math.cos(angle) * KICK_SPEED * 0.5,
                         KICK_LIFT,
                         math.sin(angle) * KICK_SPEED * 0.5]

    def update(self, dt):
        physics3d.step_ball(self.ball_pos, self.ball_vel, dt, self.pitch,
                            self.ball_radius)
        side = physics3d.detect_goal(self.ball_pos, self.pitch)
        if side is not None:
            self.score[1 if side == "left" else 0] += 1
            soccer_gl.add_effect(self.effects, 'goal', self.ball_pos)
            self.ball_pos, self.ball_vel = physics3d.kickoff_state()
        soccer_gl.update_effects(self.effects, dt)
        self.animation_time += dt

    def render(self, dt):
        """Render one frame: camera background, then the scene."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glViewport(0, 0, self.width, self.height)

        frame = self.read_frame() if self.ar_mode else None

        if frame is None:
            # No camera, or AR turned off: orbiting desktop view.
            self.draw_scene_desktop()
            self.draw_hud("Desktop view - press A for AR"
                          if self.cap is not None else
                          "No camera - desktop view (C: next camera)")
            pygame.display.flip()
            return

        self.draw_camera_background(frame)

        modelview = self.estimate_pose(frame)
        if modelview is not None:
            self.last_modelview = modelview
            self.time_since_seen = 0.0
            self.marker_visible = True
        else:
            self.time_since_seen += dt
            self.marker_visible = False

        # Keep showing the last pose briefly so a dropped frame does not
        # make the pitch flicker in and out.
        if (self.last_modelview is not None
                and self.time_since_seen <= POSE_MEMORY_SECONDS):
            self.draw_scene_on_marker(self.last_modelview)
            self.draw_hud(f"Tracking marker {FIELD_MARKER_ID}"
                          if self.marker_visible else "Marker lost...",
                          (120, 240, 170) if self.marker_visible else (240, 210, 120))
        else:
            self.draw_hud(f"Searching for marker {FIELD_MARKER_ID} - "
                          "print it and hold it flat in view",
                          (240, 210, 120))

        pygame.display.flip()

    def run(self):
        """Main loop."""
        while self.running:
            dt = min(self.clock.tick(60) / 1000.0, 0.05)
            self.handle_events()
            self.handle_input(dt)
            self.update(dt)
            self.render(dt)

        if self.cap is not None:
            self.cap.release()
        pygame.quit()


def main():
    parser = argparse.ArgumentParser(
        description="Soccer AR experience (experimental).")
    parser.add_argument("--camera", type=int, default=0,
                        help="camera index (default: 0)")
    parser.add_argument("--marker-mm", type=float, default=100.0,
                        help="printed marker size in millimetres (default: 100)")
    parser.add_argument("--pitch-spans", type=float, default=6.0,
                        help="pitch width in marker widths (default: 6)")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--fullscreen", action="store_true")
    args = parser.parse_args()

    app = ARSoccerExperience(width=args.width, height=args.height,
                             camera_index=args.camera,
                             marker_length=args.marker_mm / 1000.0,
                             pitch_spans=args.pitch_spans,
                             fullscreen=args.fullscreen)
    app.run()


if __name__ == "__main__":
    main()
