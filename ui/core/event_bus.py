from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Iterable, List


@dataclass
class Event:
    type: str
    payload: dict


class EventBus:
    def __init__(self, max_server_events_per_frame: int = 5) -> None:
        self._server_queue: Deque[Event] = deque()
        self._ui_queue: Deque[Event] = deque()
        self._max_server_events_per_frame = max_server_events_per_frame

    def publish_server(self, event: Event) -> None:
        self._server_queue.append(event)

    def publish_ui(self, event: Event) -> None:
        self._ui_queue.append(event)

    def drain_server(self) -> List[Event]:
        events: List[Event] = []
        for _ in range(min(self._max_server_events_per_frame, len(self._server_queue))):
            events.append(self._server_queue.popleft())
        return events

    def drain_ui(self) -> Iterable[Event]:
        while self._ui_queue:
            yield self._ui_queue.popleft()
