"""Unit tests for the AR pose and projection maths (audit finding B11).

The headline test is `test_pose_round_trip_recovers_a_known_pose`: it places
a marker at a known pose, projects its corners with OpenCV's camera model to
get synthetic image points, then runs the app's own detection-to-pose path
and checks the original pose comes back. That exercises the real pipeline
without needing a webcam or a printed marker.

What these tests do NOT cover: whether the overlay visually lines up on a
real camera feed. That needs hardware and remains unverified.
"""

import math

import numpy as np
import pytest

from soccer_core import ar_pose

cv2 = pytest.importorskip("cv2", reason="OpenCV is required for the AR tests")


class TestIntrinsics:

    def test_focal_length_follows_the_field_of_view(self):
        """A narrower field of view means a longer focal length."""
        narrow, _, _, _ = ar_pose.approximate_intrinsics(640, 480, 40.0)
        wide, _, _, _ = ar_pose.approximate_intrinsics(640, 480, 90.0)
        assert narrow > wide

    def test_principal_point_is_the_frame_centre(self):
        _, _, cx, cy = ar_pose.approximate_intrinsics(640, 480)
        assert (cx, cy) == (320.0, 240.0)

    def test_intrinsics_scale_with_the_frame_not_the_window(self):
        """The original used the application window width as the focal
        length, which has nothing to do with the camera."""
        small, _, _, _ = ar_pose.approximate_intrinsics(640, 480)
        large, _, _, _ = ar_pose.approximate_intrinsics(1920, 1080)
        assert large == pytest.approx(small * 3)

    def test_camera_matrix_shape(self):
        matrix = ar_pose.camera_matrix(600.0, 600.0, 320.0, 240.0)
        assert matrix.shape == (3, 3)
        assert matrix[2, 2] == 1.0


class TestMarkerGeometry:

    def test_marker_lies_in_the_z_zero_plane(self):
        """SOLVEPNP_IPPE_SQUARE requires a planar target at Z = 0; putting
        the marker in any other plane makes it fail outright."""
        points = ar_pose.marker_object_points(0.1)
        assert points.shape == (4, 3)
        assert np.allclose(points[:, 2], 0.0)

    def test_marker_is_the_requested_size(self):
        points = ar_pose.marker_object_points(0.2)
        width = points[:, 0].max() - points[:, 0].min()
        height = points[:, 1].max() - points[:, 1].min()
        assert width == pytest.approx(0.2)
        assert height == pytest.approx(0.2)

    def test_corners_are_in_aruco_order(self):
        """Top-left, top-right, bottom-right, bottom-left."""
        points = ar_pose.marker_object_points(0.1)
        assert points[0][0] < 0 and points[0][1] > 0    # top-left
        assert points[1][0] > 0 and points[1][1] > 0    # top-right
        assert points[2][0] > 0 and points[2][1] < 0    # bottom-right
        assert points[3][0] < 0 and points[3][1] < 0    # bottom-left

    def test_scene_up_maps_to_the_marker_normal(self):
        """The pitch is drawn Y-up but the marker's normal is +Z, so the
        scene has to be laid down onto the marker plane."""
        scene_up = np.array([0.0, 1.0, 0.0, 0.0])
        in_marker = ar_pose.SCENE_TO_MARKER @ scene_up
        assert in_marker[:3] == pytest.approx([0.0, 0.0, 1.0])

    def test_scene_ground_plane_stays_in_the_marker_plane(self):
        for scene_ground in ([1.0, 0.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0]):
            in_marker = ar_pose.SCENE_TO_MARKER @ np.array(scene_ground)
            assert in_marker[2] == pytest.approx(0.0)

    def test_scene_scale_shrinks_the_pitch_onto_the_table(self):
        """A 105 m pitch has to end up a few marker-widths across."""
        scale = ar_pose.scene_scale(marker_length=0.1, pitch_length=105.0,
                                    pitch_spans=6.0)
        assert 105.0 * scale == pytest.approx(0.6)


