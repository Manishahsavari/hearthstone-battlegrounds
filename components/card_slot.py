from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import pygame

from common.models import Minion, ShopSlot


Color = Tuple[int, int, int]


@dataclass
class CardSlot:
    

    rect: pygame.Rect
    minion: Optional[Minion] = None
    frozen: bool = False  

    bg: Color = (55, 55, 90)
    border: Color = (210, 210, 230)
    empty_bg: Color = (30, 30, 45)
    frozen_border: Color = (90, 180, 255)
    text: Color = (245, 245, 245)

    def set_empty(self) -> None:
        self.minion = None
        self.frozen = False

    def set_minion(self, minion: Minion) -> None:
        self.minion = minion

    def set_shop_slot(self, slot: Optional[ShopSlot]) -> None:
        if slot is None or slot.minion is None:
            self.set_empty()
            return
        self.minion = slot.minion
        self.frozen = bool(slot.frozen)

    def render(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        is_empty = self.minion is None

        pygame.draw.rect(
            surface,
            self.empty_bg if is_empty else self.bg,
            self.rect,
            border_radius=10,
        )

        border_color = self.frozen_border if self.frozen else self.border
        pygame.draw.rect(
            surface,
            border_color,
            self.rect,
            width=2,
            border_radius=10,
        )
        if is_empty:
            return

        name = self.minion.name
        if len(name) > 12:
            name = name[:11] + "…"

        name_surf = font.render(name, True, self.text)
        surface.blit(name_surf, (self.rect.x + 8, self.rect.y + 8))

        # Keyword badges under the name
        if getattr(self.minion, "keywords", None):
            x = self.rect.x + 8
            y = self.rect.y + 30
            for kw in self.minion.keywords:
                label = kw.name
                # Simple width clamp
                if len(label) > 10:
                    label = label[:9] + "…"

                text_surf = font.render(label, True, (10, 10, 10))
                pad_x, pad_y = 6, 2
                badge_rect = text_surf.get_rect()
                badge_rect.x = x
                badge_rect.y = y
                badge_rect = badge_rect.inflate(pad_x * 2, pad_y * 2)

                # Color by keyword type (very simple mapping)
                name_lower = kw.name.lower()
                if "taunt" in name_lower:
                    badge_bg = (140, 120, 200)
                elif "divine" in name_lower:
                    badge_bg = (220, 210, 120)
                elif "reborn" in name_lower:
                    badge_bg = (160, 210, 180)
                else:
                    badge_bg = (200, 200, 200)

                pygame.draw.rect(surface, badge_bg, badge_rect, border_radius=6)
                pygame.draw.rect(
                    surface, (20, 20, 20), badge_rect, width=1, border_radius=6
                )
                surface.blit(
                    text_surf,
                    text_surf.get_rect(center=badge_rect.center),
                )

                x += badge_rect.width + 4

        atk_surf = font.render(str(self.minion.attack), True, self.text)
        hp_surf = font.render(str(self.minion.health), True, self.text)

        surface.blit(atk_surf, (self.rect.x + 8, self.rect.bottom - 26))
        surface.blit(
            hp_surf,
            (self.rect.right - hp_surf.get_width() - 8, self.rect.bottom - 26),
        )

