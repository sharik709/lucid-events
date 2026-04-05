from lucid_events import Dispatcher, Event


class UserRegistered(Event):
    pass


class OrderCompleted(Event):
    pass


def test_listen_any_fires_for_every_event():
    d = Dispatcher()
    received = []

    @d.listen_any()
    def catch_all(event):
        received.append(type(event).__name__)

    d.dispatch(UserRegistered())
    d.dispatch(OrderCompleted())
    assert "UserRegistered" in received
    assert "OrderCompleted" in received


def test_listen_any_receives_event_object():
    d = Dispatcher()
    received = []

    @d.listen_any()
    def catch_all(event):
        received.append(event)

    event = UserRegistered()
    d.dispatch(event)
    assert received[0] is event


def test_listen_any_with_priority():
    d = Dispatcher()
    order = []

    @d.listen_any(priority=10)
    def high(event):
        order.append("high")

    @d.listen_any(priority=0)
    def low(event):
        order.append("low")

    d.dispatch(UserRegistered())
    assert order == ["high", "low"]


def test_multiple_wildcard_listeners_fire_in_priority_order():
    d = Dispatcher()
    order = []

    @d.listen_any(priority=5)
    def mid(event):
        order.append("mid")

    @d.listen_any(priority=20)
    def top(event):
        order.append("top")

    @d.listen_any(priority=-1)
    def bottom(event):
        order.append("bottom")

    d.dispatch(UserRegistered())
    assert order == ["top", "mid", "bottom"]


def test_wildcard_fires_after_type_specific_at_same_priority():
    d = Dispatcher()
    order = []

    @d.listen_any(priority=0)
    def wildcard(event):
        order.append("wildcard")

    @d.listen(UserRegistered, priority=0)
    def specific(event):
        order.append("specific")

    d.dispatch(UserRegistered())
    assert order == ["specific", "wildcard"]


def test_type_specific_stop_does_not_affect_wildcard():
    d = Dispatcher()
    wildcard_calls = []

    @d.listen(UserRegistered, priority=10)
    def stopper(event):
        return False

    @d.listen_any()
    def catch_all(event):
        wildcard_calls.append(event)

    d.dispatch(UserRegistered())
    assert len(wildcard_calls) == 1


def test_wildcard_returning_false_stops_other_wildcards():
    d = Dispatcher()
    calls = []

    @d.listen_any(priority=10)
    def first_wildcard(event):
        calls.append("first")
        return False

    @d.listen_any(priority=5)
    def second_wildcard(event):
        calls.append("second")

    d.dispatch(UserRegistered())
    assert calls == ["first"]


def test_wildcard_does_not_affect_other_event_type_specific_listeners():
    d = Dispatcher()
    order_calls = []

    @d.listen(OrderCompleted)
    def order_handler(event):
        order_calls.append(event)

    @d.listen_any(priority=10)
    def wildcard(event):
        return False  # stops wildcards but not specific listeners for OrderCompleted

    # Dispatch UserRegistered — wildcard stops, but OrderCompleted handler unaffected
    d.dispatch(UserRegistered())
    d.dispatch(OrderCompleted())
    assert len(order_calls) == 1
