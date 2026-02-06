import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from pathlib import Path

import pygame

from services.state_loader import load_json
from screens.combat_viewer import CombatViewerScreen


def test_combat_replay_advances() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))

    root = Path(__file__).resolve().parents[1]
    events = load_json(root / "data/mock_combat_log_advanced.json")
    screen = CombatViewerScreen(events)

    for _ in range(len(events)):
        screen._advance_event()

    player_board = screen._boards.get("player") or screen._boards.get("p1") or []
    opponent_board = screen._boards.get("opponent") or screen._boards.get("p2") or []

    assert sum(1 for m in player_board if m is not None) >= 2
    assert sum(1 for m in opponent_board if m is not None) >= 1