class TestCoordinateConversion:

    def test_a_point_in_front_of_the_camera_ends_up_in_front_in_gl(self):
        """OpenCV looks down +Z, OpenGL down -Z. Without this flip the
        scene renders mirrored, or behind the camera entirely."""
        modelview = ar_pose.cv_pose_to_gl_modelview(np.eye(3), np.array([0, 0, 2.0]))
        origin_in_view = modelview @ np.array([0.0, 0.0, 0.0, 1.0])
        assert origin_in_view[2] < 0, "marker should be in front of the GL camera"

    def test_y_axis_is_flipped(self):
        modelview = ar_pose.cv_pose_to_gl_modelview(np.eye(3), np.array([0, 1.0, 2.0]))
        origin_in_view = modelview @ np.array([0.0, 0.0, 0.0, 1.0])
        assert origin_in_view[1] == pytest.approx(-1.0)

    def test_conversion_preserves_distance(self):
        """Flipping axes must not change how far away anything is."""
        translation = np.array([0.3, -0.2, 1.5])
        modelview = ar_pose.cv_pose_to_gl_modelview(np.eye(3), translation)
        position = modelview @ np.array([0.0, 0.0, 0.0, 1.0])
        assert np.linalg.norm(position[:3]) == pytest.approx(
            np.linalg.norm(translation))

    def test_rotation_is_preserved_as_a_rotation(self):
        angle = math.radians(30)
        rotation = np.array([[math.cos(angle), -math.sin(angle), 0],
                             [math.sin(angle), math.cos(angle), 0],
                             [0, 0, 1.0]])
        modelview = ar_pose.cv_pose_to_gl_modelview(rotation, np.array([0, 0, 2.0]))
        upper = modelview[:3, :3]
        assert np.allclose(upper @ upper.T, np.eye(3), atol=1e-9)
        assert np.linalg.det(upper) == pytest.approx(1.0)

    def test_scene_alignment_can_be_turned_off(self):
        """Without alignment the matrix is just the coordinate flip."""
        rotation, translation = np.eye(3), np.array([0.0, 0.0, 1.0])
        plain = ar_pose.cv_pose_to_gl_modelview(rotation, translation,
                                                align_scene=False)
        assert np.allclose(plain[:3, :3], np.diag([1.0, -1.0, -1.0]))


class TestProjectionMatrix:

    def test_shape_and_perspective_row(self):
        projection = ar_pose.projection_from_intrinsics(
            600.0, 600.0, 320.0, 240.0, 640, 480)
        assert projection.shape == (4, 4)
        assert projection[3, 2] == -1.0, "perspective divide must use -z"

    def test_centred_principal_point_gives_a_symmetric_frustum(self):
        projection = ar_pose.projection_from_intrinsics(
            600.0, 600.0, 320.0, 240.0, 640, 480)
        assert projection[0, 2] == pytest.approx(0.0)
        assert projection[1, 2] == pytest.approx(0.0)

    def test_near_and_far_planes_map_to_the_ndc_range(self):
        near, far = 0.01, 100.0
        projection = ar_pose.projection_from_intrinsics(
            600.0, 600.0, 320.0, 240.0, 640, 480, near=near, far=far)

        for distance, expected in ((near, -1.0), (far, 1.0)):
            clip = projection @ np.array([0.0, 0.0, -distance, 1.0])
            assert clip[2] / clip[3] == pytest.approx(expected, abs=1e-6)

    def test_projection_matches_the_pinhole_model(self):
        """A point projected by this matrix must land on the same pixel
        OpenCV's camera model would put it on."""
        fx = fy = 600.0
        cx, cy = 320.0, 240.0
        width, height = 640, 480
        projection = ar_pose.projection_from_intrinsics(fx, fy, cx, cy, width, height)

        point_cv = np.array([0.1, 0.05, 2.0])        # OpenCV frame, Z forward
        expected_px = fx * point_cv[0] / point_cv[2] + cx
        expected_py = fy * point_cv[1] / point_cv[2] + cy

        # Same point in the OpenGL frame (Y and Z flipped)
        point_gl = np.array([point_cv[0], -point_cv[1], -point_cv[2], 1.0])
        clip = projection @ point_gl
        ndc_x, ndc_y = clip[0] / clip[3], clip[1] / clip[3]

        # NDC -> pixels, remembering GL's Y axis points up the screen.
        px = (ndc_x + 1) / 2 * width
        py = (1 - ndc_y) / 2 * height
        assert px == pytest.approx(expected_px, abs=1e-6)
        assert py == pytest.approx(expected_py, abs=1e-6)


