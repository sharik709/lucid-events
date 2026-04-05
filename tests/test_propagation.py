from lucid_events import Dispatcher, Event


class OrderCompleted(Event):
    def __init__(self):
        self.processed_by: list[str] = []


def test_return_false_stops_propagation():
    d = Dispatcher()
    calls = []

    d.listen(OrderCompleted, lambda e: calls.append("a") or False, priority=10)
    d.listen(OrderCompleted, lambda e: calls.append("b"), priority=5)
    d.dispatch(OrderCompleted())
    assert calls == ["a"]


def test_return_none_does_not_stop():
    d = Dispatcher()
    calls = []
    d.listen(OrderCompleted, lambda e: calls.append("a"), priority=10)
    d.listen(OrderCompleted, lambda e: calls.append("b"), priority=5)
    d.dispatch(OrderCompleted())
    assert calls == ["a", "b"]


def test_return_zero_does_not_stop():
    d = Dispatcher()
    calls = []
    d.listen(OrderCompleted, lambda e: 0, priority=10)
    d.listen(OrderCompleted, lambda e: calls.append("b"), priority=5)
    d.dispatch(OrderCompleted())
    assert "b" in calls


def test_return_empty_string_does_not_stop():
    d = Dispatcher()
    calls = []
    d.listen(OrderCompleted, lambda e: "", priority=10)
    d.listen(OrderCompleted, lambda e: calls.append("b"), priority=5)
    d.dispatch(OrderCompleted())
    assert "b" in calls


def test_return_true_does_not_stop():
    d = Dispatcher()
    calls = []
    d.listen(OrderCompleted, lambda e: True, priority=10)
    d.listen(OrderCompleted, lambda e: calls.append("b"), priority=5)
    d.dispatch(OrderCompleted())
    assert "b" in calls


def test_only_explicit_false_stops():
    d = Dispatcher()
    calls = []

    def stopper(e):
        return False

    d.listen(OrderCompleted, stopper, priority=10)
    d.listen(OrderCompleted, lambda e: calls.append("second"), priority=5)
    d.dispatch(OrderCompleted())
    assert calls == []


def test_higher_priority_can_block_lower():
    d = Dispatcher()
    calls = []
    d.listen(OrderCompleted, lambda e: False, priority=100)
    d.listen(OrderCompleted, lambda e: calls.append("blocked"), priority=50)
    d.listen(OrderCompleted, lambda e: calls.append("also_blocked"), priority=0)
    d.dispatch(OrderCompleted())
    assert calls == []


def test_stopped_event_is_still_returned():
    d = Dispatcher()
    d.listen(OrderCompleted, lambda e: False, priority=10)
    event = OrderCompleted()
    result = d.dispatch(event)
    assert result is event
