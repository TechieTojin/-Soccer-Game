# Verification Report

This records exactly what was tested, when, how, and what the result was —
separately from what is claimed but not run. If a capability is not listed
here with a result, treat it as unverified. Screenshots referenced below are
in [docs/screenshots/](screenshots/) and were captured during this session,
not staged or edited.

**Session date:** 2026-10-12
**Tested by:** automated tooling + a live interactive session, both run by
Claude Code against the working tree before any of this phase's changes were
committed.

## Environment

| | |
|---|---|
| OS | Windows 11 (build 26200), via Git Bash / MSYS |
| Python | 3.10.0 |
| pygame | 2.6.1 (SDL 2.28.4) |
| PyOpenGL | 3.1.10 |
| OpenCV | 5.0.0 (`opencv-python-headless`, with `cv2.aruco` present) |
| pytest | 9.1.1 |
| ruff | 0.17.0 |
| GPU | Intel(R) Iris(R) Xe Graphics, OpenGL 4.6.0 (driver build 30.0.101.1960) |
| Webcam | A real camera at index 0 opened successfully (1 device tested) |

This is a single environment. None of this has been checked on a different
GPU vendor (AMD/NVIDIA), a different OS, or a different webcam — see
§6 for what that gap means in practice.

## 1. Automated tests

```
$ python -m pytest -v
...
tests\test_ar_pose.py .........................                          [ 22%]
tests\test_aruco_api.py .......                                          [ 28%]
tests\test_core_physics.py ............................                  [ 53%]
tests\test_gameplay.py ............................                      [ 77%]
tests\test_stereo_and_formations.py .........................            [100%]
============================= 113 passed in 2.24s ==============================
```

```
$ python -m ruff check .
All checks passed!
```

```
$ python tests/smoke_2d.py --frames 600
Smoke test passed:
  - menu
  - help
  - 600 match frames
  - ball in bounds
  - goal banner
  - pause overlay
  - full-time screen
  - restart
```

All three commands were run to completion in this session; the output above
is the real output, not a paraphrase. The inherited research pipeline
(`soccer3d/`, `utils/`, `demo/`) is intentionally excluded from all three —
see `ruff.toml` and `pytest.ini` for the exclusion and
`SOCCER_PROJECT_AUDIT.md` §9 for why.

## 2. Mode-by-mode verification

### 2D Soccer Game — **Verified, real screen, interactive-equivalent**

Run via the headless harness (`tests/smoke_2d.py`) with SDL's dummy video
driver, which exercises the exact same `SoccerGame` class and draw calls a
real window would, and separately confirmed with a live (non-dummy) OpenGL
window during this session.

Checked: menu navigation (keyboard and mouse hover, both drive the same
`menu_index`), the controls screen, a simulated match (600 frames, ball
stays within the pitch bounds, goal scoring, kicking, team switching, player
selection), the non-blocking goal banner, pause, restart (clock and score
both reset), and full-time.

| Screenshot | Shows |
|---|---|
| `docs/screenshots/menu.png` | Main menu |
| `docs/screenshots/help.png` | Controls screen |
| `docs/screenshots/match.png` | A simulated match in progress |
| `docs/screenshots/goal_banner.png` | Non-blocking goal celebration |
| `docs/screenshots/paused.png` | Pause overlay |
| `docs/screenshots/full_time.png` | Full-time screen |

**Not verified:** a human has not played a full 90-second match start to
finish with real keyboard input, or confirmed the controls "feel" right.

### 3D Field Viewer — **Verified on real GPU hardware**

Instantiated `SoccerFieldViewer` against a real (non-dummy) OpenGL 4.6
context on the GPU listed above, ran 90 simulated frames with the orbit
camera active, and read back the actual framebuffer (`glReadPixels`, not
`pygame.image.save`, which does not read GL-rendered content — see §5).

Confirmed from the captured frame (`docs/screenshots/viewer_3d.png`):
pitch markings (touchlines, penalty areas, six-yard boxes, centre circle,
corner arcs) render correctly proportioned; both goals stand upright on the
goal line, posts vertical; all 22 players stand upright with a visible
head/torso/legs silhouette, not lying on their sides. This directly confirms
the Phase 2 fix for audit finding B16 (previously players were extruded flat
and the camera was discarded every frame).

**Not verified:** orbit/zoom key response in a live interactive session (the
input-handling code path was exercised by calling `handle_input()` directly
with synthetic key state, not by pressing real keys).

### VR Stereo Prototype — **Verified on real GPU hardware**

Same approach: real GL context, `VRSoccerExperience` instantiated, camera
placed to frame the pitch, `update()` run for 90 frames, `render()` called
in both modes.

Confirmed from the captured frames:
- `docs/screenshots/vr_mono.png` — single-view mode: an eye-level walk-through
  perspective showing the near and far goals both upright, players standing,
  pitch markings intact.
