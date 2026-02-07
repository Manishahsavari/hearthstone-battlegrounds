from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pygame


@dataclass
class _Field:
    label: str
    value: str = ""
    is_password: bool = False


class LoginScreen:
    def __init__(self, on_action: Callable[[dict], None], set_screen: Callable[[str], None]) -> None:
        self._on_action = on_action
        self._set_screen = set_screen
        self._font = pygame.font.SysFont("Arial", 20)
        self._title_font = pygame.font.SysFont("Arial", 40, bold=True)
        self._hint_font = pygame.font.SysFont("Arial", 16)
        self._error: str | None = None

        self._fields = [
            _Field("Username"),
            _Field("Password", is_password=True),
        ]
        self._active = 0

        self._btn_font = pygame.font.SysFont("Arial", 18, bold=True)
        self._register_rect = pygame.Rect(520, 470, 140, 42)
        self._login_rect = pygame.Rect(670, 470, 140, 42)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                self._active = (self._active + 1) % len(self._fields)
                return
            if event.key == pygame.K_BACKSPACE:
                f = self._fields[self._active]
                f.value = f.value[:-1]
                return
            if event.key == pygame.K_RETURN:
                self._send_login()
                return
            if event.unicode and event.unicode.isprintable():
                self._fields[self._active].value += event.unicode

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._register_rect.collidepoint(event.pos):
                self._send_register()
            elif self._login_rect.collidepoint(event.pos):
                self._send_login()

    def update(self, dt: float) -> None:
        pass

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((10, 10, 18))

        title = self._title_font.render("Welcome", True, (245, 245, 245))
        surface.blit(title, (520, 150))

        for i, f in enumerate(self._fields):
            y = 260 + i * 70
            label = self._font.render(f.label, True, (200, 200, 220))
            surface.blit(label, (470, y))

            box = pygame.Rect(470, y + 26, 420, 40)
            active = i == self._active
            pygame.draw.rect(surface, (22, 22, 34), box, border_radius=10)
            pygame.draw.rect(surface, (130, 130, 200) if active else (90, 90, 120), box, 2, border_radius=10)

            shown = ("*" * len(f.value)) if f.is_password else f.value
            txt = self._font.render(shown, True, (240, 240, 240))
            surface.blit(txt, (box.x + 12, box.y + 9))

        pygame.draw.rect(surface, (28, 80, 50), self._register_rect, border_radius=10)
        pygame.draw.rect(surface, (30, 60, 110), self._login_rect, border_radius=10)

        rtxt = self._btn_font.render("Register", True, (245, 245, 245))
        ltxt = self._btn_font.render("Login", True, (245, 245, 245))
        surface.blit(rtxt, (self._register_rect.x + 28, self._register_rect.y + 11))
        surface.blit(ltxt, (self._login_rect.x + 48, self._login_rect.y + 11))

        hint = self._hint_font.render("Tab: switch field | Enter: login", True, (170, 170, 190))
        surface.blit(hint, (470, 530))

        if self._error:
            err = self._hint_font.render(self._error, True, (255, 110, 110))
            surface.blit(err, (470, 560))

    def handle_server_message(self, msg: dict) -> None:
        t = msg.get("type")
        if t == "REGISTER_OK":
            self._error = "Registered. Now login."
        elif t == "AUTH_ERROR":
            e = msg.get("error")
            self._error = str(e) if e else "Auth error"
        elif t == "LOGIN_OK":
            self._error = None

    def _send_register(self) -> None:
        u = self._fields[0].value.strip()
        p = self._fields[1].value
        if not u or not p:
            self._error = "Username & Password required"
            return
        self._on_action({"action": "REGISTER", "payload": {"username": u, "password": p, "display_name": u}})

    def _send_login(self) -> None:
        u = self._fields[0].value.strip()
        p = self._fields[1].value
        if not u or not p:
            self._error = "Username & Password required"
            return
        self._on_action({"action": "LOGIN", "payload": {"username": u, "password": p}})
