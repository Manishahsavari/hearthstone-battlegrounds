from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Iterable, Iterator


@dataclass
class EventBus:
    server_queue: Deque[dict[str, Any]] = field(default_factory=deque)
    ui_queue: Deque[dict[str, Any]] = field(default_factory=deque)

    def post_to_server(self, event: dict) -> None:
        self.server_queue.append(event)

    def drain_server(self, max_events: int | None = None) -> Iterable[dict[str, Any]]:
        count = len(self.server_queue) if max_events is None else min(max_events, len(self.server_queue))
        for _ in range(count):
            yield self.server_queue.popleft()

    def post_to_ui(self, message: dict[str, Any]) -> None:
        self.ui_queue.append(message)

    def drain_ui(self, max_events: int | None = None) -> Iterator[dict[str, Any]]:
        count = len(self.ui_queue) if max_events is None else min(max_events, len(self.ui_queue))
        for _ in range(count):
            yield self.ui_queue.popleft()
