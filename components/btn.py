from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Tuple
import pygame

Color = Tuple[int, int, int]

@dataclass 
class Btn:
    label : str
    rect : pygame.Rect
    one_click: Callable[[],None]
    bg : Color = (40,40,40)
    fg : Color = (240,240,240)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.one_click()
        
    def render(self, surface: pygame.Surface, font: pygame.font.Font)-> None:
        # HS-style ornate button: dark fill, gold-trimmed border
        pygame.draw.rect(surface, self.bg, self.rect, border_radius=8)
        pygame.draw.rect(surface, (80, 65, 40), self.rect, width=1, border_radius=8)
        pygame.draw.rect(surface, (200, 170, 90), self.rect, width=2, border_radius=8)
        text = font.render(self.label, True, (255, 248, 220))
        surface.blit(text, text.get_rect(center=self.rect.center))

