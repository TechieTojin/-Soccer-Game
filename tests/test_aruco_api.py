"""Tests for the ArUco marker API used by the AR prototype.

These guard audit finding B1: the AR code used `aruco.Dictionary_get` and
`aruco.DetectorParameters_create`, which OpenCV removed in 4.7, so the
module raised AttributeError at import time.

They verify the API wrappers only. They do NOT verify that the AR mode
renders correctly - that still needs a webcam and manual checking.
"""

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2", reason="OpenCV is required for the AR tests")
aruco = pytest.importorskip("cv2.aruco", reason="cv2.aruco is required (opencv-contrib-python)")


def test_ar_module_imports_without_a_camera():
    """Importing the AR module must not touch the ArUco factory functions
    at import time (it used to crash here on modern OpenCV)."""
    import ar_soccer_experience

    assert hasattr(ar_soccer_experience, "create_aruco_detector")


def test_create_aruco_detector_returns_a_usable_dictionary():
    from ar_soccer_experience import create_aruco_detector

    dictionary, detector = create_aruco_detector()

    assert dictionary is not None
    # On OpenCV >= 4.7 we expect the new detector object; on older versions
    # the helper returns None and the legacy function path is used.
    if hasattr(aruco, "ArucoDetector"):
        assert detector is not None


def test_marker_generation_and_detection_round_trip():
    """Generate marker ID 0 and detect it again through the same helpers."""
    from ar_soccer_experience import create_aruco_detector, detect_aruco_markers

    dictionary, detector = create_aruco_detector()

    size = 200
    if hasattr(aruco, "generateImageMarker"):
        marker = aruco.generateImageMarker(dictionary, 0, size)
    else:
        marker = aruco.drawMarker(dictionary, 0, size)

    # Pad with a white quiet zone, which ArUco detection requires.
    padded = np.full((size + 100, size + 100), 255, dtype=np.uint8)
    padded[50:50 + size, 50:50 + size] = marker

    corners, ids, _ = detect_aruco_markers(padded, dictionary, detector)

    assert ids is not None, "marker was generated but could not be detected"
    assert 0 in ids.flatten()
    assert len(corners) == 1


# ---------------------------------------------------------------------------
# Standalone marker generator (tools/make_markers.py)
# ---------------------------------------------------------------------------

class TestMarkerGenerator:
    """The generator must produce markers the AR mode can actually detect,
    without installing packages or downloading datasets. (Audit finding B19)"""

    def test_printable_marker_is_detectable(self):
        from tools.make_markers import build_printable, get_dictionary
        from ar_soccer_experience import create_aruco_detector, detect_aruco_markers

        image = build_printable(get_dictionary("DICT_4X4_50"), 3, size_mm=50)
        dictionary, detector = create_aruco_detector()
        _, ids, _ = detect_aruco_markers(image, dictionary, detector)

        assert ids is not None, "generated marker could not be detected"
        assert 3 in ids.flatten()

    def test_printable_includes_a_quiet_zone(self):
        """ArUco needs white space around the marker to find it."""
        from tools.make_markers import build_printable, get_dictionary

        image = build_printable(get_dictionary("DICT_4X4_50"), 0, size_mm=50,
                                label=False)
        assert image[0, 0] == 255
        assert image[0, -1] == 255

    def test_size_in_mm_controls_the_pixel_size(self):
        from tools.make_markers import build_printable, get_dictionary

        dictionary = get_dictionary("DICT_4X4_50")
        small = build_printable(dictionary, 0, size_mm=50, label=False)
        large = build_printable(dictionary, 0, size_mm=100, label=False)
        assert large.shape[0] > small.shape[0]

    def test_cli_writes_files(self, tmp_path):
        from tools.make_markers import main

        assert main(["--ids", "0", "1", "--size-mm", "40",
                     "--out", str(tmp_path)]) == 0
        written = sorted(p.name for p in tmp_path.glob("*.png"))
        assert written == ["marker_0_40mm.png", "marker_1_40mm.png"]
