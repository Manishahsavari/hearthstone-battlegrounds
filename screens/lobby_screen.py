from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import pygame


Color = Tuple[int, int, int]


@dataclass
class LobbySlot:
    hero_name: str
    portrait_path: Optional[str]
    ready: bool = False


class LobbyScreen:
    def __init__(self, on_start: Callable[[], None]) -> None:
        self._on_start = on_start
        self._font = pygame.font.SysFont("Arial", 18)
        self._small_font = pygame.font.SysFont("Arial", 14)

        self._slots: List[LobbySlot] = [
            LobbySlot(
                "Sylvanas Windrunner",
                "hearthstone-battlegrounds/bgknowhow-main/images/heroes/BG23_HERO_306_render_80.webp",
                True,
            ),
            LobbySlot(
                "The Lich King",
                "hearthstone-battlegrounds/bgknowhow-main/images/heroes/TB_BaconShop_HERO_22_render_80.webp",
                False,
            ),
            LobbySlot(
                "Millhouse Manastorm",
                "hearthstone-battlegrounds/bgknowhow-main/images/heroes/TB_BaconShop_HERO_49_render_80.webp",
                True,
            ),
            LobbySlot(
                "Yogg-Saron",
                "hearthstone-battlegrounds/bgknowhow-main/images/heroes/TB_BaconShop_HERO_35_render_80.webp",
                False,
            ),
        ]

        self._start_button = pygame.Rect(520, 620, 240, 50)
        self._portraits: List[Optional[pygame.Surface]] = []
        self._load_portraits()

    def _load_portraits(self) -> None:
        for slot in self._slots:
            if slot.portrait_path is None:
                self._portraits.append(None)
                continue
            try:
                self._portraits.append(pygame.image.load(slot.portrait_path))
            except (pygame.error, FileNotFoundError):
                self._portraits.append(None)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._start_button.collidepoint(event.pos):
                self._on_start()

    def update(self, dt: float) -> None:
        return

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((16, 16, 24))
        title = self._font.render("Lobby", True, (230, 230, 240))
        surface.blit(title, (40, 30))

        self._render_slots(surface)
        self._render_start(surface)

    def _render_slots(self, surface: pygame.Surface) -> None:
        start_x = 80
        start_y = 120
        gap = 40
        slot_w = 240
        slot_h = 360

        for i, slot in enumerate(self._slots):
            x = start_x + i * (slot_w + gap)
            rect = pygame.Rect(x, start_y, slot_w, slot_h)
            pygame.draw.rect(surface, (30, 30, 42), rect, border_radius=12)
            pygame.draw.rect(surface, (90, 90, 120), rect, width=2, border_radius=12)

            portrait = self._portraits[i] if i < len(self._portraits) else None
            if portrait is not None:
                img = pygame.transform.smoothscale(portrait, (200, 200))
                surface.blit(img, (rect.x + 20, rect.y + 20))
            else:
                placeholder = pygame.Rect(rect.x + 20, rect.y + 20, 200, 200)
                pygame.draw.rect(surface, (50, 50, 70), placeholder, border_radius=10)
                label = self._small_font.render("Hero", True, (200, 200, 220))
                surface.blit(label, label.get_rect(center=placeholder.center))

            name = slot.hero_name
            name_surf = self._small_font.render(name, True, (230, 230, 240))
            surface.blit(name_surf, (rect.x + 20, rect.y + 230))

            ready_text = "READY" if slot.ready else "WAITING"
            color = (120, 200, 160) if slot.ready else (200, 120, 120)
            ready_surf = self._small_font.render(ready_text, True, color)
            surface.blit(ready_surf, (rect.x + 20, rect.y + 260))

    def _render_start(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, (40, 120, 90), self._start_button, border_radius=8)
        pygame.draw.rect(surface, (180, 240, 200), self._start_button, width=2, border_radius=8)
        text = self._font.render("Start", True, (240, 240, 250))
        surface.blit(text, text.get_rect(center=self._start_button.center))
