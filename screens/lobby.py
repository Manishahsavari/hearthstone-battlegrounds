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
    is_bot: bool = False


class LobbyScreen:
    def __init__(self, on_action: Callable[[dict], None], set_screen: Callable[[str], None]) -> None:
        self._on_action = on_action
        self._set_screen = set_screen
        self._font = pygame.font.SysFont("Arial", 18)
        self._title_font = pygame.font.SysFont("Arial", 28, bold=True)

        self.players: List[LobbyPlayer] = [LobbyPlayer("...", "...") for _ in range(4)]
        self._can_start = False

        self._build_layout()

    def _build_layout(self) -> None:
        self._ready_buttons: List[Btn] = []
        base_x = 100
        base_y = 140
        slot_w = 320
        slot_h = 90
        gap_y = 100
        self._player_rects: List[pygame.Rect] = []

        for i in range(4):
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

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self._ready_buttons:
                btn.handle_event(event)
            self._start_button.handle_event(event)

    def update(self, dt: float) -> None:
        pass

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((8, 8, 16))
        title = self._title_font.render("Lobby", True, (240, 240, 240))
        surface.blit(title, (100, 60))

        for i, player in enumerate(self.players):
            rect = self._player_rects[i]
            bg = (30, 50, 70) if player.ready else (25, 25, 40)
            border = (80, 200, 120) if player.ready else (140, 140, 180)
            pygame.draw.rect(surface, bg, rect, border_radius=10)
            pygame.draw.rect(surface, border, rect, width=2, border_radius=10)

            label = player.name + (" [BOT]" if player.is_bot else "")
            surface.blit(self._font.render(label, True, (240, 240, 240)), (rect.x + 12, rect.y + 12))
            surface.blit(self._font.render(player.hero, True, (210, 210, 230)), (rect.x + 12, rect.y + 40))

        for btn in self._ready_buttons:
            btn.render(surface, self._font)

        self._start_button.render(surface, self._font)

        status = "Ready to start" if self._can_start else "Waiting for players / ready"
        surface.blit(self._font.render(status, True, (170, 170, 190)), (280, 545))

    def _toggle_ready(self, index: int) -> None:
        self._on_action({"action": "LOBBY_READY_TOGGLE", "payload": {"player_index": index}})

    def _start_game(self) -> None:
        if not self._can_start:
            return
        self._on_action({"action": "LOBBY_START"})

    def handle_server_message(self, msg: dict) -> None:
        t = msg.get("type")
        if t == "LOBBY_UPDATE":
            payload = msg.get("payload") or {}
            players = payload.get("players") or []
            can_start = payload.get("can_start")
            if isinstance(can_start, bool):
                self._can_start = can_start
            for p in players:
                idx = p.get("player_index")
                if not isinstance(idx, int) or not (0 <= idx < 4):
                    continue
                name = p.get("name")
                hero = p.get("hero")
                ready = p.get("ready")
                is_bot = p.get("is_bot")
                if isinstance(name, str):
                    self.players[idx].name = name
                if isinstance(hero, str):
                    self.players[idx].hero = hero
                if isinstance(ready, bool):
                    self.players[idx].ready = ready
                if isinstance(is_bot, bool):
                    self.players[idx].is_bot = is_bot

        elif t == "GAME_START":
            self._set_screen("recruit")
