from lucid_events import Dispatcher, Event


class UserRegistered(Event):
    pass


def test_higher_priority_runs_first():
    d = Dispatcher()
    order = []
    d.listen(UserRegistered, lambda e: order.append("low"), priority=0)
    d.listen(UserRegistered, lambda e: order.append("high"), priority=10)
    d.dispatch(UserRegistered())
    assert order == ["high", "low"]


def test_same_priority_preserves_insertion_order():
    d = Dispatcher()
    order = []
    d.listen(UserRegistered, lambda e: order.append(1), priority=0)
    d.listen(UserRegistered, lambda e: order.append(2), priority=0)
    d.listen(UserRegistered, lambda e: order.append(3), priority=0)
    d.dispatch(UserRegistered())
    assert order == [1, 2, 3]


def test_default_priority_is_zero():
    d = Dispatcher()
    order = []
    d.listen(UserRegistered, lambda e: order.append("default"))
    d.listen(UserRegistered, lambda e: order.append("explicit_zero"), priority=0)
    d.dispatch(UserRegistered())
    assert order == ["default", "explicit_zero"]


def test_negative_priority_runs_after_default():
    d = Dispatcher()
    order = []
    d.listen(UserRegistered, lambda e: order.append("neg"), priority=-1)
    d.listen(UserRegistered, lambda e: order.append("zero"), priority=0)
    d.dispatch(UserRegistered())
    assert order == ["zero", "neg"]


def test_priority_100_50_0_ordering():
    d = Dispatcher()
    order = []
    d.listen(UserRegistered, lambda e: order.append(0), priority=0)
    d.listen(UserRegistered, lambda e: order.append(100), priority=100)
    d.listen(UserRegistered, lambda e: order.append(50), priority=50)
    d.dispatch(UserRegistered())
    assert order == [100, 50, 0]


def test_get_listeners_sorted_by_priority():
    d = Dispatcher()

    def low(e): pass
    def high(e): pass

    d.listen(UserRegistered, low, priority=0)
    d.listen(UserRegistered, high, priority=10)
    listeners = d.get_listeners(UserRegistered)
    assert listeners == [high, low]
