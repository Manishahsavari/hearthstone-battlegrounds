from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

import pygame

from common.models import Minion


@dataclass
class PopupChoice:
    """
    Discover/Choose-One popup: shows 3 card options, user picks one.
    Used for Triple reward and similar choices.
    """

    rect: pygame.Rect
    options: List[Minion]
    on_choice: Callable[[int], None]
    title: str = "Discover a minion"
    visible: bool = True

    bg: tuple[int, int, int] = (25, 25, 40)
    border: tuple[int, int, int] = (180, 160, 100)
    text: tuple[int, int, int] = (240, 240, 240)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Return True if event was consumed (popup should block other UI)."""
        if not self.visible or event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False

        ox, oy = self.rect.x, self.rect.y
        card_w, card_h = 100, 140
        gap = 20
        total_w = 3 * card_w + 2 * gap
        start_x = ox + (self.rect.width - total_w) // 2
        start_y = oy + 50

        for i in range(min(3, len(self.options))):
            r = pygame.Rect(start_x + i * (card_w + gap), start_y, card_w, card_h)
            if r.collidepoint(event.pos):
                self.on_choice(i)
                self.visible = False
                return True
        return False

    def render(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        if not self.visible:
            return

        pygame.draw.rect(surface, self.bg, self.rect, border_radius=12)
        pygame.draw.rect(surface, self.border, self.rect, width=3, border_radius=12)

        title_surf = font.render(self.title, True, self.text)
        surface.blit(
            title_surf,
            title_surf.get_rect(centerx=self.rect.centerx, top=self.rect.y + 16),
        )

        card_w, card_h = 100, 140
        gap = 20
        total_w = 3 * card_w + 2 * gap
        start_x = self.rect.x + (self.rect.width - total_w) // 2
        start_y = self.rect.y + 50

        for i, opt in enumerate(self.options[:3]):
            r = pygame.Rect(start_x + i * (card_w + gap), start_y, card_w, card_h)
            pygame.draw.rect(surface, (55, 55, 90), r, border_radius=8)
            pygame.draw.rect(surface, (200, 200, 220), r, width=2, border_radius=8)
            name = opt.name[:10] + "…" if len(opt.name) > 10 else opt.name
            name_surf = font.render(name, True, self.text)
            surface.blit(name_surf, (r.x + 6, r.y + 8))
            stats = font.render(f"{opt.attack}/{opt.health}", True, self.text)
            surface.blit(stats, (r.x + 6, r.bottom - 24))
