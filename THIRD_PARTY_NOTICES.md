# Third-Party Notices

This repository contains code from several sources. This file lists every
component that was not written for this project, what it is, and the
licence evidence found in the repository itself. Nothing here is inferred
beyond what the files state; where a file states no licence, that is
recorded as an open question rather than guessed at.

See also [SOCCER_PROJECT_AUDIT.md](SOCCER_PROJECT_AUDIT.md) §6–7 for the
original audit this file is based on, and [docs/VERIFICATION.md](docs/VERIFICATION.md)
for how the current code was tested.

---

## 1. Soccer on Your Tabletop (primary inherited codebase)

| | |
|---|---|
| **Directories** | `soccer3d/`, `utils/` (excluding the vendored components listed below), `demo/`, `compile.sh` |
| **Also includes** | `barcelona.zip` (sample dataset), `demo/data/field.png` |
| **Authors** | Konstantinos Rematas, Ira Kemelmacher-Shlizerman, Brian Curless, Steve Seitz |
| **Publication** | *Soccer on Your Tabletop*, CVPR 2018 |
| **Project page** | <http://grail.cs.washington.edu/projects/soccer/> |
| **Licence** | BSD 2-Clause (full text in [LICENSE](LICENSE), copyright 2018 the authors above) |
| **Evidence** | The repository's own `LICENSE` file names these four authors and this licence; `run_soccer_on_table.py`'s "About this project" screen cites the same project URL and CVPR 2018 attribution. |

This is the licence that governs the repository as currently distributed:
the single `LICENSE` file at the repository root is BSD-2-Clause and
applies to the whole repo as checked out. It is reproduced here unmodified,
with the original copyright notice intact, per the licence's own
redistribution terms.

**Open question:** the terms under which `barcelona.zip` (frame images and
annotations, ~41 MB) may be redistributed are not stated anywhere in this
repository. The dataset is referenced as coming from the project above;
anyone redistributing this repository further should confirm the dataset's
licence with the original project rather than assume BSD-2 extends to it.

## 2. Fast R-CNN / Faster R-CNN components

| | |
|---|---|
| **Files** | `utils/nms/nms/cpu_nms.pyx`, `utils/nms/nms/gpu_nms.pyx`, `utils/nms/nms/gpu_nms.hpp`, `utils/nms/nms/nms_kernel.cu`, `utils/nms/nms/py_cpu_nms.py`, `utils/nms/utils/bbox.pyx`, `utils/nms/utils/blob.py`, `utils/nms/utils/timer.py` |
| **Copyright** | 2015 Microsoft |
| **Authors** | Ross Girshick (`cpu_nms.pyx`, `gpu_nms.pyx`); Sergey Karayev (`bbox.pyx`) |
| **Licence** | MIT (per in-file header: *"Licensed under The MIT License [see LICENSE for details]"*) |
| **Evidence** | Each file carries this exact header as a comment block at the top. |

No separate `LICENSE` file for this component exists in the vendored copy;
the header's pointer to "see LICENSE" refers to the original Fast/Faster
R-CNN repository, not a file present here.

## 3. pycocotools (Microsoft COCO Toolbox)

| | |
|---|---|
| **Files** | `utils/nms/pycocotools/__init__.py`, `coco.py`, `mask.py`, `_mask.pyx`, `_mask.c`, `maskApi.c`, `maskApi.h` |
| **Copyright** | 2015, Piotr Dollar and Tsung-Yi Lin |
| **Licence** | "Simplified BSD License" (per `maskApi.h`: *"Licensed under the Simplified BSD License [see coco/license.txt]"*) |
| **Pinned revision** | `utils/nms/pycocotools/UPSTREAM_REV` records the upstream commit: `https://github.com/pdollar/coco/commit/3ac47c77ebd5a1ed4254a98b7fbf2ef4765a3574` |
| **Evidence** | `maskApi.h` header comment; `coco.py` carries `__author__ = 'tylin'`. |

**Known defect, not a licence issue:** `coco.py` is Python 2 source (uses
`print` as a statement) and fails `ast.parse` under Python 3. It is excluded
from this project's linting and tests (see `ruff.toml`, `pytest.ini`) for
that reason, not because of its licence.

**Open question:** the `coco/license.txt` the header refers to is not
present in this repository. The SPDX-recognisable name for "Simplified BSD
License" is typically BSD-2-Clause, but that has not been confirmed against
upstream's actual licence text.

## 4. Detectron inference script (Facebook)

| | |
|---|---|
| **File** | `utils/thirdpartyscripts/infer_subimages.py` |
| **Copyright** | 2017-present, Facebook, Inc. |
| **Licence** | Apache License, Version 2.0 |
| **Evidence** | Full Apache-2.0 header comment at the top of the file, including the standard "AS IS" disclaimer and a link to `http://www.apache.org/licenses/LICENSE-2.0`. |

