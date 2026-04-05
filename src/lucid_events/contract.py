from abc import ABC, abstractmethod
from typing import Any, Callable


class DispatcherContract(ABC):

    @abstractmethod
    def listen(
        self,
        event_type: type,
        listener: Callable | type | None = None,
        priority: int = 0,
    ) -> Any: ...

    @abstractmethod
    def dispatch(self, event: Any) -> Any: ...

    @abstractmethod
    async def dispatch_async(self, event: Any) -> Any: ...

    @abstractmethod
    def subscribe(self, subscriber: Any) -> None: ...

    @abstractmethod
    def has_listeners(self, event_type: type) -> bool: ...

    @abstractmethod
    def forget(self, event_type: type, listener: Callable | None = None) -> None: ...

    @abstractmethod
    def flush(self) -> None: ...
