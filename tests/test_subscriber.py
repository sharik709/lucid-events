import pytest
from lucid_events import Dispatcher, Event, Subscriber


class UserRegistered(Event):
    def __init__(self, user_id: int):
        self.user_id = user_id


class UserDeleted(Event):
    def __init__(self, user_id: int):
        self.user_id = user_id


class PasswordChanged(Event):
    def __init__(self, user_id: int):
        self.user_id = user_id


class UserSubscriber(Subscriber):
    def __init__(self):
        self.registered_events: list = []
        self.deleted_events: list = []

    def subscribe(self, dispatcher: Dispatcher) -> None:
        dispatcher.listen(UserRegistered, self.on_registered)
        dispatcher.listen(UserDeleted, self.on_deleted)

    def on_registered(self, event: UserRegistered):
        self.registered_events.append(event)

    def on_deleted(self, event: UserDeleted):
        self.deleted_events.append(event)


class PrioritySubscriber(Subscriber):
    def __init__(self):
        self.order: list[str] = []

    def subscribe(self, dispatcher: Dispatcher) -> None:
        dispatcher.listen(PasswordChanged, self.low, priority=0)
        dispatcher.listen(PasswordChanged, self.high, priority=10)

    def low(self, event: PasswordChanged):
        self.order.append("low")

    def high(self, event: PasswordChanged):
        self.order.append("high")


def test_subscribe_calls_subscribe_method():
    d = Dispatcher()
    sub = UserSubscriber()
    d.subscribe(sub)
    assert d.has_listeners(UserRegistered)
    assert d.has_listeners(UserDeleted)


def test_subscriber_methods_registered_as_listeners():
    d = Dispatcher()
    sub = UserSubscriber()
    d.subscribe(sub)
    event = UserRegistered(1)
    d.dispatch(event)
    assert sub.registered_events == [event]


def test_subscriber_multiple_event_types():
    d = Dispatcher()
    sub = UserSubscriber()
    d.subscribe(sub)
    reg = UserRegistered(1)
    dele = UserDeleted(2)
    d.dispatch(reg)
    d.dispatch(dele)
    assert sub.registered_events == [reg]
    assert sub.deleted_events == [dele]


def test_subscriber_registered_as_class():
    d = Dispatcher()
    d.subscribe(UserSubscriber)
    assert d.has_listeners(UserRegistered)
    assert d.has_listeners(UserDeleted)


def test_subscriber_class_autowired_via_container():
    received_dep = []

    class ServiceDep:
        pass

    class AutowiredSubscriber(Subscriber):
        def __init__(self, dep: ServiceDep):
            self.dep = dep

        def subscribe(self, dispatcher: Dispatcher) -> None:
            dispatcher.listen(UserRegistered, self.on_reg)

        def on_reg(self, event):
            received_dep.append(self.dep)

    dep_instance = ServiceDep()

    class MockContainer:
        def make(self, cls):
            return cls(dep_instance)

    d = Dispatcher(container=MockContainer())
    d.subscribe(AutowiredSubscriber)
    d.dispatch(UserRegistered(1))
    assert received_dep == [dep_instance]


def test_subscriber_priorities():
    d = Dispatcher()
    sub = PrioritySubscriber()
    d.subscribe(sub)
    d.dispatch(PasswordChanged(1))
    assert sub.order == ["high", "low"]


def test_subscriber_instance_retained():
    """Subscriber should not be garbage collected after registration."""
    import gc

    d = Dispatcher()
    d.subscribe(UserSubscriber)
    gc.collect()
    event = UserRegistered(1)
    d.dispatch(event)
    # If subscriber was GC'd, bound methods would fail
