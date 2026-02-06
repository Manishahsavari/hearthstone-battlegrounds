from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Iterable, List


@dataclass
class EventBus:
    """
    Lightweight in-process event bus.

    For now it just queues dictionaries for server/UI channels so the UI can
    send actions without blocking. This is intentionally small but expandable.
    """

    _to_server: Deque[Dict] = field(default_factory=deque)
    _to_ui: Deque[Dict] = field(default_factory=deque)

    def post_to_server(self, payload: Dict) -> None:
        self._to_server.append(payload)

    def post_to_ui(self, payload: Dict) -> None:
        self._to_ui.append(payload)

    def drain_server(self, max_events: int = 5) -> List[Dict]:
        return _drain(self._to_server, max_events)

    def drain_ui(self, max_events: int = 5) -> List[Dict]:
        return _drain(self._to_ui, max_events)


def _drain(queue: Deque[Dict], max_events: int) -> List[Dict]:
    pulled: List[Dict] = []
    for _ in range(min(max_events, len(queue))):
        pulled.append(queue.popleft())
    return pulled