Apache-2.0 requires that a copy of the licence be included with any
redistribution and that changes be stated. The header is preserved
unmodified in this repository; no changes have been made to this file.

## 5. Stacked Hourglass network implementation

| | |
|---|---|
| **File** | `soccer3d/soccerdepth/models/hourglass.py` |
| **Attribution in file** | `(c) YANG, Wei` (comment at the top of the file) |
| **Licence** | **Not stated in the file.** No licence header, no SPDX tag, no accompanying licence file for this module. |

**Open question — unresolved.** This file's docstring attributes it to
"YANG, Wei" but states no licence. It closely resembles the stacked
hourglass pose-estimation code published by Wei Yang (`bearpaw`) in several
public repositories, which is typically MIT-licensed, but this project does
not represent that as confirmed — that repository was not cross-checked.
Anyone redistributing this file should track down its specific upstream
source and licence before relying on it.

## 6. Instance segmentation model weights

| | |
|---|---|
| **File** | `soccer3d/instancesegm/model.yml.gz` (~36 MB uncompressed) |
| **Format** | Looks like an OpenCV structured-edge-detection model file (gzip-compressed YAML), based on its location alongside `soccer3d/instancesegm/core.cpp` (C++ instance segmentation code) and its `.yml.gz` extension, which is the format OpenCV's `cv::ximgproc` structured-edge detector uses. |
| **Licence / provenance** | **Not stated anywhere in this repository.** No header, no accompanying notice, no reference to where it was trained or sourced from. |

**Open question — unresolved.** This is the least-documented component in
the repository. Its exact origin (whether it ships with an OpenCV extra
module, was trained by the Soccer-on-Your-Tabletop authors, or comes from
elsewhere) was not determined. Treat its redistribution terms as unknown
rather than assuming it is covered by the repository's BSD-2-Clause
`LICENSE`.

## 7. Field texture asset

| | |
|---|---|
| **File** | `demo/data/field.png` |
| **Licence / provenance** | Not separately stated; shipped alongside the Soccer-on-Your-Tabletop demo scripts, so treated here as part of that codebase's BSD-2-Clause coverage (§1). Not independently verified against the original project. |

---

## 8. Original contributions in this repository

The following were written for this project (by Tojin Varkey Simson and
Jaiby Mariya Jospeh, with AI-assisted engineering work across three
phases — see [SOCCER_PROJECT_AUDIT.md](SOCCER_PROJECT_AUDIT.md) and
`docs/VERIFICATION.md` for what was changed and why) and are **not** part
of the inherited Soccer-on-Your-Tabletop codebase:

- `soccer_game.py` — 2D match (pygame)
- `ar_soccer_experience.py`, `vr_soccer_experience.py` — AR/VR prototypes
- `soccer3d_viewer.py` — orbiting 3D pitch viewer
- `soccer_core/` — display-independent physics, pitch geometry, formations,
  stereo camera maths, AR pose maths
- `soccer_gl.py` — shared OpenGL drawing for the AR/VR scenes
- `modern_interface.py` — Tkinter launcher
- `run_windows_version.py` — console launcher
- `setup_ar_vr.py` — dependency/marker/launcher setup script
- `tools/make_markers.py` — standalone ArUco marker generator
- `tests/`, `pytest.ini`, `ruff.toml`, `.github/workflows/ci.yml` — test
  suite, lint configuration and CI
- `requirements*.txt` — dependency manifests
- This file, `SOCCER_PROJECT_AUDIT.md`, `docs/VERIFICATION.md`, and the
  current `README.md`

These files carry no separate licence header; they are distributed under
the same BSD-2-Clause `LICENSE` that covers the rest of this repository as
checked out, with the understanding that the copyright notice already in
`LICENSE` names the original Soccer-on-Your-Tabletop authors and this file
does not add or imply any additional copyright claim over the inherited
material listed in §1–§7 above.

---

## Summary table

| Component | Licence | Status |
|---|---|---|
| Soccer on Your Tabletop core (§1) | BSD-2-Clause | Confirmed (repo `LICENSE`) |
| Fast/Faster R-CNN NMS code (§2) | MIT | Confirmed (in-file headers) |
| pycocotools (§3) | "Simplified BSD" | Confirmed by header; exact text not vendored |
| Detectron inference script (§4) | Apache-2.0 | Confirmed (in-file header) |
| Hourglass network (§5) | Unknown | **Unresolved** |
| Instance-segmentation model weights (§6) | Unknown | **Unresolved** |
| Field texture asset (§7) | Assumed BSD-2 via §1 | Not independently verified |
| Original contributions (§8) | BSD-2-Clause (this repo's `LICENSE`) | — |
