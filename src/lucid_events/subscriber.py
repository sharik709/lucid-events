from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lucid_events.dispatcher import Dispatcher


class Subscriber:
    """Base class for event subscribers that register multiple listeners at once."""

    def subscribe(self, dispatcher: "Dispatcher") -> None:
        raise NotImplementedError
