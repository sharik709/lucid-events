from lucid_events import Dispatcher, Event


class UserRegistered(Event):
    pass


class OrderCompleted(Event):
    pass


def test_forget_specific_listener():
    d = Dispatcher()
    calls = []

    def to_remove(e):
        calls.append("to_remove")

    def to_keep(e):
        calls.append("to_keep")

    d.listen(UserRegistered, to_remove)
    d.listen(UserRegistered, to_keep)
    d.forget(UserRegistered, to_remove)
    d.dispatch(UserRegistered())
    assert calls == ["to_keep"]


def test_forget_all_listeners_for_event():
    d = Dispatcher()
    calls = []
    d.listen(UserRegistered, lambda e: calls.append(1))
    d.listen(UserRegistered, lambda e: calls.append(2))
    d.forget(UserRegistered)
    d.dispatch(UserRegistered())
    assert calls == []


def test_forget_unregistered_event_is_noop():
    d = Dispatcher()
    d.forget(UserRegistered)  # No error


def test_flush_removes_all_listeners():
    d = Dispatcher()
    calls = []
    d.listen(UserRegistered, lambda e: calls.append("user"))
    d.listen(OrderCompleted, lambda e: calls.append("order"))
    d.flush()
    d.dispatch(UserRegistered())
    d.dispatch(OrderCompleted())
    assert calls == []


def test_flush_removes_wildcard_listeners():
    d = Dispatcher()
    calls = []

    @d.listen_any()
    def catch_all(event):
        calls.append(event)

    d.flush()
    d.dispatch(UserRegistered())
    assert calls == []


def test_after_forget_dispatch_no_longer_calls_removed():
    d = Dispatcher()
    calls = []

    def handler(e):
        calls.append("called")

    d.listen(UserRegistered, handler)
    d.forget(UserRegistered, handler)
    d.dispatch(UserRegistered())
    assert calls == []


def test_has_listeners_false_after_all_forgotten():
    d = Dispatcher()

    def h(e): pass

    d.listen(UserRegistered, h)
    d.forget(UserRegistered, h)
    assert not d.has_listeners(UserRegistered)


def test_get_listeners_empty_for_unknown_event():
    d = Dispatcher()
    assert d.get_listeners(UserRegistered) == []
