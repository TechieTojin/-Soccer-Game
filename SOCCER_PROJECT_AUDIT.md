# Soccer AR/VR Experience — Technical Audit

| | |
|---|---|
| **Repository** | https://github.com/TechieTojin/-Soccer-Game (audited from the local checkout, branch `main`, commit `52e0466`) |
| **Audit date** | 2026-10-12 |
| **Method** | Static reading of every top-level source file and the inherited-code headers, `ast.parse` of all 64 tracked `.py` files, grep-based cross-referencing, one read-only probe of the locally installed OpenCV, and one arithmetic check of the 2D physics constants. |
| **What was NOT done** | No project code was executed. No dependencies were installed. `pygame` and `PyOpenGL` are not installed on this machine, there was no webcam/GPU session, and the Soccer-on-Table pipeline was not run. **Nothing below is claimed to "work" unless stated as verified.** No project file was modified or committed; this report is the only file added. |

### Evidence labels used throughout

- **[Confirmed]** — directly visible in the code, or reproduced by a safe probe/arithmetic check.
- **[Derived]** — follows from the code by reasoning (e.g. OpenGL matrix math) but was not seen running. Needs a 1-minute visual check.
- **[Assumption]** — plausible but unverified; listed again in §11.

### Severity scale

**Critical** = feature advertised but cannot run / project is misrepresented · **High** = visible malfunction or licensing risk · **Medium** = wrong behaviour in a secondary path, or a maintainability blocker · **Low** = polish.

---

## 1. Executive Summary

**What the project really is.** Two bodies of code live in one repo:

1. **Inherited:** the *Soccer on Your Tabletop* research codebase (Rematas, Kemelmacher-Shlizerman, Curless, Seitz, CVPR 2018) — `soccer3d/`, `utils/`, `demo/`, `compile.sh`, plus the `barcelona.zip` sample data and a BSD-2 `LICENSE` carrying *their* copyright. About 6.3k of the ~9.1k Python lines.
2. **Original (inferred):** eight root-level scripts, ~2.8k lines (~31%): a pygame 2D game (`soccer_game.py`), simple PyOpenGL "AR" and "VR" scenes, a Tk launcher, two console launchers, a setup script and a basic 3D viewer.

**Headline findings**

| # | Finding | Severity |
|---|---|---|
| F1 | README says MIT; the `LICENSE` file is BSD-2-Clause with the *original authors'* copyright. README credits only the two of you and never names Soccer-on-Table. | **High** (licensing/credibility) |
| F2 | The documented entry point (`run_windows_version.py`) does **not** launch the 2D game, AR or VR. The 2D game (`soccer_game.py`) is referenced by no launcher. README controls and menu do not match the code. | **Critical** |
| F3 | `ar_soccer_experience.py` crashes at import on OpenCV ≥ 4.7 (`aruco.Dictionary_get` removed). Verified missing in the installed OpenCV 5.0.0. `setup_ar_vr.py` has the same defect. | **Critical** |
| F4 | `requirements.txt` omits `pygame` and `opencv-python`, which every original script needs, and instead lists the heavy research stack (`torch`, `openmesh`, `glumpy`, `visdom`). `pip install -r requirements.txt` will not produce a runnable game. | **Critical** |
| F5 | "AR" never draws the camera frame; "VR" is side-by-side stereo with no headset/tracking support. The 2D game's AR/3D/VR menu entries are placeholder message boxes. | **High** (claims vs. reality) |
| F6 | 2D game: drawn goal and goal detection are in different places; constant "gravity" drags the ball to the bottom edge of a top-down pitch; 22 players but only 9 selectable and only the selected one moves; stamina only drains on kicks. | **High** |
| F7 | Zero tests, zero CI, no package structure, ~300 lines duplicated between AR and VR, logic fused to rendering. | **Medium** |
| F8 | 41 MB `barcelona.zip` committed; `.gitignore` silently ignores `*.txt`, `*.png`, `*.json`, `*.html` (would swallow requirements files, screenshots, CI config). | **Medium** |

**Verdict.** As submitted, a reviewer following the README would hit a failure within a few minutes. None of this is deep: the 2D game is a reasonable base, and most defects are 1–10 line fixes. A **2–3 day** effort can turn it into an honest, tested, documented project. The most valuable move is to *narrow the claims to what is true* (a tested 2D match engine + OpenGL/ArUco prototypes built on top of an attributed research codebase) rather than add features.

**Recommended positioning for a Google application:** lead with the 2D game and the test/CI story; describe AR/VR as "prototypes", and describe Soccer-on-Table explicitly as upstream work you built on. Overstated claims are a bigger risk to credibility than a smaller scope.

---

## 2. Repository Map

91 tracked files; ~64 Python files / 9,115 lines. Origin column is **inferred** (see §7).

```
.
├── README.md                    original   — inaccurate in places (see §10)
├── LICENSE                      INHERITED  — BSD-2, © Rematas et al. 2018
├── requirements.txt             mixed      — research stack only, no pygame/opencv
├── .gitignore                   inherited  — ignores *.txt/*.png/*.json/*.html (!)
├── compile.sh                   INHERITED  — bash: builds nms (Cython) + instancesegm (CMake)
├── barcelona.zip                INHERITED  — 41 MB sample dataset (UW GRAIL), committed
│
├── soccer_game.py        (610)  original   — pygame 2D game + menu
├── ar_soccer_experience.py(563) original   — PyOpenGL + OpenCV ArUco "AR"
├── vr_soccer_experience.py(618) original   — PyOpenGL side-by-side stereo "VR"
├── soccer3d_viewer.py    (186)  original   — PyOpenGL static 3D field viewer
├── modern_interface.py   (316)  original   — Tk launcher + webcam preview
├── run_windows_version.py(127)  original   — console launcher (documented entry point)
├── run_soccer_on_table.py(111)  original   — matplotlib image viewer + "simulated" detection
├── setup_ar_vr.py        (265)  original   — pip/dataset/ArUco-marker/launcher setup
│
├── soccer3d/                    INHERITED  — pipeline: calibration, tracking, soccerdepth (PyTorch
│   │                                         hourglass), instancesegm (C++/OpenCV), core.py
├── utils/                       INHERITED  — camera/geometry/io/draw helpers
│   ├── nms/                     third-party — Fast R-CNN NMS (MIT) + pycocotools (BSD) + Cython/CUDA
│   └── thirdpartyscripts/       third-party — Facebook Detectron script (Apache-2.0)
└── demo/                        INHERITED  — pipeline scripts, hard-coded `/home/krematas/...` paths
```

**Entry points (who calls whom)**

