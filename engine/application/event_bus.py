from __future__ import annotations

import contextlib
from collections import defaultdict
from collections.abc import Callable

from engine.domain.events import DomainEvent
from engine.domain.interfaces import IEventBus


class EventBus(IEventBus):
    """In-memory publish-subscribe event bus."""

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[Callable]] = defaultdict(list)

    def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(type(event), []):
            with contextlib.suppress(Exception):
                handler(event)

    def subscribe(self, event_type: type[DomainEvent], handler: Callable) -> None:
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: type[DomainEvent], handler: Callable) -> None:
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    def clear(self) -> None:
        self._handlers.clear()
