from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

import pygame


Color = Tuple[int, int, int]


@dataclass
class LogPanel:
    """
    Simple vertical log panel used for combat/recruit logs.
    Keeps the most recent N lines.
    """

    rect: pygame.Rect
    max_lines: int = 40
    bg: Color = (20, 20, 30)
    border: Color = (120, 120, 150)
    text_color: Color = (230, 230, 240)
    _lines: List[str] = field(default_factory=list)

    def add_line(self, text: str) -> None:
        self._lines.append(text)
        if len(self._lines) > self.max_lines:
            self._lines = self._lines[-self.max_lines :]

    def render(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        pygame.draw.rect(surface, self.bg, self.rect)
        pygame.draw.rect(surface, self.border, self.rect, width=2)

        x = self.rect.x + 8
        y = self.rect.y + 8
        line_height = font.get_linesize()

        for line in self._lines:
            if y + line_height > self.rect.bottom - 4:
                break
            text_surf = font.render(line, True, self.text_color)
            surface.blit(text_surf, (x, y))
            y += line_height
