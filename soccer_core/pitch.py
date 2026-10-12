"""Pitch geometry shared by gameplay logic and rendering.

Having one description of where the pitch lines and goals are is what keeps
the drawn goal and the scoring check in agreement. (Audit finding B4)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Pitch2D:
    """Geometry of the top-down 2D pitch, in screen pixels.

    The playing area is the window inset by `margin` on every side. Each goal
    is a rectangle of `goal_depth` x `goal_height` sitting *outside* the goal
    line, centred vertically - exactly what `draw_goals` renders.
    """

    width: int = 1280
    height: int = 720
    margin: int = 100
    goal_height: int = 100
    goal_depth: int = 20

    # --- pitch lines -----------------------------------------------------
    @property
    def left(self) -> float:
        """x of the left goal line."""
        return float(self.margin)

    @property
    def right(self) -> float:
        """x of the right goal line."""
        return float(self.width - self.margin)

    @property
    def top(self) -> float:
        """y of the top touchline."""
        return float(self.margin)

    @property
    def bottom(self) -> float:
        """y of the bottom touchline."""
        return float(self.height - self.margin)

    @property
    def centre(self) -> tuple[float, float]:
        """Centre spot."""
        return (self.width / 2.0, self.height / 2.0)

    # --- goals -----------------------------------------------------------
    @property
    def goal_y0(self) -> float:
        """y of the top of both goal mouths."""
        return self.height / 2.0 - self.goal_height / 2.0

    @property
    def goal_y1(self) -> float:
        """y of the bottom of both goal mouths."""
        return self.height / 2.0 + self.goal_height / 2.0

    @property
    def net_left(self) -> float:
        """x of the back of the left net."""
        return self.left - self.goal_depth

    @property
    def net_right(self) -> float:
        """x of the back of the right net."""
        return self.right + self.goal_depth

    def in_goal_mouth(self, y: float) -> bool:
        """True when height `y` is between the posts of either goal."""
        return self.goal_y0 < y < self.goal_y1


@dataclass(frozen=True)
class Pitch3D:
    """Geometry of the 3D pitch, in metres, used by the AR and VR scenes.

    The pitch lies in the XZ plane with Y up: X runs goal-to-goal (the long
    axis) and Z runs touchline-to-touchline. The original code called these
    FIELD_WIDTH and FIELD_LENGTH the other way round, which is why players
    ended up outside the pitch. (Audit finding B9)
    """

    length_x: float = 105.0      # goal line to goal line (the long axis)
    width_z: float = 68.0        # touchline to touchline
    goal_width: float = 7.32     # FIFA goal width, spans Z
    goal_height: float = 2.44    # FIFA goal height, spans Y
    goal_depth: float = 1.5      # how far the net extends behind the goal line

    @property
    def half_length(self) -> float:
        """Distance from the centre spot to either goal line."""
        return self.length_x / 2.0

    @property
    def half_width(self) -> float:
        """Distance from the centre spot to either touchline."""
        return self.width_z / 2.0

    def contains(self, x: float, z: float, tolerance: float = 0.0) -> bool:
        """True when (x, z) is inside the pitch markings."""
        return (abs(x) <= self.half_length + tolerance and
                abs(z) <= self.half_width + tolerance)

    def is_between_posts(self, z: float) -> bool:
        """True when depth `z` is between the goalposts."""
        return abs(z) < self.goal_width / 2.0
