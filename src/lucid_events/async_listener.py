from typing import Any


class AsyncListener:
    """Base class for async listener objects."""

    queued: bool = False

    async def handle(self, event: Any) -> Any:
        raise NotImplementedError
