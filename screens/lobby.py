from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

import pygame

from components.btn import Btn


@dataclass
class LobbyPlayer:
    name: str
    hero: str
    ready: bool = False


class LobbyScreen:
    """
    Simple 4-player lobby:
    - shows hero/name per slot
    - allows toggling Ready per player
    - Start button switches to the Recruit screen
    """

    def __init__(
        self,
        on_action: Callable[[dict], None],
        set_screen: Callable[[str], None],
    ) -> None:
        self._on_action = on_action
        self._set_screen = set_screen
        self._font = pygame.font.SysFont("Arial", 18)

        self.players: List[LobbyPlayer] = [
            LobbyPlayer(name="Player 1", hero="Sylvanas"),
            LobbyPlayer(name="Player 2", hero="Lich King"),
            LobbyPlayer(name="Player 3", hero="Millhouse"),
            LobbyPlayer(name="Player 4", hero="Yogg-Saron"),
        ]

        self._build_layout()

    def _build_layout(self) -> None:
        self._ready_buttons: List[Btn] = []

        base_x = 100
        base_y = 140
        slot_w = 260
        slot_h = 90
        gap_y = 100

        self._player_rects: List[pygame.Rect] = []

        for i, player in enumerate(self.players):
            rect = pygame.Rect(base_x, base_y + i * gap_y, slot_w, slot_h)
            self._player_rects.append(rect)

            btn = Btn(
                "Ready",
                pygame.Rect(rect.right + 20, rect.y + 25, 90, 36),
                one_click=lambda idx=i: self._toggle_ready(idx),
            )
            self._ready_buttons.append(btn)

        self._start_button = Btn(
            "Start Game",
            pygame.Rect(100, base_y + 4 * gap_y, 160, 40),
            one_click=self._start_game,
        )

    # ------------------------------------------------------------------
    # Pygame integration

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self._ready_buttons:
                btn.handle_event(event)
            self._start_button.handle_event(event)

    def update(self, dt: float) -> None:
        # No animations yet
        return

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((8, 8, 16))

        title_font = pygame.font.SysFont("Arial", 28, bold=True)
        title = title_font.render("Lobby - Choose Heroes & Ready", True, (240, 240, 240))
        surface.blit(title, (100, 60))

        for i, player in enumerate(self.players):
            rect = self._player_rects[i]
            ready = player.ready

            bg = (30, 50, 70) if ready else (25, 25, 40)
            border = (80, 200, 120) if ready else (140, 140, 180)

            pygame.draw.rect(surface, bg, rect, border_radius=10)
            pygame.draw.rect(surface, border, rect, width=2, border_radius=10)

            name_surf = self._font.render(player.name, True, (240, 240, 240))
            hero_surf = self._font.render(player.hero, True, (210, 210, 230))

            surface.blit(name_surf, (rect.x + 12, rect.y + 12))
            surface.blit(hero_surf, (rect.x + 12, rect.y + 40))

        for btn in self._ready_buttons:
            btn.render(surface, self._font)

        self._start_button.render(surface, self._font)

    # ------------------------------------------------------------------
    # Internal actions

    def _toggle_ready(self, index: int) -> None:
        self.players[index].ready = not self.players[index].ready
        self._on_action(
            {
                "action": "LOBBY_READY_TOGGLE",
                "player_index": index,
                "ready": self.players[index].ready,
            }
        )

    def _start_game(self) -> None:
        # For now, just switch to Recruit screen
        if not any(p.ready for p in self.players):
            # Require at least one Ready
            return
        self._on_action(
            {
                "action": "LOBBY_START",
                "ready_players": [i for i, p in enumerate(self.players) if p.ready],
            }
        )
        self._set_screen("recruit")

