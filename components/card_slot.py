from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import pygame

from common.models import Minion, ShopSlot

try:
    from services.asset_loader import load_minion_art
except ImportError:
    def load_minion_art(_: str, size: tuple = (80, 80)) -> Optional[pygame.Surface]:
        return None


Color = Tuple[int, int, int]


@dataclass
class CardSlot:
    rect: pygame.Rect
    minion: Optional[Minion] = None
    frozen: bool = False

    bg: Color = (50, 45, 55)
    border: Color = (180, 170, 150)
    empty_bg: Color = (28, 25, 35)
    frozen_border: Color = (90, 180, 255)
    text: Color = (255, 248, 220)
    golden_border: Color = (220, 190, 80)
    ornate_dark: Color = (60, 50, 40)

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

    def render(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        hover: bool = False,
    ) -> None:
        is_empty = self.minion is None

        pygame.draw.rect(
            surface,
            self.empty_bg if is_empty else self.bg,
            self.rect,
            border_radius=12,
        )

        if self.frozen:
            border_color = self.frozen_border
        elif getattr(self.minion, "is_golden", False) and not is_empty:
            border_color = self.golden_border
        else:
            border_color = self.border
        # Ornate HS-style: inner dark trim then gold/colored outer
        pygame.draw.rect(surface, self.ornate_dark, self.rect, width=1, border_radius=12)
        width = 3 if hover else 2
        pygame.draw.rect(
            surface,
            border_color,
            self.rect,
            width=width,
            border_radius=12,
        )
        if is_empty:
            return

        # Minion art (HS-style) - centered
        art = load_minion_art(self.minion.card_id, (self.rect.w - 16, 70))
        if art:
            art_rect = art.get_rect(centerx=self.rect.centerx, top=self.rect.y + 6)
            surface.blit(art, art_rect)

        name = self.minion.name
        if len(name) > 12:
            name = name[:11] + "…"
        name_surf = font.render(name, True, self.text)
        name_y = self.rect.y + (80 if art else 8)
        surface.blit(name_surf, (self.rect.x + 8, name_y))

        # Keyword badges under the name
        if getattr(self.minion, "keywords", None):
            x = self.rect.x + 8
            y = name_y + 20
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

        # HS-style stat bubbles: attack (orange) bottom-left, health (green) bottom-right
        bubble_r = 14
        atk_color = (220, 130, 60)
        hp_color = (60, 160, 90)
        atk_center = (self.rect.x + 22, self.rect.bottom - 22)
        hp_center = (self.rect.right - 22, self.rect.bottom - 22)
        pygame.draw.circle(surface, atk_color, atk_center, bubble_r)
        pygame.draw.circle(surface, hp_color, hp_center, bubble_r)
        small_font = pygame.font.SysFont("Arial", 16, bold=True)
        atk_surf = small_font.render(str(self.minion.attack), True, (30, 20, 10))
        hp_surf = small_font.render(str(self.minion.health), True, (15, 25, 15))
        surface.blit(atk_surf, atk_surf.get_rect(center=atk_center))
        surface.blit(hp_surf, hp_surf.get_rect(center=hp_center))

