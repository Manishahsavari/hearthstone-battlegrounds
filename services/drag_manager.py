from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import pygame

from common.models import Minion
from components.card_slot import CardSlot


Area = str 
Pos = Tuple[int, int]


@dataclass
class DragState:
    active: bool = False
    origin_area: Optional[Area] = None
    origin_index: int = -1
    minion: Optional[Minion] = None
    offset: Pos = (0, 0)
    position: Pos = (0, 0)


class DragManager:
    
    def __init__(
        self,
        *,
        on_buy: Callable[[int], None],
        on_play: Callable[[int, int], None],
        on_sell: Callable[[int], None],
    ) -> None:
        self._on_buy = on_buy
        self._on_play = on_play
        self._on_sell = on_sell
        self._state = DragState()

    

    def handle_mouse_down(
        self,
        pos: Pos,
        shop_slots: List[CardSlot],
        hand_slots: List[CardSlot],
        board_slots: List[CardSlot],
    ) -> None:
        for i, slot in enumerate(shop_slots):
            if slot.rect.collidepoint(pos) and slot.minion is not None:
                self._begin_drag("shop", i, slot.minion, pos, slot.rect)
                return

        for i, slot in enumerate(hand_slots):
            if slot.rect.collidepoint(pos) and slot.minion is not None:
                self._begin_drag("hand", i, slot.minion, pos, slot.rect)
                return

        for i, slot in enumerate(board_slots):
            if slot.rect.collidepoint(pos) and slot.minion is not None:
                self._begin_drag("board", i, slot.minion, pos, slot.rect)
                return

    def handle_mouse_move(self, pos: Pos) -> None:
        if not self._state.active:
            return
        self._state.position = pos

    def handle_mouse_up(
        self,
        pos: Pos,
        shop_slots: List[CardSlot],
        hand_slots: List[CardSlot],
        board_slots: List[CardSlot],
    ) -> None:
        if not self._state.active:
            return

        origin_area = self._state.origin_area
        origin_index = self._state.origin_index

        try:
            if origin_area == "shop":
                target_index = _hit_index(pos, hand_slots)
                if target_index is not None:
                    self._on_buy(origin_index)

            elif origin_area == "hand":
                target_index = _hit_index(pos, board_slots)
                if target_index is not None:
                    self._on_play(origin_index, target_index)

            elif origin_area == "board":
                if _hit_index(pos, board_slots) is None:
                    self._on_sell(origin_index)
        finally:
            self._state = DragState()


    def _begin_drag(
        self,
        area: Area,
        index: int,
        minion: Minion,
        pos: Pos,
        rect: pygame.Rect,
    ) -> None:
        offset = (pos[0] - rect.x, pos[1] - rect.y)
        self._state = DragState(
            active=True,
            origin_area=area,
            origin_index=index,
            minion=minion,
            offset=offset,
            position=pos,
        )


    def render(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """
        Draw the dragged card following the cursor, if any.
        """
        if not self._state.active or self._state.minion is None:
            return

        x, y = self._state.position
        ox, oy = self._state.offset
        rect = pygame.Rect(x - ox, y - oy, 120, 160)

        pygame.draw.rect(surface, (80, 80, 140), rect, border_radius=10)
        pygame.draw.rect(surface, (240, 240, 255), rect, width=2, border_radius=10)

        name = self._state.minion.name
        if len(name) > 12:
            name = name[:11] + "…"
        name_surf = font.render(name, True, (250, 250, 255))
        surface.blit(name_surf, (rect.x + 8, rect.y + 8))

        atk_surf = font.render(str(self._state.minion.attack), True, (250, 250, 255))
        hp_surf = font.render(str(self._state.minion.health), True, (250, 250, 255))
        surface.blit(atk_surf, (rect.x + 8, rect.bottom - 26))
        surface.blit(
            hp_surf, (rect.right - hp_surf.get_width() - 8, rect.bottom - 26)
        )


def _hit_index(pos: Pos, slots: List[CardSlot]) -> Optional[int]:
    for i, slot in enumerate(slots):
        if slot.rect.collidepoint(pos):
            return i
    return None

