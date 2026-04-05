import pytest
from lucid_events import Dispatcher, Event


class OrderCompleted(Event):
    def __init__(self, order_id: int):
        self.order_id = order_id


class PlainObject:
    pass


def test_dispatch_calls_all_listeners():
    d = Dispatcher()
    calls = []
    d.listen(OrderCompleted, lambda e: calls.append("a"))
    d.listen(OrderCompleted, lambda e: calls.append("b"))
    d.dispatch(OrderCompleted(1))
    assert calls == ["a", "b"]


def test_listener_receives_event():
    d = Dispatcher()
    received = []
    d.listen(OrderCompleted, lambda e: received.append(e))
    event = OrderCompleted(42)
    d.dispatch(event)
    assert received[0] is event


def test_dispatch_returns_event():
    d = Dispatcher()
    d.listen(OrderCompleted, lambda e: None)
    event = OrderCompleted(1)
    result = d.dispatch(event)
    assert result is event


def test_dispatch_no_listeners_does_not_raise():
    d = Dispatcher()
    d.dispatch(OrderCompleted(1))  # no error


def test_dispatch_non_event_object():
    d = Dispatcher()
    calls = []
    d.listen(PlainObject, lambda e: calls.append(e))
    obj = PlainObject()
    d.dispatch(obj)
    assert calls == [obj]


def test_dispatch_many():
    d = Dispatcher()
    received = []
    d.listen(OrderCompleted, lambda e: received.append(e.order_id))
    events = [OrderCompleted(1), OrderCompleted(2), OrderCompleted(3)]
    d.dispatch_many(events)
    assert received == [1, 2, 3]


def test_listen_as_decorator_registers_and_returns_fn():
    d = Dispatcher()
    calls = []

    @d.listen(OrderCompleted)
    def handler(event):
        calls.append(event.order_id)

    assert callable(handler)
    d.dispatch(OrderCompleted(7))
    assert calls == [7]


def test_multiple_listeners_all_fire():
    d = Dispatcher()
    results = []
    d.listen(OrderCompleted, lambda e: results.append(1))
    d.listen(OrderCompleted, lambda e: results.append(2))
    d.listen(OrderCompleted, lambda e: results.append(3))
    d.dispatch(OrderCompleted(1))
    assert results == [1, 2, 3]


def test_same_listener_registered_twice_fires_twice():
    d = Dispatcher()
    calls = []

    def handler(e):
        calls.append(1)

    d.listen(OrderCompleted, handler)
    d.listen(OrderCompleted, handler)
    d.dispatch(OrderCompleted(1))
    assert len(calls) == 2
