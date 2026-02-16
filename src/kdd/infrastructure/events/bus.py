"""In-memory event bus.

Simple publish/subscribe for domain events.  Handlers are called
synchronously in registration order.  Implements ``EventBus`` port.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable


class InMemoryEventBus:
    """Synchronous in-memory event bus."""

    def __init__(self) -> None:
        self._handlers: dict[type, list[Callable[..., Any]]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Callable[..., Any]) -> None:
        """Register *handler* to be called when *event_type* is published."""
        self._handlers[event_type].append(handler)

    def publish(self, event: Any) -> None:
        """Dispatch *event* to all registered handlers for its type."""
        for handler in self._handlers.get(type(event), []):
            handler(event)