- `docs/screenshots/vr_stereo.png` — stereo mode: two side-by-side halves,
  each with the correct (not squashed) aspect ratio, and a visible positional
  difference between the halves consistent with real binocular parallax
  (confirming the Phase 2 fix for audit finding B13 — eyes separated along
  the camera's right vector rather than world X).

**Not verified:** viewing this through an actual stereo viewer or headset-style
enclosure to confirm the 3D effect is perceptually convincing to a human eye
— this project does not claim headset support, so that was not attempted.
Live WASD/mouse-equivalent input was not exercised interactively.

### AR Prototype — **Partially verified on real hardware; marker tracking confirmed synthetically**

This mode was tested in three separate ways in this session:

1. **Real webcam, real GL context, no marker present.** `ARSoccerExperience`
   opened the real camera at index 0 (resolution 640×480), pulled 30 live
   frames through the full pipeline (`cv2.cvtColor`, ArUco detection, texture
   upload, full-screen quad draw, HUD overlay), and rendered without error.
   The captured frame showed the live camera feed correctly composited as
   the 3D scene's background with the "Searching for marker…" HUD overlaid
   in the correct position — confirming the Phase 2 fix for audit finding
   B10 (previously the camera frame was never drawn at all). **That
   screenshot was deleted immediately after inspection and is not included
   in this repository**, because it captured a real person's face via the
   live webcam; it is not appropriate to retain or publish. The verification
   claim above is made on the basis of having inspected it, not on a
   retained file.
2. **Desktop fallback, real GL context.** With `ar_mode` forced off, the
   orbiting desktop view and its HUD rendered correctly —
   `docs/screenshots/ar_desktop_fallback.png`.
3. **Marker detection and pose recovery, end-to-end, with a synthetic frame.**
   A marker was rendered with `tools/make_markers.py`'s own drawing function
   onto a plain grey background (not a photo of anyone), fed into
   `ARSoccerExperience` in place of a camera frame, and run through the
   *actual* `estimate_pose` → `cv2.solvePnP` → `cv_pose_to_gl_modelview`
   pipeline. The marker was detected, a pose was recovered
   (`marker_visible = True`, `last_modelview is not None`), and the pitch
   rendered anchored to it — `docs/screenshots/ar_marker_tracking.png`. The
   viewing angle in that image is a close, steep synthetic placement chosen
   for a clean test, not a realistic tabletop framing.

**Not verified — and this matters:** no *printed, physical* marker has been
held in front of a camera by a person in normal lighting. The scale,
stability, and alignment quality of the overlay on an actual printed marker
at a real table distance is unverified. Camera intrinsics are an assumed 60°
field of view, not a calibration — see the module docstring and
`SOCCER_PROJECT_AUDIT.md` finding B11. **Keep this mode labelled
experimental** (it already is, in the module docstring, the console banner,
and the launcher's menu label) until someone has done that physical test.

### Launcher (`run_windows_version.py`) — **Verified**

`--list` prints all six modes; `--mode markers` was run to completion
(writes a marker PNG and exits 0). The interactive menu was driven with
scripted stdin for the exit path. Launching the 2D/3D/AR/VR modes as actual
*subprocesses* (as opposed to importing their classes directly, which is
what the rest of this report does) was not separately re-verified in this
phase — it was verified in Phase 2's audit and is unchanged since.

### Tk launcher (`modern_interface.py`) — **Unverified (import-only)**

Imports cleanly. The GUI itself (buttons, camera preview thread, settings
dialog) has not been opened in this session.

## 3. What this report does NOT claim

- No claim that AR tracking is accurate, stable, or usable with a real
  printed marker — see above.
- No claim about behaviour on a different OS, GPU vendor, or Python version
  than the one listed in §Environment.
- No claim that the inherited research pipeline (`soccer3d/`, `utils/`,
  `demo/`) runs on Windows, or at all — it was not touched, per the audit.
- No claim of full interactive playtesting with a human at the keyboard for
  any mode — see each mode's "Not verified" line above.
- No performance/frame-rate measurement under real GPU load with the full
  scene (frame counts above were correctness checks, not benchmarks).

## 4. Manual verification checklist (Windows)

Use this to verify what automation in this session did not cover. Record
the date, OS build, and GPU/webcam used alongside each result.

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -v
python -m ruff check .
```

- [ ] `python run_windows_version.py --mode 2d` — play a full match: move,
      kick, score at both ends, let the clock reach 0, confirm the winner
      screen, press R to restart.
- [ ] `python run_windows_version.py --mode 3d` — orbit with arrow keys,
      zoom with W/S, confirm the camera actually responds (not frozen).
- [ ] `python run_windows_version.py --mode vr` — press V to toggle stereo
      on/off exactly once per press (not repeatedly while held), walk with
      WASD, confirm both eyes show a sensible, undistorted picture.
- [ ] `python tools/make_markers.py --size-mm 100` then print
      `ar_markers/marker_0_100mm.png` at 100% scale (not "fit to page").
- [ ] `python run_windows_version.py --mode ar --camera 0` (or
      `python ar_soccer_experience.py --marker-mm 100`) — hold the printed
      marker flat in front of the camera in good light; confirm the pitch
      appears anchored to the marker, press A to toggle AR/desktop view, C
      to switch camera if more than one is available.
- [ ] Confirm the webcam light turns off when the AR window is closed.
- [ ] `python modern_interface.py` — click through each card, confirm the
      camera preview updates, confirm each "Start" button launches its mode.

## 5. A testing artefact worth recording

While capturing the GPU screenshots in §2, the first attempts at a capture
helper used `pygame.image.save()` directly on an OpenGL-mode display
surface, and separately called `glReadPixels` *after* `pygame.display.flip()`
without switching the read buffer. Both produced solid black images. Neither
was a bug in the application: `pygame.image.save` does not read an
OpenGL-rendered framebuffer at all, and `glReadPixels` defaults to
`GL_BACK`, which holds stale content immediately after a buffer swap. The
fix (read via `glReadPixels` before swapping, or explicit
`glReadBuffer(GL_FRONT)` after) is recorded here so the same false alarm
isn't rediscovered later. It is not part of the shipped application code.

## 6. Residual risk

The gap between "verified in this session" and "verified for you" is real:
different GPU vendors implement the OpenGL fixed-function pipeline with
known quirks (the mesh and lighting code here uses `glMaterialfv` and
positional lights, which have historically behaved differently across
Intel/NVIDIA/AMD drivers), and no printed-marker AR test has been done at
all. Treat §2's "Verified" labels as "verified on one Intel integrated GPU,
one webcam, one Windows build" rather than "verified everywhere."
