import pytest
from lucid_events import Dispatcher, Event


class EmptyEvent(Event):
    pass


class PlainObject:
    value = 42


def test_empty_event_dispatches_fine():
    d = Dispatcher()
    calls = []
    d.listen(EmptyEvent, lambda e: calls.append(True))
    d.dispatch(EmptyEvent())
    assert calls == [True]


def test_non_event_subclass_works():
    d = Dispatcher()
    calls = []
    d.listen(PlainObject, lambda e: calls.append(e.value))
    obj = PlainObject()
    d.dispatch(obj)
    assert calls == [42]


def test_listener_exception_propagates():
    d = Dispatcher()

    def broken(e):
        raise ValueError("boom")

    d.listen(EmptyEvent, broken)
    with pytest.raises(ValueError, match="boom"):
        d.dispatch(EmptyEvent())


def test_listener_exception_stops_remaining_listeners():
    d = Dispatcher()
    calls = []

    def broken(e):
        raise RuntimeError("stop")

    d.listen(EmptyEvent, broken, priority=10)
    d.listen(EmptyEvent, lambda e: calls.append("after"), priority=5)

    with pytest.raises(RuntimeError):
        d.dispatch(EmptyEvent())

    assert calls == []


def test_register_for_never_dispatched_type():
    d = Dispatcher()
    d.listen(EmptyEvent, lambda e: None)
    # Just registering, never dispatching — no error


def test_has_listeners_false_for_unknown_event():
    d = Dispatcher()
    assert not d.has_listeners(EmptyEvent)


def test_get_listeners_empty_for_unknown_event():
    d = Dispatcher()
    assert d.get_listeners(EmptyEvent) == []


def test_large_number_of_listeners():
    d = Dispatcher()
    calls = []
    count = 1000
    for _ in range(count):
        d.listen(EmptyEvent, lambda e: calls.append(1))
    d.dispatch(EmptyEvent())
    assert len(calls) == count


def test_recursive_dispatch():
    d = Dispatcher()
    depth = []

    class InnerEvent(Event):
        pass

    inner_calls = []
    d.listen(InnerEvent, lambda e: inner_calls.append(True))

    def outer_handler(e):
        depth.append(1)
        d.dispatch(InnerEvent())

    d.listen(EmptyEvent, outer_handler)
    d.dispatch(EmptyEvent())
    assert len(depth) == 1
    assert inner_calls == [True]


def test_same_function_multiple_event_types():
    d = Dispatcher()
    calls = []

    def handler(e):
        calls.append(type(e).__name__)

    d.listen(EmptyEvent, handler)
    d.listen(PlainObject, handler)
    d.dispatch(EmptyEvent())
    d.dispatch(PlainObject())
    assert calls == ["EmptyEvent", "PlainObject"]


def test_lambda_as_listener():
    d = Dispatcher()
    calls = []
    d.listen(EmptyEvent, lambda e: calls.append("lambda"))
    d.dispatch(EmptyEvent())
    assert calls == ["lambda"]
