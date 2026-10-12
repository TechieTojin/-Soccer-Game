"""Generate printable ArUco markers for the AR mode.

Standalone on purpose: it only writes PNG files. The previous way to get a
marker was `setup_ar_vr.py`, which also pip-installed packages and
downloaded a 41 MB dataset - far too much for "I need a marker to print".
(Audit finding B19)

Usage:
    python tools/make_markers.py                     # marker 0, 100 mm
    python tools/make_markers.py --ids 0 1 2         # several markers
    python tools/make_markers.py --size-mm 150       # bigger marker
    python tools/make_markers.py --out my_markers    # choose a folder

Print the PNG at 100% scale (no "fit to page"), measure the printed black
square, and pass that measurement to the AR app:

    python ar_soccer_experience.py --marker-mm 98
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

try:
    import cv2
    import cv2.aruco as aruco
except ImportError:  # pragma: no cover - depends on the environment
    print("OpenCV is required. Install it with:\n"
          "    pip install -r requirements.txt")
    raise SystemExit(1) from None

# Printing at 300 DPI gives a crisp marker at any sensible size.
DPI = 300
MM_PER_INCH = 25.4
# White margin around the marker. ArUco needs a quiet zone to detect it.
QUIET_ZONE_FRACTION = 0.25


def get_dictionary(dictionary_name: str):
    """Return a predefined ArUco dictionary, on old or new OpenCV.

    OpenCV 4.7 replaced `Dictionary_get` with `getPredefinedDictionary`.
    """
    dictionary_id = getattr(aruco, dictionary_name)
    if hasattr(aruco, "getPredefinedDictionary"):
        return aruco.getPredefinedDictionary(dictionary_id)
    return aruco.Dictionary_get(dictionary_id)


def draw_marker(dictionary, marker_id: int, pixels: int) -> np.ndarray:
    """Render one marker, on old or new OpenCV.

    `drawMarker` became `generateImageMarker` in OpenCV 4.7.
    """
    if hasattr(aruco, "generateImageMarker"):
        return aruco.generateImageMarker(dictionary, marker_id, pixels)
    return aruco.drawMarker(dictionary, marker_id, pixels)


def build_printable(dictionary, marker_id: int, size_mm: float,
                    label: bool = True) -> np.ndarray:
    """Return a print-ready image: marker, quiet zone and a size caption."""
    pixels = max(50, int(round(size_mm / MM_PER_INCH * DPI)))
    marker = draw_marker(dictionary, marker_id, pixels)

    quiet = int(pixels * QUIET_ZONE_FRACTION)
    canvas_size = pixels + 2 * quiet
    caption_height = int(pixels * 0.12) if label else 0

    canvas = np.full((canvas_size + caption_height, canvas_size), 255,
                     dtype=np.uint8)
    canvas[quiet:quiet + pixels, quiet:quiet + pixels] = marker

    if label:
        text = f"ID {marker_id}   {size_mm:.0f} mm   print at 100%"
        cv2.putText(canvas, text, (quiet, canvas_size + caption_height // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, pixels / 1400.0, 0,
                    max(1, pixels // 400), cv2.LINE_AA)
    return canvas


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate printable ArUco markers for the AR mode.")
    parser.add_argument("--ids", type=int, nargs="+", default=[0],
                        help="marker IDs to generate (default: 0)")
    parser.add_argument("--size-mm", type=float, default=100.0,
                        help="printed marker size in millimetres (default: 100)")
    parser.add_argument("--dictionary", default="DICT_4X4_50",
                        help="ArUco dictionary (default: DICT_4X4_50)")
    parser.add_argument("--out", default="ar_markers",
                        help="output directory (default: ar_markers)")
    parser.add_argument("--no-label", action="store_true",
                        help="omit the printed caption")
    args = parser.parse_args(argv)

    try:
        dictionary = get_dictionary(args.dictionary)
    except AttributeError:
        print(f"Unknown ArUco dictionary: {args.dictionary}")
        return 1

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for marker_id in args.ids:
        image = build_printable(dictionary, marker_id, args.size_mm,
                                label=not args.no_label)
        path = out_dir / f"marker_{marker_id}_{args.size_mm:.0f}mm.png"
        if not cv2.imwrite(str(path), image):
            print(f"Failed to write {path}")
            return 1
        print(f"Wrote {path}  ({image.shape[1]}x{image.shape[0]} px @ {DPI} DPI)")

    print("\nPrint at 100% scale, then measure the black square and pass it to:")
    print(f"    python ar_soccer_experience.py --marker-mm {args.size_mm:.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
