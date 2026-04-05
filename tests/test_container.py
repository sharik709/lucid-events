from lucid_events import Dispatcher, Event, Listener, Subscriber


class UserRegistered(Event):
    def __init__(self, user_id: int):
        self.user_id = user_id


class MockContainer:
    def __init__(self, bindings: dict):
        self._bindings = bindings

    def make(self, cls):
        return self._bindings[cls]()


def test_container_resolves_listener_class():
    calls = []

    class MyListener(Listener):
        def handle(self, event):
            calls.append(event.user_id)

    container = MockContainer({MyListener: MyListener})
    d = Dispatcher(container=container)
    d.listen(UserRegistered, MyListener)
    d.dispatch(UserRegistered(7))
    assert calls == [7]


def test_container_autowires_dependencies():
    resolved_deps = []

    class MailService:
        pass

    mail = MailService()

    class WelcomeListener(Listener):
        def __init__(self, mailer: MailService):
            self.mailer = mailer

        def handle(self, event):
            resolved_deps.append(self.mailer)

    class Container:
        def make(self, cls):
            return cls(mail)

    d = Dispatcher(container=Container())
    d.listen(UserRegistered, WelcomeListener)
    d.dispatch(UserRegistered(1))
    assert resolved_deps == [mail]


def test_container_autowires_subscriber():
    received = []

    class LogService:
        pass

    log = LogService()

    class AuditSubscriber(Subscriber):
        def __init__(self, logger: LogService):
            self.logger = logger

        def subscribe(self, dispatcher):
            dispatcher.listen(UserRegistered, self.on_register)

        def on_register(self, event):
            received.append(self.logger)

    class Container:
        def make(self, cls):
            return cls(log)

    d = Dispatcher(container=Container())
    d.subscribe(AuditSubscriber)
    d.dispatch(UserRegistered(1))
    assert received == [log]


def test_without_container_listener_uses_no_arg():
    calls = []

    class SimpleListener(Listener):
        def handle(self, event):
            calls.append(event.user_id)

    d = Dispatcher()
    d.listen(UserRegistered, SimpleListener)
    d.dispatch(UserRegistered(5))
    assert calls == [5]


def test_listener_resolved_per_dispatch_not_cached():
    instances: list = []

    class TrackListener(Listener):
        def __init__(self):
            instances.append(self)  # keep strong refs so ids don't collide

        def handle(self, event):
            pass

    d = Dispatcher()
    d.listen(UserRegistered, TrackListener)
    d.dispatch(UserRegistered(1))
    d.dispatch(UserRegistered(2))
    d.dispatch(UserRegistered(3))
    assert len(instances) == 3
    assert instances[0] is not instances[1]
    assert instances[1] is not instances[2]
