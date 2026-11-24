from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class StageTimer:
    """Wall-clock stage timings via time.perf_counter (milliseconds)."""

    stages_ms: dict[str, float] = field(default_factory=dict)
    _t0: float = field(default_factory=time.perf_counter)

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            self.stages_ms[name] = round((time.perf_counter() - start) * 1000.0, 3)

    def total_ms(self) -> float:
        return round((time.perf_counter() - self._t0) * 1000.0, 3)

    def as_dict(self) -> dict[str, float]:
        return dict(self.stages_ms)
