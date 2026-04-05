from lucid_events import Dispatcher, Event


class ValidateOrder(Event):
    def __init__(self, order_id: int):
        self.order_id = order_id
        self.is_valid = True
        self.errors: list[str] = []


def test_listener_can_modify_event():
    d = Dispatcher()

    @d.listen(ValidateOrder)
    def invalidate(event):
        event.is_valid = False

    event = d.dispatch(ValidateOrder(1))
    assert event.is_valid is False


def test_subsequent_listeners_see_mutations():
    d = Dispatcher()

    @d.listen(ValidateOrder, priority=100)
    def first(event):
        event.errors.append("first_error")

    @d.listen(ValidateOrder, priority=50)
    def second(event):
        assert "first_error" in event.errors
        event.errors.append("second_error")

    event = d.dispatch(ValidateOrder(1))
    assert event.errors == ["first_error", "second_error"]


def test_dispatch_returns_mutated_event():
    d = Dispatcher()

    @d.listen(ValidateOrder)
    def handler(event):
        event.is_valid = False
        event.errors.append("failed")

    result = d.dispatch(ValidateOrder(1))
    assert result.is_valid is False
    assert result.errors == ["failed"]


def test_multiple_listeners_mutate_same_field_last_writer_wins():
    d = Dispatcher()

    @d.listen(ValidateOrder, priority=10)
    def first(event):
        event.order_id = 999

    @d.listen(ValidateOrder, priority=5)
    def second(event):
        event.order_id = 42

    event = d.dispatch(ValidateOrder(1))
    assert event.order_id == 42
