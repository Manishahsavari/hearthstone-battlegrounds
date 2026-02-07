from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable

import pygame


@dataclass
class _Particle:
    x: float
    y: float
    vx: float
    vy: float
    r: float


class MatchmakingScreen:
    def __init__(self, set_screen: Callable[[str], None]) -> None:
        self._set_screen = set_screen
        self._title_font = pygame.font.SysFont("Arial", 36, bold=True)
        self._font = pygame.font.SysFont("Arial", 18)
        self._t = 0.0
        self._progress = 0.0
        self._current = 1
        self._target = 4
        self._phase = "MATCHMAKING"

        self._rng = random.Random(1337)
        self._particles: list[_Particle] = []
        for _ in range(80):
            self._particles.append(
                _Particle(
                    x=self._rng.uniform(0, 1280),
                    y=self._rng.uniform(0, 720),
                    vx=self._rng.uniform(-28, 28),
                    vy=self._rng.uniform(-28, 28),
                    r=self._rng.uniform(1.5, 3.2),
                )
            )

    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    def update(self, dt: float) -> None:
        self._t += dt
        w, h = 1280, 720

        for p in self._particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            if p.x < -10:
                p.x = w + 10
            if p.x > w + 10:
                p.x = -10
            if p.y < -10:
                p.y = h + 10
            if p.y > h + 10:
                p.y = -10

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((8, 10, 18))

        for p in self._particles:
            pygame.draw.circle(surface, (70, 90, 130), (int(p.x), int(p.y)), int(p.r))

        cx, cy = 640, 330
        pulse = 1.0 + 0.06 * math.sin(self._t * 2.2)
        ring_r = int(95 * pulse)
        ring_w = 6 + int(2 * (1 + math.sin(self._t * 3.0)))

        pygame.draw.circle(surface, (60, 120, 200), (cx, cy), ring_r, ring_w)
        pygame.draw.circle(surface, (25, 35, 55), (cx, cy), 70, 0)

        angle = self._t * 2.8
        for i in range(12):
            a = angle + i * (math.tau / 12)
            x = cx + math.cos(a) * 78
            y = cy + math.sin(a) * 78
            s = 3 + int(3 * (0.5 + 0.5 * math.sin(a * 2)))
            pygame.draw.circle(surface, (120, 180, 255), (int(x), int(y)), s)

        title = self._title_font.render("Finding opponents", True, (245, 245, 245))
        surface.blit(title, (460, 140))

        dots = "." * int((self._t * 2) % 4)
        sub = self._font.render(f"{self._current}/{self._target} players found{dots}", True, (190, 190, 210))
        surface.blit(sub, (520, 200))

        bar = pygame.Rect(420, 520, 440, 14)
        pygame.draw.rect(surface, (22, 26, 40), bar, border_radius=8)
        fill = pygame.Rect(bar.x, bar.y, int(bar.w * max(0.0, min(1.0, self._progress))), bar.h)
        pygame.draw.rect(surface, (90, 160, 255), fill, border_radius=8)

        hint = self._font.render("Matchmaking in progress…", True, (160, 160, 180))
        surface.blit(hint, (535, 550))

    def handle_server_message(self, msg: dict) -> None:
        t = msg.get("type")
        if t == "MATCHMAKING_STATUS":
            payload = msg.get("payload") or {}
            pr = payload.get("progress")
            cur = payload.get("current")
            tgt = payload.get("target")
            ph = payload.get("phase")
            if isinstance(pr, (int, float)):
                self._progress = float(pr)
            if isinstance(cur, int):
                self._current = cur
            if isinstance(tgt, int):
                self._target = tgt
            if isinstance(ph, str):
                self._phase = ph

        if t == "LOBBY_UPDATE":
            payload = msg.get("payload") or {}
            ph = payload.get("phase")
            if ph == "LOBBY":
                self._set_screen("lobby")
