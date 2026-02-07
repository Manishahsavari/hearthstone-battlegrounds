import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from common.models import Minion
from components.card_slot import CardSlot
from services.drag_manager import DragManager


def test_drag_play_calls_callback() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))

    shop_slots = [CardSlot(pygame.Rect(0, 0, 10, 10))]
    hand_slots = [CardSlot(pygame.Rect(20, 0, 10, 10))]
    board_slots = [CardSlot(pygame.Rect(40, 0, 10, 10))]

    minion = Minion(card_id="m1", name="Murloc", attack=1, health=1, tier=1)
    hand_slots[0].minion = minion

    called = {}

    def on_buy(index: int) -> None:
        called["buy"] = index

    def on_play(hand_index: int, board_index: int) -> None:
        called["play"] = (hand_index, board_index)

    def on_sell(index: int) -> None:
        called["sell"] = index

    drag = DragManager(on_buy=on_buy, on_play=on_play, on_sell=on_sell)

    drag.handle_mouse_down((21, 1), shop_slots, hand_slots, board_slots)
    drag.handle_mouse_move((41, 1))
    drag.handle_mouse_up((41, 1), shop_slots, hand_slots, board_slots)

    assert called.get("play") == (0, 0)
