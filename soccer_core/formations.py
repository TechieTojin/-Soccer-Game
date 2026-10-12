"""Player formations for the 3D (AR/VR) scenes.

The hard-coded formation these scenes used placed goalkeepers at x = +-60 on
a pitch only +-52.5 long, so both keepers stood outside the pitch and the
defenders stood on the goal line. The positions here are derived from the
pitch dimensions instead of being written out by hand, so they cannot drift
outside the markings again. (Audit finding B9)
"""

from __future__ import annotations

from typing import Literal

from soccer_core.pitch import Pitch2D, Pitch3D

Team = Literal["red", "blue"]

RED = (1.0, 0.0, 0.0)
BLUE = (0.0, 0.0, 1.0)

# A 4-3-3, as fractions of the half-length from the centre spot (0.0) to the
# team's own goal line (1.0), paired with offsets across the pitch as
# fractions of the half-width.
_SHAPE: tuple[tuple[float, float], ...] = (
    # Forwards - closest to the halfway line
    (0.20, 0.35), (0.20, 0.0), (0.20, -0.35),
    # Midfielders
    (0.42, 0.44), (0.42, 0.0), (0.42, -0.44),
    # Defenders
    (0.68, 0.58), (0.68, 0.23), (0.68, -0.23), (0.68, -0.58),
    # Goalkeeper
    (0.91, 0.0),
)


def formation_433(pitch: Pitch3D, team: Team) -> list[tuple[float, float]]:
    """Return 11 `(x, z)` positions for `team` in a 4-3-3.

    The red team defends the negative-X goal and the blue team the
    positive-X goal, so their shapes are mirrored. Every position is inside
    the pitch markings by construction.
    """
    direction = -1.0 if team == "red" else 1.0
    return [
        (direction * depth * pitch.half_length, across * pitch.half_width)
        for depth, across in _SHAPE
    ]


# A 4-4-2 for the 2D match, matching the roles the game assigns by squad
# index (0 GK, 1-4 defenders, 5-8 midfielders, 9-10 strikers).
# `depth` runs from the team's own goal line (0.0) to the halfway line (1.0);
# `across` runs from the top touchline (0.0) to the bottom one (1.0).
_SHAPE_2D: tuple[tuple[float, float], ...] = (
    (0.07, 0.50),                                        # GK
    (0.28, 0.15), (0.28, 0.38), (0.28, 0.62), (0.28, 0.85),   # LB CB CB RB
    (0.58, 0.15), (0.58, 0.38), (0.58, 0.62), (0.58, 0.85),   # LM CM CM RM
    (0.85, 0.36), (0.85, 0.64),                               # ST ST
)


def formation_442(pitch: Pitch2D, team: Team) -> list[tuple[float, float]]:
    """Return 11 `(x, y)` kick-off positions in screen pixels.

    Red defends the left goal and blue the right, so the two shapes are
    mirrored about the halfway line. Positions are derived from the pitch
    rather than hard-coded, so they stay inside the markings at any window
    size - the previous grid layout bunched every player into the top half
    of the screen.
    """
    half_length = (pitch.right - pitch.left) / 2.0
    playable_height = pitch.bottom - pitch.top

    positions: list[tuple[float, float]] = []
    for depth, across in _SHAPE_2D:
        if team == "red":
            x = pitch.left + depth * half_length
        else:
            x = pitch.right - depth * half_length
        positions.append((x, pitch.top + across * playable_height))
    return positions


def scene_players(pitch: Pitch3D) -> list[tuple[float, float, tuple[float, float, float]]]:
    """Return `(x, z, rgb)` for all 22 players, red first then blue.

    This is the shape the AR and VR scenes expect for their player list.
    """
    players: list[tuple[float, float, tuple[float, float, float]]] = []
    for team, colour in (("red", RED), ("blue", BLUE)):
        players.extend((x, z, colour) for x, z in formation_433(pitch, team))
    return players