| Entry point | Launches | Notes |
|---|---|---|
| `python run_windows_version.py` (README) | `run_soccer_on_table.py`, `soccer3d_viewer.py` | Menu has **only** these two + docs. No 2D game/AR/VR. |
| `python modern_interface.py` (created by `setup_ar_vr.py`) | `run_soccer_on_table.py` ("2D Viewer"), `soccer3d_viewer.py`, `ar_…py`, `vr_…py` | The only launcher that reaches AR/VR. |
| `python soccer_game.py` | — | **[Confirmed]** referenced by nothing except a README tree comment (`grep`). |
| `python setup_ar_vr.py` | — | Installs packages, downloads data, makes markers + launcher. |

---

## 3. Architecture

```
                      ┌──────────────────────────────────────────────┐
  Launchers           │ run_windows_version.py   modern_interface.py │   (subprocess.run per script)
                      └───────────┬──────────────────────┬───────────┘
                                  │                      │
        ┌─────────────┬───────────┴───┬──────────────────┴────┬──────────────┐
        ▼             ▼               ▼                       ▼              ▼
 run_soccer_on_   soccer3d_viewer  ar_soccer_experience  vr_soccer_experience  soccer_game
 table (matplotlib) (PyOpenGL)     (PyOpenGL+ArUco)       (PyOpenGL stereo)    (pygame, standalone)
        │              │               │                       │
        └── barcelona/ dataset (only checked for existence in 2 of them)

 soccer3d/ + utils/ + demo/  ← research pipeline; NOT imported by any original script (grep-verified)
```

Key architectural facts **[Confirmed]**:

- **Each mode is an isolated monolithic class/script.** No shared module, no shared state; "integration between modes" is only *launching a different subprocess*. A goal in the AR scene has no relationship to the 2D score.
- **Logic is fused with rendering.** `update_ball_physics`, scoring, and input handling sit in the same class as OpenGL/pygame draw calls (`ar_…:466`, `vr_…:524`, `soccer_game.py:315`). Physics cannot be unit-tested without a display.
- **AR and VR are copy-paste siblings.** `create_field_texture`, `draw_player`, `draw_ball`, `add_effect`, `draw_effects`, `update_ball_physics`, `reset_ball`, the formation table and constants are duplicated (~300 lines).
- **Physics is frame-count-driven in 3D** (`+= 0.016`, `-= 0.01` per frame) and partly `dt`-driven in 2D, with per-frame multipliers (`*= 0.99`) that are not `dt`-scaled in either.
- **The research pipeline is not wired in.** The viewer's player positions are hard-coded lists (`soccer3d_viewer.py:105`, `ar_…:69`); the dataset is only checked for existence.

---

## 4. Feature Verification Matrix

"Code evidence" = what the source shows. **Runtime-verified is "No" everywhere** — nothing was executed.

| Claimed feature (README) | Code evidence | Status |
|---|---|---|
| 2D: real-time player movement | Selected player moves with arrows (`soccer_game.py:276-299`); other 21 players are static | **Partial** — [Confirmed] |
| 2D: ball physics w/ gravity & air resistance | Present (`:315-364`), but gravity on a top-down pitch is physically meaningless and pulls ball to the bottom edge (see B5) | **Present, flawed** — [Confirmed] |
| 2D: player roles | 11 roles assigned and drawn (`:130-145`, `:476`); roles affect kick power only (`:248-251`) | **Cosmetic** |
| 2D: stamina system | Drains only on kick (−10, `:267`); regen when idle (+0.5/frame, `:303`); scales speed & kick power | **Partial** — moving does not drain stamina |
| 2D: score tracking & match timer | Score list + 90 s countdown + game-over overlay (`:78-79`, `:312`, `:542`) | **Present** — but goal geometry is inconsistent (B4) |
| 2D: player switching / "team management" | Tab toggles team, keys 1–9 pick player (`:230-235`) | **Partial** — players 10–11 unreachable (B7); no AI opponent |
| 2D: "Space: kick", "Tab: switch teams", "1-9" | Matches code | OK |
| README "Arrow keys: Move selected player" | Matches code | OK |
| **Menu: 2D / 3D Field / AR / VR** (README "Usage") | `run_windows_version.py` offers image viewer + 3D viewer only. `soccer_game.py` menu: 3D/AR/VR are `show_message` stubs (`:588-599`) | **Not as documented** |
| 3D field visualisation | `soccer3d_viewer.py`: textured-less quad, lines, hard-coded players; likely orientation issues (B12) | **Prototype**, [Derived] issues |
| AR: camera-based field tracking | ArUco ID 0 → `solvePnP` → modelview (`ar_…:217-278`), approximate intrinsics | **Prototype**; crashes on OpenCV ≥ 4.7 (B1); no calibration |
| AR: "camera feed" / overlay on table | Frame is used only for marker detection; **never rendered** (`ar_…:549-552`) | **Not implemented** — [Confirmed] |
| AR: interactive ball physics | Random-direction kick (`:520-526`); ball ignores players | **Minimal** |
| AR/VR: "player animations and formations" | Sine-wave limb swing and static 4-3-3 table; players off-pitch (B9) | **Cosmetic** |
| AR: goal celebrations | Particle spheres after goal (`:403-432`) | **Present** — [Derived]; unseen |
| VR: immersive / first-person | Side-by-side stereo, keyboard locomotion (`vr_…:574-583`) | **Stereo demo only**; no HMD/OpenXR/head tracking |
| VR: "interactive ball control" | Hold Space within 5 m to kick toward ball (`:478-489`) | **Minimal** |
| VR: "dynamic lighting and shadows" | 2 fixed lights; **no shadows** anywhere | **Overstated** |
| "Barcelona dataset automatically downloaded when running the game" | Only `setup_ar_vr.py` downloads it, over plain HTTP; nothing in the game does | **False as written** |
| "Windows 10+, Python 3.7+" | `setup_ar_vr.py` requires 3.8+ (`:20`); 3.7 is EOL | **Inconsistent** |
| 3D reconstruction from video (the research pipeline) | Inherited; hard-coded Linux paths, requires Detectron/OpenPose/CUDA | **Not usable on Windows as shipped** [Assumption on CUDA] |

---

## 5. Bugs and Risks

Format: **ID · Severity · File:line · Evidence · Fix · Effort.** Line numbers refer to the checkout audited.

### 5.1 Launch / packaging