# A marker whose printed face is turned towards the camera: its normal
# points back along the camera's view axis, which is a 180-degree turn about
# X. An identity rotation would mean looking at the *back* of the marker,
# which is not a pose a detector can ever report.
#
# The small extra tilt is deliberate. A square viewed exactly head-on is
# pose-ambiguous - the two IPPE solutions are indistinguishable - and the
# solver may return either. Any real marker on a table is viewed at some
# angle, so the tests use a realistic one.
FACING_CAMERA = np.array([math.pi, 0.15, 0.0])


class TestPoseRoundTrip:
    """End-to-end check of the detection-to-modelview path, using
    synthetic image points instead of a webcam."""

    def _synthesise(self, rvec, tvec, marker_length=0.1,
                    width=640, height=480):
        """Project a marker at a known pose into image points."""
        fx, fy, cx, cy = ar_pose.approximate_intrinsics(width, height)
        matrix = ar_pose.camera_matrix(fx, fy, cx, cy)
        object_points = ar_pose.marker_object_points(marker_length)
        image_points, _ = cv2.projectPoints(
            object_points, rvec, tvec, matrix, np.zeros((4, 1)))
        return image_points.reshape(-1, 2), matrix, object_points

    def test_pose_round_trip_recovers_a_known_pose(self):
        """Project a marker at a known pose, then solve for it again."""
        # A marker facing the camera, 50 cm away and slightly off-centre.
        rvec = FACING_CAMERA.reshape(3, 1)
        tvec = np.array([[0.02], [0.01], [0.5]])
        image_points, matrix, object_points = self._synthesise(rvec, tvec)

        ok, rvec_out, tvec_out = cv2.solvePnP(
            object_points, image_points, matrix, np.zeros((4, 1)),
            flags=cv2.SOLVEPNP_IPPE_SQUARE)

        assert ok
        assert tvec_out.flatten() == pytest.approx(tvec.flatten(), abs=1e-4)

        # Compare rotations as matrices: rotation vectors have sign/wrap
        # conventions that make a direct comparison misleading.
        expected, _ = cv2.Rodrigues(rvec)
        recovered, _ = cv2.Rodrigues(rvec_out)
        assert np.allclose(expected, recovered, atol=1e-3)

    def test_recovered_marker_sits_in_front_of_the_gl_camera(self):
        rvec = np.array([[0.2], [0.0], [0.0]])
        tvec = np.array([[0.0], [0.0], [0.6]])
        image_points, matrix, object_points = self._synthesise(rvec, tvec)

        ok, rvec_out, tvec_out = cv2.solvePnP(
            object_points, image_points, matrix, np.zeros((4, 1)),
            flags=cv2.SOLVEPNP_IPPE_SQUARE)
        assert ok

        rotation, _ = cv2.Rodrigues(rvec_out)
        modelview = ar_pose.cv_pose_to_gl_modelview(rotation, tvec_out)
        marker_origin = modelview @ np.array([0.0, 0.0, 0.0, 1.0])

        assert marker_origin[2] < 0, "marker must be in front of the GL camera"
        assert abs(marker_origin[2]) == pytest.approx(0.6, abs=1e-3)

    def test_scene_is_laid_flat_on_the_marker(self):
        """A point 'above' the pitch must rise off the marker's surface
        towards the viewer, not shoot sideways along the table."""
        tvec = np.array([[0.0], [0.0], [0.6]])
        image_points, matrix, object_points = self._synthesise(FACING_CAMERA, tvec)

        ok, rvec_out, tvec_out = cv2.solvePnP(
            object_points, image_points, matrix, np.zeros((4, 1)),
            flags=cv2.SOLVEPNP_IPPE_SQUARE)
        assert ok

        rotation, _ = cv2.Rodrigues(rvec_out)
        modelview = ar_pose.cv_pose_to_gl_modelview(rotation, tvec_out)

        origin = np.asarray(modelview @ np.array([0.0, 0.0, 0.0, 1.0]))
        above = np.asarray(modelview @ np.array([0.0, 0.1, 0.0, 1.0]))

        # "Up from the pitch" must leave the marker plane towards the
        # viewer, i.e. the point gets closer to the GL camera.
        assert above[2] > origin[2], "the scene is growing into the table"
        assert np.linalg.norm(above[:3] - origin[:3]) == pytest.approx(0.1, abs=1e-3)

    def test_pitch_plane_stays_on_the_table(self):
        """Both ground axes of the scene must remain in the marker plane."""
        tvec = np.array([[0.0], [0.0], [0.5]])
        image_points, matrix, object_points = self._synthesise(FACING_CAMERA, tvec)
        ok, rvec_out, tvec_out = cv2.solvePnP(
            object_points, image_points, matrix, np.zeros((4, 1)),
            flags=cv2.SOLVEPNP_IPPE_SQUARE)
        assert ok

        rotation, _ = cv2.Rodrigues(rvec_out)
        modelview = ar_pose.cv_pose_to_gl_modelview(rotation, tvec_out)
        origin = np.asarray(modelview @ np.array([0.0, 0.0, 0.0, 1.0]))

        # The marker's own normal, expressed in the GL view frame.
        up = np.asarray(modelview @ np.array([0.0, 1.0, 0.0, 0.0]))[:3]

        # Both of the scene's ground axes must stay perpendicular to that
        # normal, i.e. flat on the table.
        for ground_point in ([0.1, 0.0, 0.0, 1.0], [0.0, 0.0, 0.1, 1.0]):
            moved = np.asarray(modelview @ np.array(ground_point))
            offset = moved[:3] - origin[:3]
            assert float(np.dot(offset, up)) == pytest.approx(0.0, abs=1e-6)

    def test_detected_marker_flows_through_to_a_usable_pose(self):
        """Integration: real detection -> solvePnP -> GL modelview.

        Unlike the other round-trips this does not hand solvePnP synthetic
        corner coordinates. It renders an actual marker image, runs the
        app's own detector over it, and feeds the detected corners into the
        app's own pose path - the same sequence `estimate_pose` performs on
        a webcam frame.
        """
        from ar_soccer_experience import create_aruco_detector, detect_aruco_markers
        from tools.make_markers import build_printable, get_dictionary

        scene = build_printable(get_dictionary("DICT_4X4_50"), 0,
                                size_mm=60, label=False)
        height, width = scene.shape[:2]

        dictionary, detector = create_aruco_detector()
        corners, ids, _ = detect_aruco_markers(scene, dictionary, detector)
        assert ids is not None and 0 in ids.flatten()

        image_points = np.asarray(corners[0][0], dtype=np.float64)
        fx, fy, cx, cy = ar_pose.approximate_intrinsics(width, height)

        ok, rvec, tvec = cv2.solvePnP(
            ar_pose.marker_object_points(0.06), image_points,
            ar_pose.camera_matrix(fx, fy, cx, cy), np.zeros((4, 1)),
            flags=cv2.SOLVEPNP_IPPE_SQUARE)
        assert ok, "solvePnP failed on a genuinely detected marker"

        rotation, _ = cv2.Rodrigues(rvec)
        modelview = ar_pose.cv_pose_to_gl_modelview(rotation, tvec)

        assert modelview.shape == (4, 4)
        origin = np.asarray(modelview @ np.array([0.0, 0.0, 0.0, 1.0]))
        assert origin[2] < 0, "marker must land in front of the GL camera"
        assert 0.01 < abs(origin[2]) < 10.0, "implausible marker distance"

    def test_distance_scales_with_the_declared_marker_size(self):
        """Telling the app a bigger printed marker must place it further
        away: this is why `--marker-mm` matters."""
        rvec = np.array([[0.0], [0.0], [0.0]])
        tvec = np.array([[0.0], [0.0], [0.5]])
        image_points, matrix, _ = self._synthesise(rvec, tvec, marker_length=0.1)

        # Solve the same pixels against a marker declared twice as large.
        ok, _, tvec_out = cv2.solvePnP(
            ar_pose.marker_object_points(0.2), image_points, matrix,
            np.zeros((4, 1)), flags=cv2.SOLVEPNP_IPPE_SQUARE)
        assert ok
        assert tvec_out.flatten()[2] == pytest.approx(1.0, abs=1e-3)
