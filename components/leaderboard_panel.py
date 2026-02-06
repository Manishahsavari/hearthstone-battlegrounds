from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import pygame

from common.models import Player


Color = Tuple[int, int, int]


@dataclass
class LeaderboardPanel:
    rect: pygame.Rect
    players: List[Player] = field(default_factory=list)

    bg: Color = (18, 18, 24)
    border: Color = (90, 90, 120)
    title_color: Color = (170, 170, 200)
    text_color: Color = (230, 230, 240)
    dead_color: Color = (170, 90, 90)
    ghost_color: Color = (140, 140, 170)

    def update_players(self, players: List[Player]) -> None:
        self.players = players

    def render(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        pygame.draw.rect(surface, self.bg, self.rect, border_radius=8)
        pygame.draw.rect(surface, self.border, self.rect, width=2, border_radius=8)

        title = font.render("Leaderboard", True, self.title_color)
        surface.blit(title, (self.rect.x + 10, self.rect.y + 8))

        y = self.rect.y + 34
        line_height = font.get_height() + 4

        for player in self.players:
            status = ""
            color = self.text_color
            if player.is_dead:
                status = "DEAD"
                color = self.dead_color
            elif player.is_ghost:
                status = "GHOST"
                color = self.ghost_color

            name = player.hero_name or player.name or player.player_id
            info = f"{name} | HP {player.health} | T{player.tavern_tier}"
            if status:
                info = f"{info} | {status}"

            text_surf = font.render(info, True, color)
            surface.blit(text_surf, (self.rect.x + 10, y))
            y += line_height
            if y > self.rect.bottom - line_height:
                return
