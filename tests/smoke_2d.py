"""Headless smoke test for the 2D game.

Unit tests cover the rules; this covers the parts they cannot reach - the
actual pygame update-and-draw loop and every screen's drawing code. It
catches the kind of crash that only happens once something is rendered (a
bad rect, a missing attribute, a surface with the wrong format).

It runs with SDL's dummy video driver, so it needs no display and no
webcam, and it is safe to run in CI.

    python tests/smoke_2d.py
    python tests/smoke_2d.py --frames 600 --shots out/

Exits non-zero if anything raises.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Must be set before pygame is imported.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pygame  # noqa: E402

from soccer_game import SoccerGame  # noqa: E402


def run(frames: int = 300, shots_dir: Path | None = None) -> int:
    """Exercise every screen. Returns a process exit code."""
    game = SoccerGame(enable_camera=False)
    surface = pygame.display.get_surface()
    checks = []

    def snapshot(name: str) -> None:
        if shots_dir is not None:
            shots_dir.mkdir(parents=True, exist_ok=True)
            pygame.image.save(surface, str(shots_dir / f"{name}.png"))

    # --- menu and help -------------------------------------------------
    game.mode = "menu"
    game.draw_menu()
    snapshot("menu")
    checks.append("menu")

    for index in range(len(game.menu_items)):
        game.menu_index = index
        game.draw_menu()
    game.menu_index = 0

    game.mode = "help"
    game.draw_help()
    snapshot("help")
    checks.append("help")

    # --- a simulated match ---------------------------------------------
    game.mode = "2d_game"
    game.reset_game_state()
    game.show_goal_message = lambda message: None
    game.dt = 1 / 60

    for frame in range(frames):
        pygame.event.pump()
        game.update_game_state()
        game.draw_2d_game()
        pygame.display.flip()

        # Exercise the input handlers too.
        if frame % 97 == 0:
            game.handle_game_key(pygame.K_SPACE)
        if frame % 131 == 0:
            game.handle_game_key(pygame.K_TAB)
        if frame % 53 == 0:
            game.handle_game_key(pygame.K_5)

    checks.append(f"{frames} match frames")
    snapshot("match")

    # The ball must still be somewhere sensible.
    pitch = game.pitch
    assert pitch.net_left <= game.ball_pos[0] <= pitch.net_right, \
        f"ball escaped horizontally: {game.ball_pos}"
    assert pitch.top - 1 <= game.ball_pos[1] <= pitch.bottom + 1, \
        f"ball escaped vertically: {game.ball_pos}"
    checks.append("ball in bounds")

    # --- overlays --------------------------------------------------------
    game.show_message("Red Team Scores!", 1600)
    game.draw_2d_game()
    snapshot("goal_banner")
    checks.append("goal banner")

    game.banner_text = None
    game.paused = True
    game.draw_2d_game()
    snapshot("paused")
    checks.append("pause overlay")

    game.paused = False
    game.game_time = 0
    game.draw_2d_game()
    snapshot("full_time")
    checks.append("full-time screen")

    # Restart must bring the clock back.
    game.handle_game_key(pygame.K_r)
    assert game.game_time > 0, "restart did not reset the match clock"
    assert game.score == [0, 0], "restart did not reset the score"
    checks.append("restart")

    pygame.quit()

    print("Smoke test passed:")
    for check in checks:
        print(f"  - {check}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=int, default=300,
                        help="simulated match frames (default: 300)")
    parser.add_argument("--shots", type=Path, default=None,
                        help="directory to save screenshots into")
    args = parser.parse_args(argv)

    try:
        return run(frames=args.frames, shots_dir=args.shots)
    except Exception as error:
        print(f"Smoke test FAILED: {type(error).__name__}: {error}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
