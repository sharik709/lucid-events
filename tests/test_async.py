import pytest
from lucid_events import AsyncListener, Dispatcher, Event, Listener, Subscriber


class OrderCompleted(Event):
    def __init__(self, order_id: int):
        self.order_id = order_id


class PaymentReceived(Event):
    pass


async def test_async_function_listener_awaited():
    d = Dispatcher()
    calls = []

    @d.listen(OrderCompleted)
    async def handler(event):
        calls.append(event.order_id)

    await d.dispatch_async(OrderCompleted(1))
    assert calls == [1]


async def test_async_listener_class_handle_awaited():
    class MyAsyncListener(AsyncListener):
        calls = []

        async def handle(self, event):
            MyAsyncListener.calls.append(event)

    MyAsyncListener.calls = []
    d = Dispatcher()
    d.listen(OrderCompleted, MyAsyncListener())
    event = OrderCompleted(2)
    await d.dispatch_async(event)
    assert MyAsyncListener.calls == [event]


async def test_mixed_sync_and_async_listeners():
    d = Dispatcher()
    order = []

    d.listen(OrderCompleted, lambda e: order.append("sync"), priority=10)

    @d.listen(OrderCompleted)
    async def async_handler(event):
        order.append("async")

    await d.dispatch_async(OrderCompleted(1))
    assert "sync" in order
    assert "async" in order


def test_sync_dispatch_raises_for_async_listener():
    d = Dispatcher()

    @d.listen(OrderCompleted)
    async def handler(event):
        pass

    with pytest.raises(TypeError):
        d.dispatch(OrderCompleted(1))


def test_sync_dispatch_raises_for_async_listener_class():
    class MyAsync(AsyncListener):
        async def handle(self, event):
            pass

    d = Dispatcher()
    d.listen(OrderCompleted, MyAsync())

    with pytest.raises(TypeError):
        d.dispatch(OrderCompleted(1))


async def test_async_listener_can_stop_propagation():
    d = Dispatcher()
    calls = []

    @d.listen(OrderCompleted, priority=10)
    async def stopper(event):
        calls.append("stopper")
        return False

    @d.listen(OrderCompleted, priority=5)
    async def second(event):
        calls.append("second")

    await d.dispatch_async(OrderCompleted(1))
    assert calls == ["stopper"]


async def test_async_subscriber_methods():
    class AsyncSub(Subscriber):
        def __init__(self):
            self.calls: list = []

        def subscribe(self, dispatcher: Dispatcher) -> None:
            dispatcher.listen(PaymentReceived, self.on_payment)

        async def on_payment(self, event):
            self.calls.append(event)

    d = Dispatcher()
    sub = AsyncSub()
    d.subscribe(sub)
    event = PaymentReceived()
    await d.dispatch_async(event)
    assert sub.calls == [event]


async def test_dispatch_async_returns_event():
    d = Dispatcher()

    @d.listen(OrderCompleted)
    async def handler(event):
        pass

    event = OrderCompleted(99)
    result = await d.dispatch_async(event)
    assert result is event
