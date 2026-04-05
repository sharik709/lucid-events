import asyncio
import inspect
import logging
import warnings
from typing import Any, Callable

from lucid_events.async_listener import AsyncListener
from lucid_events.listener import Listener

logger = logging.getLogger(__name__)

_Entry = tuple[int, int, Any]  # (priority, insertion_order, listener)


class Dispatcher:
    def __init__(self, container: Any = None) -> None:
        self._listeners: dict[type, list[_Entry]] = {}
        self._wildcard_listeners: list[_Entry] = []
        self._container = container
        self._insertion_counter: int = 0
        self._subscribers: list[Any] = []

    # ------------------------------------------------------------------ #
    # Registration
    # ------------------------------------------------------------------ #

    def listen(
        self,
        event_type: type,
        listener: Any = None,
        priority: int = 0,
    ) -> Any:
        """Register a listener for an event type. Usable as a decorator or called directly."""
        if listener is None:
            def decorator(fn: Any) -> Any:
                self._register(event_type, fn, priority)
                return fn
            return decorator
        self._register(event_type, listener, priority)
        return listener

    def _register(self, event_type: type, listener: Any, priority: int) -> None:
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append((priority, self._insertion_counter, listener))
        self._insertion_counter += 1

    def listen_any(self, priority: int = 0) -> Callable:
        """Register a wildcard listener that fires for every event."""
        def decorator(fn: Any) -> Any:
            self._wildcard_listeners.append((priority, self._insertion_counter, fn))
            self._insertion_counter += 1
            return fn
        return decorator

    def subscribe(self, subscriber: Any) -> None:
        """Register a subscriber (instance or class)."""
        if isinstance(subscriber, type):
            instance = self._container.make(subscriber) if self._container else subscriber()
        else:
            instance = subscriber
        self._subscribers.append(instance)
        instance.subscribe(self)

    # ------------------------------------------------------------------ #
    # Dispatch
    # ------------------------------------------------------------------ #

    def dispatch(self, event: Any) -> Any:
        """Dispatch an event synchronously. Raises TypeError if an async listener is encountered."""
        for _, _, listener in self._sorted_listeners(type(event)):
            result = self._call_sync(listener, event)
            if result is False:
                break

        for _, _, listener in self._sorted_wildcard_listeners():
            result = self._call_sync(listener, event)
            if result is False:
                break

        return event

    async def dispatch_async(self, event: Any) -> Any:
        """Dispatch an event, awaiting async listeners."""
        for _, _, listener in self._sorted_listeners(type(event)):
            result = await self._call_async(listener, event)
            if result is False:
                break

        for _, _, listener in self._sorted_wildcard_listeners():
            result = await self._call_async(listener, event)
            if result is False:
                break

        return event

    def dispatch_many(self, events: list[Any]) -> None:
        """Dispatch multiple events in sequence."""
        for event in events:
            self.dispatch(event)

    # ------------------------------------------------------------------ #
    # Query
    # ------------------------------------------------------------------ #

    def has_listeners(self, event_type: type) -> bool:
        return bool(self._listeners.get(event_type))

    def get_listeners(self, event_type: type) -> list[Any]:
        return [listener for _, _, listener in self._sorted_listeners(event_type)]

    # ------------------------------------------------------------------ #
    # Removal
    # ------------------------------------------------------------------ #

    def forget(self, event_type: type, listener: Any = None) -> None:
        """Remove a specific listener, or all listeners for an event type."""
        if event_type not in self._listeners:
            return
        if listener is None:
            del self._listeners[event_type]
        else:
            self._listeners[event_type] = [
                entry for entry in self._listeners[event_type] if entry[2] is not listener
            ]
            if not self._listeners[event_type]:
                del self._listeners[event_type]

    def flush(self) -> None:
        """Remove all listeners for all events, including wildcards."""
        self._listeners.clear()
        self._wildcard_listeners.clear()

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _sorted_listeners(self, event_type: type) -> list[_Entry]:
        entries = self._listeners.get(event_type, [])
        return sorted(entries, key=lambda e: (-e[0], e[1]))

    def _sorted_wildcard_listeners(self) -> list[_Entry]:
        return sorted(self._wildcard_listeners, key=lambda e: (-e[0], e[1]))

    def _resolve_listener(self, listener: Any) -> Any:
        """Instantiate listener classes; return callables as-is."""
        if isinstance(listener, type):
            if self._container:
                return self._container.make(listener)
            return listener()
        return listener

    def _call_sync(self, listener: Any, event: Any) -> Any:
        resolved = self._resolve_listener(listener)

        if isinstance(resolved, AsyncListener):
            raise TypeError(
                f"Async listener {type(resolved).__name__}.handle() must be dispatched "
                "with dispatch_async()"
            )
        if inspect.iscoroutinefunction(resolved):
            raise TypeError(
                f"Async listener {resolved!r} must be dispatched with dispatch_async()"
            )

        if isinstance(resolved, Listener):
            if resolved.queued:
                warnings.warn(
                    f"{type(resolved).__name__} has queued=True but lucid-queue is not "
                    "installed; running synchronously.",
                    stacklevel=3,
                )
            return resolved.handle(event)

        return resolved(event)

    async def _call_async(self, listener: Any, event: Any) -> Any:
        resolved = self._resolve_listener(listener)

        if isinstance(resolved, AsyncListener):
            return await resolved.handle(event)
        if inspect.iscoroutinefunction(resolved):
            return await resolved(event)
        if isinstance(resolved, Listener):
            return resolved.handle(event)
        return resolved(event)
