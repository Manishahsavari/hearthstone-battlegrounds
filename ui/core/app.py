from __future__ import annotations

import sys
import traceback
from dataclasses import dataclass, field

import pygame

from .event_bus import EventBus
from .net_client import NetworkClient
from .screen_manager import ScreenManager
from screens.login import LoginScreen
from screens.matchmaking import MatchmakingScreen
from screens.lobby import LobbyScreen
from screens.recruit_screen import make_recruit_screen
from screens.combat_viewer import CombatViewerScreen


DEFAULT_BG = (15, 15, 25)


@dataclass
class AppConfig:
    width: int = 1280
    height: int = 720
    title: str = "Hearthstone Battlegrounds"
    fps: int = 60


@dataclass
class App:
    config: AppConfig = field(default_factory=AppConfig)
    event_bus: EventBus = field(default_factory=EventBus)
    screen_manager: ScreenManager = field(default_factory=ScreenManager)

    net: NetworkClient = field(init=False)

    _screen: pygame.Surface | None = field(init=False, default=None)
    _clock: pygame.time.Clock | None = field(init=False, default=None)
    _running: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        pygame.init()
        self._screen = pygame.display.set_mode((self.config.width, self.config.height))
        pygame.display.set_caption(self.config.title)
        self._clock = pygame.time.Clock()
        self.net = NetworkClient(self.event_bus)
        self.net.start()
        self._register_default_screens()

    def _register_default_screens(self) -> None:
        login = LoginScreen(
            on_action=self.event_bus.post_to_server,
            set_screen=self.screen_manager.set_active,
        )
        self.screen_manager.register("login", login, activate=True)

        mm = MatchmakingScreen(set_screen=self.screen_manager.set_active)
        self.screen_manager.register("matchmaking", mm, activate=False)

        lobby = LobbyScreen(
            on_action=self.event_bus.post_to_server,
            set_screen=self.screen_manager.set_active,
        )
        self.screen_manager.register("lobby", lobby, activate=False)

        recruit = make_recruit_screen(
            self.event_bus.post_to_server,
            set_screen=self.screen_manager.set_active,
        )
        self.screen_manager.register("recruit", recruit, activate=False)

        combat = CombatViewerScreen(
            self.event_bus.post_to_server,
            set_screen=self.screen_manager.set_active,
        )
        self.screen_manager.register("combat_viewer", combat, activate=False)

    def run(self) -> None:
        if self._screen is None or self._clock is None:
            raise RuntimeError("App was not initialized correctly.")

        self._running = True

        try:
            while self._running:
                dt_ms = self._clock.tick(self.config.fps)
                dt = dt_ms / 1000.0

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self._running = False
                    else:
                        try:
                            self.screen_manager.handle_event(event)
                        except Exception:
                            print("\n[client] EXCEPTION in handle_event:\n", flush=True)
                            traceback.print_exc()
                            self._running = False
                            break

                try:
                    for msg in self.event_bus.drain_ui(200):
                        if msg.get("type") == "LOGIN_OK":
                            payload = msg.get("payload") or {}
                            token = payload.get("token")
                            if isinstance(token, str) and token:
                                self.net.set_token(token)
                                self.screen_manager.set_active("matchmaking")

                        try:
                            self.screen_manager.handle_server_message(msg)
                        except Exception:
                            print("\n[client] EXCEPTION in handle_server_message:\n", flush=True)
                            print("[client] msg =", msg, flush=True)
                            traceback.print_exc()
                            self._running = False
                            break
                except Exception:
                    print("\n[client] EXCEPTION while draining ui queue:\n", flush=True)
                    traceback.print_exc()
                    self._running = False

                try:
                    self.screen_manager.update(dt)
                except Exception:
                    print("\n[client] EXCEPTION in update:\n", flush=True)
                    traceback.print_exc()
                    self._running = False

                try:
                    self._screen.fill(DEFAULT_BG)
                    self.screen_manager.render(self._screen)
                    pygame.display.flip()
                except Exception:
                    print("\n[client] EXCEPTION in render/flip:\n", flush=True)
                    traceback.print_exc()
                    self._running = False

        finally:
            try:
                self.net.stop()
            except Exception:
                pass
            try:
                pygame.quit()
            except Exception:
                pass
            return


def main() -> None:
    app = App()
    app.run()


if __name__ == "__main__":
    main()
