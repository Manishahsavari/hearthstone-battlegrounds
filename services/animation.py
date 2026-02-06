from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Animation:
    duration: float
    elapsed: float = 0.0

    def reset(self) -> None:
        self.elapsed = 0.0

    def update(self, dt: float) -> float:
        self.elapsed = min(self.duration, self.elapsed + dt)
        if self.duration <= 0:
            return 1.0
        return self.elapsed / self.duration

    def done(self) -> bool:
        return self.elapsed >= self.duration
