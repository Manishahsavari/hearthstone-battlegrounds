from __future__ import annotations

import sys
from dataclasses import dataclass, field

import pygame

from .event_bus import EventBus
from .screen_manager import ScreenManager
from screens.recruit_screen import make_recruit_screen
from screens.combat_viewer import CombatViewerScreen
from screens.lobby import LobbyScreen


DEFAULT_BG = (15, 15, 25)


@dataclass
class AppConfig:
    width: int = 1280
    height: int = 720
    title: str = "Hearthstone Battlegrounds"
    fps: int = 60


@dataclass
class App:
    """
    Main pygame application.

    Responsibilities:
    - Initialize pygame window, clock, and global EventBus
    - Own a ScreenManager and forward events/update/render to it
    - Run the main loop until the window is closed
    """

    config: AppConfig = field(default_factory=AppConfig)
    event_bus: EventBus = field(default_factory=EventBus)
    screen_manager: ScreenManager = field(default_factory=ScreenManager)

    _screen: pygame.Surface | None = field(init=False, default=None)
    _clock: pygame.time.Clock | None = field(init=False, default=None)
    _running: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        pygame.init()
        self._screen = pygame.display.set_mode(
            (self.config.width, self.config.height)
        )
        pygame.display.set_caption(self.config.title)
        self._clock = pygame.time.Clock()
        self._register_default_screens()

    def _register_default_screens(self) -> None:
        # Screens
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

        # Lobby is the initial screen
        lobby = LobbyScreen(
            on_action=self.event_bus.post_to_server,
            set_screen=self.screen_manager.set_active,
        )
        self.screen_manager.register("lobby", lobby, activate=True)

    # Main loop ----------------------------------------------------------

    def run(self) -> None:
        if self._screen is None or self._clock is None:
            raise RuntimeError("App was not initialized correctly.")

        self._running = True

        while self._running:
            dt_ms = self._clock.tick(self.config.fps)
            dt = dt_ms / 1000.0

            # Input events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                else:
                    self.screen_manager.handle_event(event)

            # Server events could be pulled here and dispatched to screens
            # for message in self.event_bus.drain_ui(max_events=5):
            #     ...  # TODO: integrate with screens in later steps

            # Update & render
            self.screen_manager.update(dt)
            self._screen.fill(DEFAULT_BG)
            self.screen_manager.render(self._screen)
            pygame.display.flip()

        pygame.quit()
        sys.exit(0)


def main() -> None:
    app = App()
    app.run()


if __name__ == "__main__":
    main()

