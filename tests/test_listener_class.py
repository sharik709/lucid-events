import pytest
from lucid_events import Dispatcher, Event, Listener


class UserRegistered(Event):
    def __init__(self, user_id: int):
        self.user_id = user_id


class SimpleListener(Listener):
    def __init__(self):
        self.received = []

    def handle(self, event):
        self.received.append(event)


class DependencyListener(Listener):
    def __init__(self, service):
        self.service = service
        self.called_with = []

    def handle(self, event):
        self.called_with.append((self.service, event))


class NoArgListener(Listener):
    calls = []

    def handle(self, event):
        NoArgListener.calls.append(event)


def test_listener_handle_called_with_event():
    d = Dispatcher()
    listener = SimpleListener()
    d.listen(UserRegistered, listener)
    event = UserRegistered(1)
    d.dispatch(event)
    assert listener.received == [event]


def test_listener_with_dependencies_manual_instantiation():
    d = Dispatcher()
    service = object()
    listener = DependencyListener(service)
    d.listen(UserRegistered, listener)
    event = UserRegistered(2)
    d.dispatch(event)
    assert listener.called_with == [(service, event)]


def test_listener_class_without_container_uses_no_arg():
    NoArgListener.calls = []
    d = Dispatcher()
    d.listen(UserRegistered, NoArgListener)
    event = UserRegistered(3)
    d.dispatch(event)
    assert len(NoArgListener.calls) == 1
    assert NoArgListener.calls[0] is event


def test_listener_class_resolved_via_container():
    service = object()

    class MyListener(Listener):
        resolved_with = []

        def __init__(self, svc):
            self.svc = svc

        def handle(self, event):
            MyListener.resolved_with.append(self.svc)

    class MockContainer:
        def make(self, cls):
            return cls(service)

    d = Dispatcher(container=MockContainer())
    d.listen(UserRegistered, MyListener)
    d.dispatch(UserRegistered(4))
    assert MyListener.resolved_with == [service]


def test_listener_class_resolved_per_dispatch():
    """Each dispatch creates a new listener instance (not cached)."""
    instances = []

    class TrackingListener(Listener):
        def __init__(self):
            instances.append(self)

        def handle(self, event):
            pass

    d = Dispatcher()
    d.listen(UserRegistered, TrackingListener)
    d.dispatch(UserRegistered(1))
    d.dispatch(UserRegistered(2))
    assert len(instances) == 2
    assert instances[0] is not instances[1]
