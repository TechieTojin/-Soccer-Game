"""Camera pose and projection maths for the AR mode.

Pure NumPy: no OpenCV, no OpenGL, so all of it is unit-testable. The AR
module calls `cv2.solvePnP` to get a rotation and translation, then uses
these helpers to turn them into OpenGL matrices.

Three defects in the original AR code are addressed here (audit finding B11):

1. **No coordinate-system conversion.** OpenCV's camera frame is X right,
   Y *down*, Z *into* the scene. OpenGL's is X right, Y *up*, Z *out of*
   the screen. Loading an OpenCV pose straight into the modelview matrix,
   as the original did, mirrors the scene vertically and in depth.
   `cv_pose_to_gl_modelview` applies the diag(1, -1, -1) flip.
2. **Projection unrelated to the camera.** The original called
   `gluPerspective(45, ...)` while telling `solvePnP` the focal length was
   the *window* width, so the pose and the projection disagreed and the
   overlay could not line up. `projection_from_intrinsics` derives the GL
   projection from the same intrinsics given to solvePnP.
3. **Marker size ignored.** The marker was described as 10 units across
   while the pitch is 105 units long, so the pitch was about ten times the
   size of the marker. Object points are now in metres at the marker's real
   printed size, which makes the translation metric and lets the scene be
   scaled to a sensible size on the table.
"""

from __future__ import annotations

import numpy as np

# Maps an OpenCV camera frame to an OpenGL one: flip Y and Z.
CV_TO_GL = np.diag([1.0, -1.0, -1.0, 1.0]).astype(np.float64)

# Maps our Y-up scene onto the marker's own plane.
#
# A marker's local frame has its normal along +Z (OpenCV's convention for a
# planar target, and what SOLVEPNP_IPPE_SQUARE requires), while the pitch is
# modelled with Y up. This rotation - +90 degrees about X - sends the
# scene's "up" to the marker's normal, so the pitch lies *on* the marker
# instead of standing upright through it.
SCENE_TO_MARKER = np.array([
    [1.0, 0.0, 0.0, 0.0],
    [0.0, 0.0, -1.0, 0.0],
    [0.0, 1.0, 0.0, 0.0],
    [0.0, 0.0, 0.0, 1.0],
], dtype=np.float64)


def approximate_intrinsics(width: int, height: int,
                           horizontal_fov_degrees: float = 60.0
                           ) -> tuple[float, float, float, float]:
    """Rough `(fx, fy, cx, cy)` for an uncalibrated webcam.

    Derived from the *frame* size and an assumed field of view. The original
    code used the application window's width as the focal length, which has
    nothing to do with the camera that produced the frame.

    This is a guess, not a calibration: the overlay will sit approximately,
    not exactly, on the marker. Calibrating the camera properly (OpenCV's
    chessboard procedure) and passing the real matrix gives a better fit.
    """
    fov = np.radians(horizontal_fov_degrees)
    fx = (width / 2.0) / np.tan(fov / 2.0)
    return float(fx), float(fx), width / 2.0, height / 2.0


def camera_matrix(fx: float, fy: float, cx: float, cy: float) -> np.ndarray:
    """Assemble a 3x3 pinhole camera matrix."""
    return np.array([[fx, 0.0, cx],
                     [0.0, fy, cy],
                     [0.0, 0.0, 1.0]], dtype=np.float64)


def marker_object_points(marker_length: float) -> np.ndarray:
    """Corners of the marker in its own frame, in metres.

    The marker lies in the Z = 0 plane with its normal along +Z, and the
    corners are ordered top-left, top-right, bottom-right, bottom-left -
    the order ArUco reports them in, and the order `SOLVEPNP_IPPE_SQUARE`
    requires. Putting the marker in any other plane makes that solver fail
    outright, which is exactly what the pose round-trip test caught.

    The scene is Y-up rather than Z-up, so `cv_pose_to_gl_modelview`
    applies `SCENE_TO_MARKER` to lay the pitch down on the marker.
    """
    half = marker_length / 2.0
    return np.array([
        [-half, half, 0.0],
        [half, half, 0.0],
        [half, -half, 0.0],
        [-half, -half, 0.0],
    ], dtype=np.float64)


def projection_from_intrinsics(fx: float, fy: float, cx: float, cy: float,
                               width: int, height: int,
                               near: float = 0.01,
                               far: float = 100.0) -> np.ndarray:
    """Build an OpenGL projection matrix from pinhole intrinsics.

    The result is the 4x4 matrix in row-major (NumPy) order; pass its
    transpose to `glLoadMatrixf`, which expects column-major data.

    Using the same intrinsics for the projection and for `solvePnP` is what
    makes the rendered scene line up with the marker in the video frame.
    """
    projection = np.zeros((4, 4), dtype=np.float64)
    projection[0, 0] = 2.0 * fx / width
    projection[0, 2] = 1.0 - 2.0 * cx / width
    projection[1, 1] = 2.0 * fy / height
    projection[1, 2] = 2.0 * cy / height - 1.0
    projection[2, 2] = -(far + near) / (far - near)
    projection[2, 3] = -2.0 * far * near / (far - near)
    projection[3, 2] = -1.0
    return projection


def cv_pose_to_gl_modelview(rotation: np.ndarray, translation: np.ndarray,
                            align_scene: bool = True) -> np.ndarray:
    """Convert an OpenCV marker pose into an OpenGL modelview matrix.

    `rotation` is the 3x3 matrix from `cv2.Rodrigues` and `translation` the
    3-vector from `solvePnP`. With `align_scene` (the default) the result
    also lays the Y-up scene flat on the marker, so a pitch drawn in the XZ
    plane appears lying on the table.

    The result is row-major; pass its transpose to `glLoadMatrixf`, which
    expects column-major data.
    """
    pose = np.eye(4, dtype=np.float64)
    pose[:3, :3] = np.asarray(rotation, dtype=np.float64)
    pose[:3, 3] = np.asarray(translation, dtype=np.float64).reshape(3)

    modelview = CV_TO_GL @ pose
    if align_scene:
        modelview = modelview @ SCENE_TO_MARKER
    return modelview


def scene_scale(marker_length: float, pitch_length: float,
                pitch_spans: float = 6.0) -> float:
    """Scale factor that fits the pitch onto the table.

    The pitch is modelled at life size (about 105 m long) but has to appear
    a few marker-widths across on a desk. `pitch_spans` is how many marker
    lengths the pitch should cover.
    """
    return (marker_length * pitch_spans) / pitch_length