**B1 · Critical · [ar_soccer_experience.py:19-20](ar_soccer_experience.py#L19-L20), [setup_ar_vr.py:114,120](setup_ar_vr.py#L114)** — AR crashes at import.
*Evidence [Confirmed]:* module-level `aruco.Dictionary_get(...)` / `DetectorParameters_create()`; `drawMarker` in setup. Probe of installed OpenCV 5.0.0: `Dictionary_get False, DetectorParameters_create False, drawMarker False; getPredefinedDictionary / ArucoDetector / generateImageMarker True`. These were removed from the Python API in OpenCV 4.7 (assumption on exact version boundary; the 5.0 probe is verified). Because it runs at import time, the launcher's "Start" button just reports "Error running…".
*Fix:* `aruco.getPredefinedDictionary(DICT_4X4_50)`, `aruco.ArucoDetector(dict, aruco.DetectorParameters())` + `detector.detectMarkers(gray)`, `aruco.generateImageMarker(dict, id, px)`. Move construction into `__init__`, not import time. Pin `opencv-contrib-python>=4.8`. *Effort: 1 h.*

**B2 · Critical · [requirements.txt](requirements.txt)** — wrong dependency set.
*Evidence [Confirmed]:* lists `numpy scipy matplotlib cython glog pyyaml shapely tqdm glog torch torchvision visdom openmesh glumpy pyopengl` (`glog` duplicated, nothing pinned). Missing: `pygame`, `opencv-python`/`-contrib`, `pillow`. Every original script imports at least one of those. Meanwhile `torch`, `openmesh`, `glumpy`, `visdom` are needed only by the inherited pipeline.
*Fix:* split into `requirements.txt` (runtime for original code: `pygame`, `numpy`, `PyOpenGL`, `opencv-contrib-python`, `Pillow`, `matplotlib`), `requirements-dev.txt` (pytest, ruff), and `requirements-pipeline.txt` (inherited research deps, clearly marked optional). Pin with compatible ranges. Beware `.gitignore` `*.txt` (B14). *Effort: 1 h.*

**B3 · Critical · [run_windows_version.py:46-53,107-112](run_windows_version.py#L46-L53)** — documented launcher omits the game.
*Evidence [Confirmed]:* options are "Image Viewer", "3D Field", "Documentation", "Exit". README tells users to "select 2D / 3D / AR / VR". `show_documentation` opens `README_WINDOWS.md` ([:73](run_windows_version.py#L73)) which does not exist in the repo. `soccer_game.py` is unreachable from any launcher; `modern_interface.py`'s "2D Viewer" card starts `run_soccer_on_table.py` (the matplotlib image viewer, [:242](modern_interface.py#L242)).
*Fix:* one launcher (`python -m soccer_ar_vr` or `python main.py --mode 2d|3d|ar|vr`), delete or fix the other; point "2D" at the game; remove the dead docs option. *Effort: 2 h.*

**B4 · High · [soccer_game.py:371-386 vs 459-464](soccer_game.py#L371-L386)** — goal geometry mismatch.
*Evidence [Confirmed]:* goals are *drawn* at x = 80-100 (left) and `width-100` (right), i.e. on the pitch outline. Detection requires `ball_x < 20` / `> width-20`. The ball can only get there by crossing the drawn goal and the out-of-bounds margin, and walls bounce it at `x = ball_radius` (8). Also the pitch outline is `(100,100)…(width-100,height-100)` while the ball is allowed to roam the entire 1280×720 window (walls at the window edge, [:329-335](soccer_game.py#L329-L335)); players are clamped to the window too ([:298-299](soccer_game.py#L298-L299)). The ball never goes "out" (no throw-ins/corners).
*Fix:* define one `Pitch` rect and one `Goal` rect; use them for drawing, wall collision and scoring. Count a goal when the ball centre enters the goal rect. *Effort: 2 h.*

**B5 · High · [soccer_game.py:318, 320-321](soccer_game.py#L318)** — "gravity" in a top-down view.
*Evidence [Confirmed + arithmetic]:* `ball_vel[1] += 0.2` every frame, then `*= 0.99`. Iterating that recurrence reaches ≈17 px/frame after 200 frames and converges to ≈19.8 px/frame — a resting ball is dragged to the bottom edge within a second or two and is also biased downward on every pass. `self.friction = 0.95` is declared ([:122](soccer_game.py#L122)) but **never used**. Damping is per-frame, not `dt`-scaled, so physics speed depends on frame rate.
*Fix:* remove gravity for the 2D mode (or model height as a separate z), apply rolling friction `v *= friction ** (dt*60)`. *Effort: 1 h.*

**B6 · Medium · [soccer_game.py:337-364](soccer_game.py#L337-L364)** — collision code.
*Evidence [Confirmed]:* (a) `normal_x = dx / dist` raises `ZeroDivisionError` if ball centre == player centre (rare but fatal; whole game loop dies). (b) Impulse is applied without checking the bodies are approaching (`rel·n < 0`), so a separating ball can be pulled back. (c) With masses 1/1 the formula reduces to removing the normal component (perfectly inelastic) — no restitution parameter, inconsistent with the 0.8 wall bounce. (d) Players don't collide with each other.
*Fix:* guard `dist < 1e-6`; only respond if `rel·n < 0`; add restitution; unit-test it. *Effort: 1.5 h.*

**B7 · Medium · [soccer_game.py:232-235](soccer_game.py#L232-L235)** — player selection.
*Evidence [Confirmed]:* `K_1..K_9` can only produce indices 0-8; the `< 11` check is dead. Indices 9 and 10 (both strikers) are unreachable by keyboard. Only the selected player has movement code; the other 21 are static obstacles, so "match" is a one-player sandbox. Tab flips team but keeps the same `selected_player` index.
*Fix:* add `[`/`]` or Q/E to cycle, or auto-select nearest-to-ball; add trivial AI (move towards ball / return to formation) for non-selected players. *Effort: 3-4 h for cycle + basic AI.*

**B8 · Medium · [soccer_game.py:288-303](soccer_game.py#L288-L303)** — stamina model.
*Evidence [Confirmed]:* moving never reduces stamina; only kicks do (−10). Regen (+0.5) is per frame and happens only if no direction key is held. At stamina 0 speed and kick power are 0 ([:289,255](soccer_game.py#L289)), so a player holding a key cannot move *or* recover — a soft-lock until the key is released. README's "stamina affecting player performance" is thus only true for kicks.
*Fix:* drain proportional to speed·dt, regen·dt, floor speed multiplier at ~0.3. *Effort: 1 h.*

**B9 · Medium · [ar_…:81,94](ar_soccer_experience.py#L81) / [vr_…:61,74](vr_soccer_experience.py#L61)** — players placed outside the pitch.
*Evidence [Confirmed]:* goalkeepers at x = ±60 while the pitch half-length is `FIELD_WIDTH/2 = 52.5`. Defenders at ±50 stand on the goal line. Naming is also swapped: `FIELD_WIDTH = 105`, `FIELD_LENGTH = 68` (the long axis is called "width").
*Fix:* GK at ±50, defenders ±38, rename to `PITCH_LENGTH_X`/`PITCH_WIDTH_Z`. *Effort: 30 min.*

**B10 · High · [ar_soccer_experience.py:434-442, 549-552](ar_soccer_experience.py#L434)** — AR is not visually AR.
*Evidence [Confirmed]:* the camera `frame` goes only into `detect_markers`; no `glTexImage2D`/blit of the video; `glClear` + 3D scene on a black background. If `cap.read()` fails (`ret` False) *nothing* is rendered or ticked that frame ([:549-552](ar_soccer_experience.py#L549-L552)).
*Fix:* upload frame as a texture and draw a fullscreen quad (orthographic, depth test off) before the 3D pass; render the previous pose when detection fails. *Effort: 3-4 h.*

**B11 · High · [ar_soccer_experience.py:237-278, 439](ar_soccer_experience.py#L237-L278)** — pose-to-OpenGL conversion.
*Evidence [Derived]:* (a) `glLoadMatrixf(transform.T)` with an OpenCV pose and **no** Y/Z axis flip (`diag(1,-1,-1)`) normally yields a mirrored/upside-down scene. (b) Marker size is 10 units, but the field is 105×68 units, so the pitch is ~10× the marker and fills/exceeds the view; scale should map the table-top pitch to the printed marker. (c) Projection is a fixed `gluPerspective(45, …)` ([:54](ar_soccer_experience.py#L54)) while `solvePnP` assumes `fx = width` — the two are inconsistent. (d) Marker model points lie in the XZ-plane while the field is drawn in XZ with Y up; verify handedness. (e) `solvePnP` return value is ignored.
*Fix:* flip axes, derive projection from the camera matrix, scale pitch by `marker_len_m / pitch_len`, check `ok`. *Effort: 3-4 h (needs a webcam to validate).*

**B12 · Medium · [ar_…:515-541](ar_soccer_experience.py#L515-L541)** — view controls do nothing.
*Evidence [Derived]:* arrows/+/- call `glRotatef`/`glScalef` inside `handle_events`, but `render_scene` begins with `glLoadMatrixf(...)`/`glLoadIdentity()+gluLookAt` every frame ([:438-442](ar_soccer_experience.py#L438-L442)), discarding the accumulated matrix. The README advertises these keys. *Fix:* keep `yaw/pitch/zoom` state and apply in the view matrix. *Effort: 30 min.*

**B13 · Medium · [vr_soccer_experience.py:412](vr_soccer_experience.py#L412)** — stereo viewport aspect wrong.
*Evidence [Confirmed]:* `aspect = width / (height/2)` = 3.56 for 1920×1080. Each eye viewport is `width/2 × height` → aspect 0.89. Result: horizontally squashed image in both eyes. In addition: eye offset is along world X, not the camera's right vector ([:422-426](vr_soccer_experience.py#L422-L426)), so after turning, the "stereo" separation lies along the view direction and the 3D effect breaks [Derived]. `K_v` is polled with `get_pressed()` ([:468](vr_soccer_experience.py#L468)), so holding V flips VR mode every frame (use `KEYDOWN`). Pitch has no clamp and `look_dir` is never re-normalised, so repeated rotation drifts ([:491-513](vr_soccer_experience.py#L491-L513)).
*Fix:* `aspect = (w/2)/h` for split-screen; `right = normalize(cross(look, up))`; edge-triggered toggle; yaw/pitch angles instead of vector rotation. *Effort: 1.5 h.*

**B14 · Medium · [vr_…:222-238](vr_soccer_experience.py#L222-L238)** — goalposts likely underground/misoriented.
*Evidence [Derived from rotation math]:* `glRotatef(90,1,0,0)` maps the cylinder axis +Z to −Y, so posts of height 2.44 extend *below* the ground; the crossbar uses `glRotatef(90,0,1,0)` → along +X while it should span Z. Same pattern for legs in `draw_player` (`:325-337`, legs hang to y = −0.3). Not seen rendered — verify visually; fix with `glRotatef(-90,1,0,0)`. *Effort: 30 min.*

**B15 · Medium · [vr_…:143-147](vr_soccer_experience.py#L143-L147)** — start-up cost.
*Evidence [Confirmed]:* centre circle drawn with a Python double loop over 1024×1024 = 1,048,576 pixels with `np.sqrt` each. Expect multi-second start-up (not timed). Texture is square but stretched over 105×68 m, so the "circle" renders as an ellipse. *Fix:* vectorise with `np.ogrid` or `cv2.circle`; make texture aspect 105:68. *Effort: 30 min.*

**B16 · Medium · [soccer3d_viewer.py:77-84, 100-102, 61-66](soccer3d_viewer.py#L77)** — viewer.
*Evidence:* [Confirmed] it **exits if the dataset is missing** though it never reads it (positions are hard-coded, [:105](soccer3d_viewer.py#L105)); the `gluLookAt` at `:100` is overwritten by `glLoadIdentity()` at `:161` (comment is misleading). [Derived] players are cylinders drawn along +Z with no rotation, so they lie on their sides; the camera starts at the origin in the pitch plane, so the first view is edge-on. *Fix:* drop the dataset check; look from (0, 60, 60); rotate −90° about X. *Effort: 1 h.*

**B17 · High · [modern_interface.py:301](modern_interface.py#L301)** — `messagebox.warning` doesn't exist (the function is `showwarning`). **[Confirmed]** → `AttributeError` at start-up whenever the dataset is missing — which is the default state after a fresh clone with the zip unextracted. *Effort: 5 min.*

**B18 · Medium · [modern_interface.py:217-237, 259-268](modern_interface.py#L217)** — launcher robustness.
*Evidence:* camera opened and read in a daemon thread that calls Tk widgets directly (`create_image`, `status_var.set`, `self.after(30)` with no callback — in Tk this blocks the calling thread; none of this is thread-safe) [Confirmed pattern, behaviour Assumption]. If no camera: `cap.read()` returns `(False, None)` forever, so the thread spins at 33 Hz. Preview holds the camera, so the AR subprocess likely can't open the same device on Windows [Assumption]. Scripts are launched by bare relative name, so the launcher only works when CWD is the repo root. "Camera" dropdown, "AR Mode" checkbox and Settings window are non-functional stubs ([:177-185, 270-278](modern_interface.py#L177)). *Fix:* use `after()` polling on the main thread, release camera before launching AR, use `Path(__file__).parent`. *Effort: 2 h.*

**B19 · Medium · [setup_ar_vr.py:31-45,69,82](setup_ar_vr.py#L31)** — setup script.
*Evidence [Confirmed]:* installs both `opencv-python` **and** `opencv-contrib-python` (they overwrite each other's `cv2`); `pip install tk` on Windows (tkinter ships with CPython; the PyPI package is unrelated) and `python-tk` elsewhere (not a PyPI name) → the script returns failure; dataset is fetched over plain `http://` with no checksum; packages unpinned; `os.remove("barcelona.zip")` would delete the tracked zip if the download path ever runs on a checkout that has it. *Fix:* drop this script in favour of `pip install -r requirements.txt`; keep only the marker generator as `tools/make_markers.py`. *Effort: 1 h.*

**B20 · Low-Med · [soccer_game.py:56-65, 184, 198-214](soccer_game.py#L56)** — game shell.
*Evidence [Confirmed]:* camera opened at start-up for a mode that is a stub (slow on Windows, lights the webcam LED) with a bare `except:`; menu clicks use `mouse.get_pressed()` every frame instead of `MOUSEBUTTONDOWN`; `show_message` runs a nested blocking loop (also used for goal banners, freezing the sim); startup banner prints WASD/V/A controls that don't exist in this game ([:67-74](soccer_game.py#L67-L74)); `from OpenGL.GL import *` is imported but unused (needless dependency); 36 px role labels drawn inside 15 px radius circles overflow; ball "shadow" uses RGBA on a non-alpha surface (alpha ignored); `FULLSCREEN | RESIZABLE` at hard-coded 1920×1080 in AR/VR ([:28-31](ar_soccer_experience.py#L28-L31)) is fragile on laptops/high-DPI.

**B21 · Medium · [utils/nms/pycocotools/coco.py:77+](utils/nms/pycocotools/coco.py#L77)** — Python 2 code. **[Confirmed]** `ast.parse` fails (`print '...'`) — the only one of 64 files that does. Any tool that byte-compiles the repo (pytest collection with `--doctest-modules`, mypy, `compileall`, some CI linters) fails on it. `compile.sh` is Bash-only; `cpu_nms.pyx` uses `np.float` which was removed from NumPy ≥ 1.24 (the Python-level alias; Cython-level behaviour [Assumption]). *Fix:* exclude `utils/nms`, `soccer3d`, `demo` from lint/test config, or `pip install pycocotools`. *Effort: 30 min.*

**B22 · Medium · [demo/*.py](demo/estimate_poses.py)** — inherited scripts default to `/home/krematas/...` paths; `soccer3d/core.py` imports `pycocotools`, `glog`, compiled `nms`, Detectron/OpenPose outputs, etc. **[Confirmed]** hard-coded Linux defaults; whether the pipeline works on Windows is **[Assumption: no]** and out of scope for a "moderate improvement".

**B23 · Medium · repo hygiene** — `barcelona.zip` (41 MB) is committed. `.gitignore` ([.gitignore](.gitignore)) ignores `*.txt`, `*.png`, `*.json`, `*.html`, `*.jpg`, `*.pdf`: new `requirements-dev.txt`, `docs/screenshot.png`, JSON configs would be **silently ignored** by `git add`. Local clone shows a single commit, so history cannot show who wrote what. *Fix:* add `!requirements*.txt` and `!docs/**` exceptions; move data to a GitHub Release or download script. *Effort: 30 min.*

### 5.2 Code quality, performance, testability (cross-cutting)

| Area | Observation | Evidence |
|---|---|---|
| Modularity | 600-line god-classes; AR ≈ VR duplicated ~300 lines | §3 |
| Error handling | Bare `except:` (`soccer_game.py:63`), failing camera reads unhandled, `print` instead of `logging`, `sys.exit()` inside constructors/viewer | `soccer_game.py:63`, `run_soccer_on_table.py:144` |
| Performance | New `gluNewQuadric()` per body part per frame (≈7 × 22 players + ball, never `gluDeleteQuadric`) → allocation churn/leak; immediate-mode OpenGL; 22 font renders/frame in 2D | `ar_…:328-364`, `vr_…:300-337`, `soccer_game.py:476` |
| Timing | Fixed `0.016` increments & per-frame constants instead of real `dt` | `ar_…:458-459`, `vr_…:591-592`, `:469,473` |
| Testability | Physics/state live in classes that call `pygame.init()` and `set_mode()` in `__init__` | `soccer_game.py:20-25` |
| Types/docs | No type hints, no module docstrings except a stray string after imports in `soccer_game.py:13-17` | — |
| Security | `zipfile.extractall` on a downloaded zip (CPython sanitises `..`, but no checksum, HTTP); `subprocess.run([sys.executable, script])` with fixed names is fine | `setup_ar_vr.py:78-86` |

---

## 6. Dependency Compatibility

Local environment seen: Windows 11, **Python 3.10.0**, `numpy 2.2.6`, `opencv-python-headless 5.0.0.93`; `pygame` and `PyOpenGL` **not installed**; I did not install anything.

| Dependency | Used by | Declared? | Risk |
|---|---|---|---|
| `pygame` | `soccer_game`, AR, VR, viewer | **No** (`requirements.txt`) | Add; `pygame>=2.5` / `pygame-ce`. Python 3.12/3.13 wheel availability [Assumption: fine on 2.6+]. |
| `PyOpenGL` | `soccer_game` (unused import), AR, VR, viewer | `pyopengl` yes | Needs a GL 2.1-compat driver; legacy fixed-function API (`glBegin`, `glLightfv`) — fine on desktop drivers, not on macOS core profile. `glGenerateMipmap` requires GL ≥ 3.0 on some drivers [Assumption]. |
| `opencv-python[-contrib]` | `soccer_game` (camera), AR, VR (texture), Tk launcher | **No** | `cv2.aruco` **API break** (B1). Choose **one** of `opencv-python`/`-contrib` (headless has no `imshow`; irrelevant here but conflicts with GUI builds). |
| `Pillow`, `matplotlib`, `numpy`, `scipy` | viewers / launcher | numpy, scipy, matplotlib yes; Pillow transitive | `numpy 2.x` OK for original code (only `np.sign`, arrays). `scipy` isn't imported by any original script. |
| `tkinter` | `modern_interface` | stdlib | Don't `pip install tk` (B19). |
| `torch`, `torchvision`, `visdom`, `openmesh`, `glumpy`, `glog`, `shapely`, `cython`, `pyyaml`, `tqdm` | inherited pipeline only | yes | Heavy / often awkward on Windows; `glumpy` and `visdom` are unmaintained-looking [Assumption]; `glog` listed twice. Move to an optional extra. |
| Detectron (caffe2), OpenPose, CMake/OpenCV C++ | inherited pipeline | **No** | Not pip-installable; `infer_subimages.py` imports `caffe2`/`detectron` directly. |
| Python version | all | README says 3.7+, setup says 3.8+ | 3.7 and 3.8 are EOL. Recommend **3.10–3.12**, test 3.10 and 3.12. |
| Platform | | Windows 10+ | `compile.sh` is Bash; `os.system('cls')`; `/home/krematas` paths. Original scripts are plausibly Windows-OK (not executed). |

---

## 7. Code Ownership and Licensing

### 7.1 Original vs. inherited (best inference — confirm with your own git history)

| Group | Files | Lines (Py) | Basis |
|---|---|---|---|
| **Likely original** | `soccer_game.py`, `ar_…`, `vr_…`, `soccer3d_viewer.py`, `modern_interface.py`, `run_windows_version.py`, `run_soccer_on_table.py`, `setup_ar_vr.py` | ≈ 2,800 (~31%) | Windows-focused, no upstream headers, "Developed by Tojin Varkey Simson and Jaiby Mariya Jospeh" banner, entirely different style/dependency set from upstream. |
| **Inherited (Soccer-on-Table)** | `soccer3d/**`, `utils/*.py`, `demo/**`, `compile.sh`, `soccer3d/instancesegm/**`, `barcelona.zip`, `demo/data/field.png`, `LICENSE` | ≈ 4,500 | Upstream paths (`/home/krematas/…`), `YoutubeVideo` class, BSD-2 LICENSE naming the upstream authors. |
| **Third-party inside inherited** | `utils/nms/nms/*` (Fast R-CNN, © Microsoft, MIT per headers); `utils/nms/pycocotools/*` (COCO API, pinned via `UPSTREAM_REV`; BSD); `utils/thirdpartyscripts/infer_subimages.py` (Facebook Detectron, **Apache-2.0** header); `soccer3d/soccerdepth/models/hourglass.py` ("(c) YANG, Wei" — stacked hourglass; upstream license **[Assumption: MIT, verify]**); `soccer3d/instancesegm/model.yml.gz` (looks like an OpenCV structured-edge model; **license unknown — verify**) | ≈ 1,000+ | File headers / provenance |

The git history in this checkout has a single commit, so *authorship cannot be proven from git*. If you have an earlier private history, keep it — it's your strongest evidence of what you wrote.

### 7.2 Licensing findings

| ID | Severity | Finding | Action |
|---|---|---|---|
| L1 | **High** | **README says "MIT License"** ([README.md](README.md), License section) but `LICENSE` is **BSD 2-Clause, © 2018 Rematas, Kemelmacher-Shlizerman, Curless, Seitz**. The repo is therefore not accurately licensed, and the only copyright holders named in the licence are the upstream authors. | Decide deliberately. Simplest/safest: keep BSD-2-Clause for the whole repo, add `Copyright (c) 2026 <your names>` *below* the upstream line, fix the README. (Alternative: separate licences per directory.) *Not legal advice.* |
| L2 | **High** | **No attribution to upstream in README.** Acknowledgements thank "Barcelona dataset", OpenCV and Pygame communities but never name the *Soccer on Your Tabletop* paper/authors/repo, even though a third of the repo and the data are theirs. For a job application this reads as presenting inherited work as your own. | Add an "Acknowledgements & Provenance" section with the paper citation and link (CVPR 2018, http://grail.cs.washington.edu/projects/soccer/ — `run_soccer_on_table.py:228` already uses this URL), plus a table of what is yours vs upstream. |
| L3 | Medium | BSD-2 requires retaining the copyright notice, conditions and disclaimer for source *and* binary redistribution. Currently satisfied for upstream code only through the one `LICENSE` file. | Keep it verbatim. |
| L4 | Medium | Third-party files carry their own licences (MIT, BSD, Apache-2.0). The Apache-2.0 header requires keeping the licence notice and stating changes. No `NOTICE`/third-party file exists. | Add `THIRD_PARTY_NOTICES.md` listing each component, source URL, licence, and include licence texts. Do **not** strip the in-file headers. |
| L5 | Medium | **`barcelona.zip` redistribution:** 41 MB of YouTube-derived match frames + annotations. Terms [Assumption: distributed by UW GRAIL for research; not stated in repo]. Committing it re-hosts it. | Verify terms on the upstream project page; prefer linking to the official download and removing the blob from the repo (use a Release or `git filter-repo` if you want it out of history). |
| L6 | Low | `model.yml.gz`, `field.png` provenance unstated. | Identify source/licence; document. |
| L7 | Low | Barcelona/FC Barcelona names, player likenesses in dataset frames. | Don't use screenshots from the dataset as project marketing without checking; use your own 2D/AR captures. |

---

## 8. Prioritised Upgrade Plan

Principle: **make claims true, then prove them.** No rewrite, no new features beyond what is needed to make existing ones work.

### P0 — Reliability and honesty (≈ 1 day)

| # | Task | Fixes | Effort |
|---|---|---|---|
| 1 | Fix `requirements.txt` (split runtime / dev / pipeline), pin ranges | B2, B19 | 1 h |
| 2 | Fix ArUco API (`ArucoDetector`, `generateImageMarker`), construct in `__init__` | B1 | 1 h |
| 3 | One launcher that actually starts 2D/3D/AR/VR; remove dead docs option; fix `messagebox.showwarning`; use `Path(__file__)` | B3, B17, B18 | 2-3 h |
| 4 | Correct README and LICENSE statement + provenance + `THIRD_PARTY_NOTICES.md` | L1-L4 | 1.5 h |
| 5 | 2D game correctness: single pitch/goal geometry, drop gravity, `dt`-scaled damping, div-zero guard, stamina drain, selection keys | B4-B8 | 3-4 h |
| 6 | Quick 3D fixes: swap `FIELD_*` names, GK/defender positions, stereo aspect + right-vector, V toggle on KEYDOWN, post/leg rotations, view-control state | B9, B12-B14 | 2 h |

### P1 — Maintainability and tests (≈ 1 day)

| # | Task | Effort |
|---|---|---|
| 7 | Extract pure logic into a `soccer_ar_vr/` package: `physics.py` (ball step, wall/player collision, friction), `match.py` (score, clock, goal rule, reset), `stamina.py`, `formations.py`, `pitch.py` (constants). `soccer_game.py` becomes a thin pygame view/controller | 4 h |
| 8 | Share AR/VR common code (texture, player/ball drawing, ball physics reuse of `physics.py`) in `render3d.py`; delete duplicates | 2 h |
| 9 | Tests (§9), ruff config, `pytest.ini`, GitHub Actions | 3 h |
| 10 | Remove `barcelona.zip` from the tree (keep a download helper with SHA-256), fix `.gitignore` exceptions | 30 min |

### P2 — UI polish (≈ 0.5-1 day, optional)

| # | Task | Effort |
|---|---|---|
| 11 | 2D: pitch margin/out-of-bounds, smaller role labels (letters only), stamina bars, "GOAL!" banner as non-blocking overlay, pause (P), restart (R), MOUSEBUTTONDOWN menu with hover + keyboard navigation | 3 h |
| 12 | AR: render camera feed as background, on-screen status ("marker found / searching"), fall back to a desktop camera if no webcam | 3-4 h (B10, B11; needs webcam) |
| 13 | Capture screenshots/GIF of 2D game, 3D viewer, AR with marker for README (own captures) | 1 h |

---

## 9. Testing Plan

### 9.1 What can be tested without a display/GPU/webcam

After step 7 (extract pure logic), these are straightforward `pytest` unit tests:

| Test | Asserts |
|---|---|
| `test_ball_wall_bounce` | Ball at wall reverses and loses 20% velocity; never ends outside the pitch |
| `test_ball_stops_with_friction` | After N steps with no input, speed → 0 and position stays in bounds (would have caught B5) |
| `test_no_drift_without_gravity` | Stationary ball stays put for 5 s of sim time |
| `test_player_ball_collision_zero_distance` | No exception when centres coincide (B6) |
| `test_collision_only_when_approaching` | Separating ball isn't pulled back |
| `test_goal_detection_matches_drawn_goal` | Ball centre inside goal rect ⇒ +1 for the right team; just outside ⇒ 0 (B4) |
| `test_score_and_reset_after_goal` | Ball to centre, players to formation |
| `test_match_clock` | Clock decrements by `dt`, stops at 0, winner/draw text correct |
| `test_stamina_drain_and_recovery` | Moving drains, idle recovers, floor speed > 0 (B8) |
| `test_kick_requires_proximity_and_scales_with_stamina` | Far player can't kick; low-stamina kick weaker |
| `test_select_player_all_eleven` | Every index 0-10 is selectable |
| `test_formation_inside_pitch` | All AR/VR formation coordinates within `±PITCH_HALF_LENGTH/±PITCH_HALF_WIDTH` (B9) |
| `test_pose_conversion` (AR) | Given synthetic marker corners generated by projecting a known pose, `solvePnP` pipeline recovers it within tolerance (no webcam needed) |
| `test_aruco_marker_roundtrip` | `generateImageMarker` → `ArucoDetector` finds ID 0 (guards B1) |
| `test_stereo_eye_offset` | Eye offsets are perpendicular to look direction and symmetric (B13) |
| `test_requirements_importable` | Smoke import of every module in the package |

### 9.2 Headless smoke tests (optional)

pygame can run without a window: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`. Run `SoccerGame` for ~120 simulated frames with scripted key states and assert no exception and sane state. OpenGL tests need a context — leave them as manual verification (§9.4) rather than flaky CI.

### 9.3 CI — suggested `.github/workflows/ci.yml`

Note: because of `.gitignore` `*.txt`, whitelist requirements files first (B23).

```yaml
name: CI
on:
  push: { branches: [main] }
  pull_request:

jobs:
  test:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
        python: ["3.10", "3.12"]
    runs-on: ${{ matrix.os }}
    env:
      SDL_VIDEODRIVER: dummy
      SDL_AUDIODRIVER: dummy
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
          cache: pip
      - run: python -m pip install -U pip
      - run: python -m pip install -r requirements.txt -r requirements-dev.txt
      - name: Lint
        run: ruff check soccer_ar_vr tests
      - name: Unit tests
        run: pytest -q --maxfail=1 --cov=soccer_ar_vr --cov-report=term-missing
```

Scope CI to the original package only; **exclude** `soccer3d/`, `utils/`, `demo/` (Python 2 `coco.py`, CUDA/Detectron dependencies). Add `[tool.ruff] extend-exclude = ["soccer3d", "utils", "demo"]`.

### 9.4 Verification commands (run locally before claiming anything works)

```powershell
# 0. clean venv
py -3.12 -m venv .venv ; .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt

# 1. static
ruff check .
python -m compileall -q soccer_ar_vr          # no Python-2 syntax in the package

# 2. automated
pytest -q

# 3. headless game smoke
$env:SDL_VIDEODRIVER="dummy"; python -c "from soccer_ar_vr.game import smoke; smoke(frames=300)"

# 4. API break guard
python -c "import cv2, cv2.aruco as a; print(cv2.__version__, hasattr(a,'ArucoDetector'))"

# 5. manual matrix (record result + screenshot for each)
python main.py --mode 2d     # move, kick, score, timer to 0, game over, ESC
python main.py --mode 3d     # field visible from above, players upright
python main.py --mode vr     # both eyes undistorted, V toggles once per press
python main.py --mode ar     # with printed ArUco ID 0: video visible, pitch locked on marker
```

Keep a `docs/VERIFICATION.md` table (feature · date · OS/GPU/webcam · pass/fail). That is the strongest antidote to "do not claim features work unless verified."

---

## 10. README Recommendations

Current problems **[Confirmed]:** says MIT while LICENSE is BSD-2; never mentions Soccer-on-Table; claims auto-download of the dataset; menu/controls don't match the launcher; "dynamic lighting and shadows", "realistic player models", "immersive VR" are overstated; says `pip install -r requirements.txt` is sufficient; references `README_WINDOWS.md` indirectly; project-tree block lists `soccerontable/` and a `barcelona/` folder that doesn't exist; Python 3.7+.

### Proposed structure

1. **Title + one-line description + badges** (CI status, Python versions, license).
2. **Demo** — GIF of the 2D match, screenshot of the 3D viewer, a photo/GIF of AR on a printed marker (own captures; store under `docs/` and whitelist in `.gitignore`).
3. **What this is — and what it isn't.** Three honest bullets: playable 2D match (original); OpenGL 3D viewer, ArUco AR prototype, side-by-side-stereo "VR" prototype (original; keyboard-driven, no headset); built beside the *Soccer on Your Tabletop* research code (not required to play).
4. **Status table** — Feature · Status (Stable / Prototype / Not implemented) · Verified on (OS, date). Copy from §4 after fixes.
5. **Quick start** — Python version, `venv`, `pip install -r requirements.txt`, `python main.py`. Windows (PowerShell) first.
6. **Controls** — one table per mode, auto-checked against the code.
7. **AR setup** — generate/print marker (`python tools/make_markers.py`), size, lighting, camera index, troubleshooting (camera busy, no marker found).
8. **Architecture** — the small diagram from §3 after refactor; where physics, rendering and input live; how to run tests.
9. **Development** — `pytest`, `ruff`, CI, project layout.
10. **Project structure** — accurate tree.
11. **Provenance & Acknowledgements** — upstream paper (authors, CVPR 2018, project URL), which directories are inherited, third-party components (nms, pycocotools, Detectron script, hourglass), dataset source and terms, and what *you* built. Link `THIRD_PARTY_NOTICES.md`.
12. **License** — consistent with the `LICENSE` file.
13. **Roadmap / known limitations** — honest list (no HMD, AR calibration approximate, no AI opponents beyond basic).
14. **Authors** — names; avoid personal contact details in a public README unless intended.

Tip for recruiters: put the "Provenance" short form **near the top** ("Built on top of the open-source *Soccer on Your Tabletop* research code; the 2D game, AR/VR prototypes and launchers are original"). It builds trust, and your original contribution reads as clearer, not smaller.

---

## 11. Questions Requiring Verification

| # | Question | Why it matters | How to verify |
|---|---|---|---|
| Q1 | Does your GitHub remote have more history than this local checkout (single commit `52e0466`)? Which files did you write vs. copy? | Authorship claims, license text, what to describe as "yours" | `git log --stat` on the remote; your original work history |
| Q2 | Does `soccer_game.py` start and play correctly on your machine (the gravity/goal findings are from code + arithmetic, not observed)? | B4/B5/B7/B8 | Run it; try to score; watch ball at rest |
| Q3 | What does the AR mode look like with OpenCV < 4.7 and a webcam (field orientation, scale, mirroring)? | B10/B11 are [Derived] | Run with an older cv2 once, screenshot |
| Q4 | Do goalposts/legs render below ground in VR/AR? Are players on their sides in the 3D viewer? | B14, B16 are [Derived] from rotation math | Run both and look |
| Q5 | Which OpenGL version/driver do the target machines have? Does `glGenerateMipmap` work without extra setup? | Fixed-function + mipmaps need a capable context | Run on a clean Windows laptop |
| Q6 | Is there a `README_WINDOWS.md` or other files that exist locally but were never pushed? | Referenced by `run_windows_version.py:73` | Check your working tree / `.gitignore` effects |
| Q7 | What terms apply to `barcelona.zip` (frames + annotations)? And what is the origin/licence of `model.yml.gz` and `field.png`? | L5/L6 | UW GRAIL project page, upstream repo |
| Q8 | What licence does the hourglass implementation carry upstream (bearpaw/pytorch-pose)? | L4 | Check upstream repo |
| Q9 | Did the CPU NMS / pycocotools / `compile.sh` ever build on your Windows machine? Do you intend to support the inherited pipeline at all? | Decides whether `requirements-pipeline.txt` is worth keeping | Try or drop it |
| Q10 | Which exact OpenCV version removed `Dictionary_get` etc.? (Reported as 4.7 from memory; 5.0.0 was verified) | Version pin in requirements | OpenCV 4.x changelog / test with 4.6 vs 4.8 |
| Q11 | Do you actually want VR to mean *HMD* support (OpenXR/WebXR), or is stereo preview enough as a stated scope? | Scope of README claims | Your decision |
| Q12 | Is it acceptable to rename files/introduce a package? (Audit made no changes.) | Plan assumes a `soccer_ar_vr/` package | Your decision |

---

## 12. Implementation Plan (≈ 2–3 days focused work)

Assumes one developer, Windows machine with a webcam, no new features beyond what is listed.

### Day 1 — Make it run, make it true (≈ 7-8 h)

| Time | Task | Done when |
|---|---|---|
| 1 h | New `requirements*.txt`, `.gitignore` exceptions, fresh venv | `pip install -r requirements.txt` then `python soccer_game.py` starts |
| 1 h | Fix ArUco API (B1) + marker generator script | `python -c "import ar_soccer_experience"` succeeds; marker round-trip test passes |
| 2 h | Unified launcher (`main.py --mode`), fix Tk bugs (B3, B17, B18), remove dead options | Every mode starts from one command; launcher doesn't crash without dataset/camera |
| 3 h | 2D fixes: pitch/goal geometry, no gravity, damping, collision guard, stamina, selection (B4-B8) | You can score on the drawn goal; ball at rest stays at rest; all 11 selectable |
| 1 h | Quick 3D/VR fixes (B9, B12-B14, B16) | Visual check: posts above ground, stereo undistorted, V toggles once |

### Day 2 — Structure and proof (≈ 7-8 h)

| Time | Task | Done when |
|---|---|---|
| 3-4 h | Extract `soccer_ar_vr/` (`physics`, `match`, `stamina`, `pitch`, `formations`); `soccer_game.py` becomes view/controller; AR/VR reuse physics | Game behaves as before; no pygame import in logic modules |
| 3 h | Write the §9.1 tests; `ruff`; `pytest` green locally | ≥ 15 tests passing; physics/match coverage > 80% |
| 1 h | Add GitHub Actions (§9.3), confirm green on Ubuntu + Windows | Green badge |
| 30 min | Remove `barcelona.zip` from tree, add download helper w/ checksum | Repo size drops ~41 MB (history unchanged unless you rewrite it) |

### Day 3 — Polish and presentation (≈ 5-6 h, can be trimmed)

| Time | Task | Done when |
|---|---|---|
| 2 h | 2D UI polish (non-blocking goal banner, pause/restart, smaller labels, hover/keyboard menu) | Screenshot-worthy |
| 2-3 h | AR: render webcam background, status text, axis flip/scale (B10, B11) — **skip and relabel AR "experimental" if no time** | Pitch locked on marker, video visible |
| 1.5 h | Screenshots/GIF, rewrite README (§10), `THIRD_PARTY_NOTICES.md`, fix LICENSE/README mismatch, `docs/VERIFICATION.md` | README matches code; every claim has a verification row |

### Cut-down 1-day version (if time is very tight)

B2 (requirements), B1 (ArUco), B3 + B17 (launcher), B4 + B5 (goal + gravity), L1 + L2 (license + attribution), README status table, and 6-8 physics/match unit tests + CI. That alone removes every Critical/High item except the cosmetic AR overlay.

### Definition of done

- [ ] Fresh clone → `pip install -r requirements.txt` → `python main.py` works on Windows 10/11.
- [ ] `pytest` and CI green on Windows + Ubuntu.
- [ ] README states what is original, what is inherited, and the licence — consistent with `LICENSE`.
- [ ] Every README feature has a row in `docs/VERIFICATION.md` with a date and platform.
- [ ] No Critical/High finding in §5 remains open.

---

*Report generated from static analysis only. No project files were modified, no dependencies installed, no commits made. The only file created is this report.*
