from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Protocol, Any

import pygame


class Screen(Protocol):
    def handle_event(self, event: pygame.event.Event) -> None: ...
    def update(self, dt: float) -> None: ...
    def render(self, surface: pygame.Surface) -> None: ...


@dataclass
class _EmptyScreen:
    background_color: tuple[int, int, int] = (10, 10, 20)

    def handle_event(self, event: pygame.event.Event) -> None:
        return

    def update(self, dt: float) -> None:
        return

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(self.background_color)


@dataclass
class ScreenManager:
    _screens: Dict[str, Screen] = field(default_factory=dict)
    _active_name: Optional[str] = None
    _fallback: Screen = field(default_factory=_EmptyScreen)

    def register(self, name: str, screen: Screen, *, activate: bool = False) -> None:
        self._screens[name] = screen
        if activate or self._active_name is None:
            self._active_name = name

    @property
    def active(self) -> Screen:
        if self._active_name is None:
            return self._fallback
        return self._screens.get(self._active_name, self._fallback)

    def set_active(self, name: str) -> None:
        if name not in self._screens:
            raise KeyError(f"Screen '{name}' is not registered.")
        self._active_name = name

    def handle_event(self, event: pygame.event.Event) -> None:
        self.active.handle_event(event)

    def update(self, dt: float) -> None:
        self.active.update(dt)

    def render(self, surface: pygame.Surface) -> None:
        self.active.render(surface)

    def handle_server_message(self, msg: dict[str, Any]) -> None:
        scr = self.active
        fn = getattr(scr, "handle_server_message", None)
        if callable(fn):
            fn(msg)
