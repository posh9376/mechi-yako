"""Event transport interface. In-process now; Azure Service Bus can implement EventSink later."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from threading import Condition
from typing import Any, Iterator, Protocol


class EventSink(Protocol):
    """Destination for replayed (or live) match events."""

    def publish(self, event: dict[str, Any]) -> None:
        """Publish one event dict (schema v1 event object)."""

    def close(self) -> None:
        """Signal end of stream."""


@dataclass
class InProcessEventQueue:
    """Thread-safe in-memory queue. Suitable for local demo and FastAPI SSE fan-out later."""

    maxsize: int | None = None
    _items: deque[dict[str, Any] | None] = field(default_factory=deque, init=False, repr=False)
    _cond: Condition = field(default_factory=Condition, init=False, repr=False)
    _closed: bool = field(default=False, init=False, repr=False)

    def publish(self, event: dict[str, Any]) -> None:
        with self._cond:
            if self._closed:
                raise RuntimeError("queue is closed")
            if self.maxsize is not None:
                while len(self._items) >= self.maxsize:
                    self._cond.wait(timeout=0.05)
            self._items.append(event)
            self._cond.notify_all()

    def close(self) -> None:
        with self._cond:
            self._closed = True
            self._items.append(None)  # sentinel
            self._cond.notify_all()

    def __iter__(self) -> Iterator[dict[str, Any]]:
        while True:
            with self._cond:
                while not self._items:
                    if self._closed:
                        return
                    self._cond.wait(timeout=0.05)
                item = self._items.popleft()
                self._cond.notify_all()
            if item is None:
                return
            yield item

    def drain(self) -> list[dict[str, Any]]:
        """Non-blocking snapshot of queued events (excludes sentinel)."""
        with self._cond:
            out = [x for x in self._items if x is not None]
            self._items.clear()
            return out
