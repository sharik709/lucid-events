from typing import Any


class Listener:
    """Base class for listener objects with dependencies."""

    queued: bool = False

    def handle(self, event: Any) -> Any:
        raise NotImplementedError
