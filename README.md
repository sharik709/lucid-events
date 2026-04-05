# Lucid Events

**Fire events, not imports. Decouple your services with a clean event dispatcher that wires listeners through the container.**

Your `OrderService` shouldn't know that emails get sent, caches get warmed, analytics get tracked, and Slack gets pinged after a successful checkout. It should fire `OrderCompleted` and move on. Lucid Events gives Python a proper event dispatcher — typed event objects, prioritized listeners, subscriber classes, async support, and deep integration with Lucid Container so listeners get their dependencies autowired.

[![PyPI version](https://badge.fury.io/py/lucid-events.svg)](https://pypi.org/project/lucid-events/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Before & After

**Without Lucid Events:**

```python
class OrderService:
    def __init__(
        self,
        repo: OrderRepository,
        mailer: MailerContract,
        cache: CacheContract,
        analytics: AnalyticsClient,
        logger: LoggerContract,
        slack: SlackNotifier,
    ):
        self.repo = repo
        self.mailer = mailer
        self.cache = cache
        self.analytics = analytics
        self.logger = logger
        self.slack = slack

    def complete(self, order: Order):
        self.repo.save(order)
        self.mailer.send(order.user.email, "Order confirmed", ...)
        self.cache.forget(f"user:{order.user_id}:orders")
        self.analytics.track("order_completed", {"total": order.total})
        self.logger.info(f"Order {order.id} completed")
        self.slack.notify(f"New order #{order.id} — ${order.total}")
        # Every new side effect = another dependency, another line here
```

**With Lucid Events:**

```python
class OrderService:
    def __init__(self, repo: OrderRepository, events: EventDispatcher):
        self.repo = repo
        self.events = events

    def complete(self, order: Order):
        self.repo.save(order)
        self.events.dispatch(OrderCompleted(order))
        # That's it. Listeners handle everything else.
```

---

## Installation

```bash
pip install lucid-events
```

Requires Python 3.10 or higher. No dependencies.

---

## Quick Start

### Define an event

```python
from lucid_events import Event

class UserRegistered(Event):
    def __init__(self, user_id: int, email: str):
        self.user_id = user_id
        self.email = email
```

Events are plain classes that carry data. No base class is strictly required — `Event` is provided for type clarity and IDE support, but any object works.

### Register listeners and dispatch

```python
from lucid_events import Dispatcher

dispatcher = Dispatcher()

# Register a function listener
@dispatcher.listen(UserRegistered)
def send_welcome_email(event: UserRegistered):
    print(f"Sending welcome email to {event.email}")

@dispatcher.listen(UserRegistered)
def track_signup(event: UserRegistered):
    print(f"Tracking signup for user {event.user_id}")

# Fire the event — both listeners run
dispatcher.dispatch(UserRegistered(user_id=42, email="alice@example.com"))
```

---

## Full API Reference

### `Event`

Base class for events. Optional but recommended for type safety and IDE autocompletion.

```python
from lucid_events import Event

class PaymentFailed(Event):
    def __init__(self, order_id: int, reason: str, amount: float):
        self.order_id = order_id
        self.reason = reason
        self.amount = amount
```

Events are just data carriers. They shouldn't contain business logic — that belongs in listeners.

---

### `Dispatcher()`

Creates a new event dispatcher.

```python
from lucid_events import Dispatcher

dispatcher = Dispatcher()
```

---

### `.listen(event_type, listener=None, priority=0)`

Registers a listener for an event type. Can be used as a decorator or called directly.

| Parameter    | Type                                  | Description                                     |
|--------------|---------------------------------------|-------------------------------------------------|
| `event_type` | `type`                                | The event class to listen for.                  |
| `listener`   | `Callable \| Listener \| None`        | Function or Listener instance. `None` when used as decorator. |
| `priority`   | `int`                                 | Higher priority runs first. Default `0`.        |

```python
# As a decorator
@dispatcher.listen(UserRegistered)
def on_user_registered(event: UserRegistered):
    print(f"Welcome {event.email}")

# Direct registration
dispatcher.listen(UserRegistered, send_welcome_email)

# With priority (higher = runs first)
dispatcher.listen(UserRegistered, send_welcome_email, priority=10)
dispatcher.listen(UserRegistered, track_analytics, priority=5)
# send_welcome_email runs before track_analytics
```

---

### `.dispatch(event)`

Fires an event. All registered listeners for that event's type are called in priority order (highest first, FIFO within same priority).

| Parameter | Type  | Description            |
|-----------|-------|------------------------|
| `event`   | `Any` | The event object.      |

Returns the event object (allows inspection of any mutations listeners made).

```python
event = dispatcher.dispatch(OrderCompleted(order))
```

---

### `.dispatch_many(events)`

Dispatches multiple events in sequence.

```python
dispatcher.dispatch_many([
    OrderCompleted(order),
    InventoryUpdated(order.items),
    UserActivityLogged(user_id=order.user_id, action="purchase"),
])
```

---

### `.has_listeners(event_type)`

Returns `True` if any listeners are registered for the given event type.

```python
dispatcher.has_listeners(UserRegistered)  # True
dispatcher.has_listeners(SomeOtherEvent)  # False
```

---

### `.get_listeners(event_type)`

Returns a list of all listeners for the given event type, sorted by priority (highest first).

```python
listeners = dispatcher.get_listeners(UserRegistered)
```

---

### `.forget(event_type, listener=None)`

Removes listeners. If `listener` is provided, removes that specific listener. Otherwise removes all listeners for the event type.

```python
# Remove a specific listener
dispatcher.forget(UserRegistered, send_welcome_email)

# Remove ALL listeners for an event
dispatcher.forget(UserRegistered)
```

---

### `.flush()`

Removes all listeners for all events.

```python
dispatcher.flush()
```

---

## Stopping Propagation

A listener can stop subsequent listeners from running by returning `False` explicitly.

```python
@dispatcher.listen(OrderCompleted, priority=100)
def fraud_check(event: OrderCompleted):
    if event.order.flagged_for_review:
        flag_for_manual_review(event.order)
        return False  # Stop — don't send confirmation email or anything else

@dispatcher.listen(OrderCompleted, priority=50)
def send_confirmation(event: OrderCompleted):
    # This won't run if fraud_check returned False
    send_email(event.order.user.email, "Order confirmed!")
```

Only an explicit `return False` stops propagation. Returning `None` (default) or any other value continues normally.

---

## Listener Classes

For listeners that need dependencies or hold state, use the `Listener` base class.

```python
from lucid_events import Listener

class SendWelcomeEmail(Listener):
    def __init__(self, mailer: MailerContract, config: ConfigContract):
        self.mailer = mailer
        self.config = config

    def handle(self, event: UserRegistered):
        self.mailer.send(
            to=event.email,
            subject=f"Welcome to {self.config.get('app.name')}",
            body=f"Hi there! Your account #{event.user_id} is ready.",
        )
```

When used with Lucid Container, listener classes are **autowired** — their constructor dependencies are resolved automatically.

```python
# Manual registration
dispatcher.listen(UserRegistered, SendWelcomeEmail(mailer, config))

# With container autowiring (preferred — see Container Integration below)
dispatcher.listen(UserRegistered, SendWelcomeEmail)  # class, not instance
```

---

## Subscribers

A subscriber is a class that registers multiple listeners at once. This keeps related event wiring in one place instead of scattered across your codebase.

```python
from lucid_events import Subscriber

class UserEventSubscriber(Subscriber):

    def subscribe(self, dispatcher: Dispatcher):
        dispatcher.listen(UserRegistered, self.on_registered)
        dispatcher.listen(UserDeleted, self.on_deleted)
        dispatcher.listen(PasswordChanged, self.on_password_changed, priority=10)

    def on_registered(self, event: UserRegistered):
        send_welcome_email(event.email)
        create_default_settings(event.user_id)

    def on_deleted(self, event: UserDeleted):
        cleanup_user_data(event.user_id)
        send_goodbye_email(event.email)

    def on_password_changed(self, event: PasswordChanged):
        notify_security(event.user_id)
        invalidate_sessions(event.user_id)
```

Register a subscriber:

```python
dispatcher.subscribe(UserEventSubscriber())

# With container autowiring (subscriber dependencies resolved automatically)
dispatcher.subscribe(UserEventSubscriber)  # class, not instance
```

---

## Async Support

Async listeners work alongside sync listeners. The dispatcher handles both transparently.

### Async function listeners

```python
@dispatcher.listen(OrderCompleted)
async def notify_warehouse(event: OrderCompleted):
    await warehouse_api.submit(event.order.items)

@dispatcher.listen(OrderCompleted)
def log_order(event: OrderCompleted):
    # Sync listeners work in the same chain
    print(f"Order {event.order.id} completed")
```

### Async dispatch

When any listener is async, use `await dispatch_async()`:

```python
await dispatcher.dispatch_async(OrderCompleted(order))
```

`dispatch_async()` runs all listeners in priority order, awaiting async ones and calling sync ones normally.

### Async listener classes

```python
from lucid_events import AsyncListener

class NotifyExternalAPI(AsyncListener):
    def __init__(self, http_client: HttpClient):
        self.client = http_client

    async def handle(self, event: OrderCompleted):
        await self.client.post("/webhooks/order", json={
            "order_id": event.order.id,
            "total": event.order.total,
        })
```

### Async subscribers

```python
from lucid_events import Subscriber

class PaymentSubscriber(Subscriber):

    def subscribe(self, dispatcher: Dispatcher):
        dispatcher.listen(PaymentReceived, self.on_payment)
        dispatcher.listen(RefundRequested, self.on_refund)

    async def on_payment(self, event: PaymentReceived):
        await ledger.credit(event.amount)

    def on_refund(self, event: RefundRequested):
        # Sync and async methods in the same subscriber — both work
        initiate_refund(event.payment_id)
```

---

## Wildcard Listeners

Listen to all events, regardless of type. Useful for logging, debugging, and audit trails.

```python
@dispatcher.listen_any()
def log_all_events(event):
    print(f"[EVENT] {type(event).__name__}: {vars(event)}")

# With priority
@dispatcher.listen_any(priority=-100)
def audit_trail(event):
    # Runs last (lowest priority), after all specific listeners
    audit_log.record(type(event).__name__, vars(event))
```

Wildcard listeners run **after** all type-specific listeners for that event, unless priority overrides this.

---

## Event Mutability

Events are mutable by default. Listeners can modify the event, and subsequent listeners see the changes. This is intentional — it enables patterns like enrichment and validation.

```python
class ValidateOrder(Event):
    def __init__(self, order: Order):
        self.order = order
        self.is_valid = True
        self.errors: list[str] = []

@dispatcher.listen(ValidateOrder, priority=100)
def check_stock(event: ValidateOrder):
    if not inventory.in_stock(event.order.items):
        event.is_valid = False
        event.errors.append("Items out of stock")

@dispatcher.listen(ValidateOrder, priority=50)
def check_payment(event: ValidateOrder):
    if not event.is_valid:
        return  # Previous listener already failed it
    if not payment.verify(event.order.payment_method):
        event.is_valid = False
        event.errors.append("Payment method invalid")

# Dispatch and inspect
event = dispatcher.dispatch(ValidateOrder(order))
if not event.is_valid:
    print(f"Validation failed: {event.errors}")
```

---

## Queued Listeners

Mark a listener to be dispatched later through a queue instead of running immediately. Requires `lucid-queue` (when available) — without it, queued listeners run synchronously as a fallback.

```python
from lucid_events import Listener

class GenerateInvoicePDF(Listener):
    queued = True  # This listener runs in the background

    def handle(self, event: OrderCompleted):
        pdf = generate_pdf(event.order)
        store_invoice(event.order.id, pdf)
```

The `queued = True` flag tells the dispatcher to serialize the event and push it onto the queue rather than calling `handle()` inline. The queue worker deserializes and runs it later.

When `lucid-queue` isn't installed, the dispatcher logs a warning and runs the listener synchronously. This means your code works the same in development (sync) and production (queued) without changes.

---

## Container Integration

### EventDispatcher as a service

```python
from lucid_container import ServiceProvider
from lucid_events import Dispatcher, DispatcherContract

class EventServiceProvider(ServiceProvider):

    def register(self):
        self.app.singleton(DispatcherContract, Dispatcher)
        self.app.alias("events", DispatcherContract)

    def boot(self):
        dispatcher = self.app.make(DispatcherContract)

        # Register listener classes — autowired through container
        dispatcher.listen(UserRegistered, SendWelcomeEmail, priority=10)
        dispatcher.listen(UserRegistered, TrackSignupAnalytics)
        dispatcher.listen(OrderCompleted, SendOrderConfirmation)
        dispatcher.listen(OrderCompleted, UpdateInventory, priority=20)

        # Register subscribers — also autowired
        dispatcher.subscribe(PaymentEventSubscriber)
```

### Container-aware dispatcher

When the `Dispatcher` is given a container reference, it can resolve listener classes on the fly:

```python
dispatcher = Dispatcher(container=app)

# Pass a class, not an instance — container builds it with dependencies
dispatcher.listen(UserRegistered, SendWelcomeEmail)

# When UserRegistered fires, the container does:
#   listener = container.make(SendWelcomeEmail)
#   listener.handle(event)
# SendWelcomeEmail gets its MailerContract, ConfigContract, etc. autowired
```

This is the preferred pattern. Listener classes aren't instantiated until the event actually fires. Dependencies are resolved lazily, not at registration time.

### Dispatching from any service

```python
class OrderService:
    def __init__(self, repo: OrderRepository, events: DispatcherContract):
        self.repo = repo
        self.events = events

    def complete(self, order: Order):
        self.repo.save(order)
        self.events.dispatch(OrderCompleted(order))
```

`OrderService` depends on `DispatcherContract`, not on mailers, analytics, or anything else. Adding a new side effect means registering a new listener — zero changes to `OrderService`.

---

## Real-World Examples

### Decoupled user lifecycle

```python
# Events
class UserRegistered(Event):
    def __init__(self, user_id: int, email: str, name: str):
        self.user_id = user_id
        self.email = email
        self.name = name

class UserVerified(Event):
    def __init__(self, user_id: int):
        self.user_id = user_id

class UserDeactivated(Event):
    def __init__(self, user_id: int, reason: str):
        self.user_id = user_id
        self.reason = reason

# Listeners — each lives in its own module, knows nothing about the others
class SendWelcomeEmail(Listener):
    def __init__(self, mailer: MailerContract):
        self.mailer = mailer

    def handle(self, event: UserRegistered):
        self.mailer.send(event.email, "Welcome!", f"Hi {event.name}!")

class CreateDefaultUserSettings(Listener):
    def __init__(self, settings_repo: SettingsRepository):
        self.settings = settings_repo

    def handle(self, event: UserRegistered):
        self.settings.create_defaults(event.user_id)

class GrantFreeTrial(Listener):
    def __init__(self, billing: BillingService):
        self.billing = billing

    def handle(self, event: UserVerified):
        self.billing.start_trial(event.user_id, days=14)

class CleanupUserData(Listener):
    queued = True

    def __init__(self, storage: StorageContract, cache: CacheContract):
        self.storage = storage
        self.cache = cache

    def handle(self, event: UserDeactivated):
        self.storage.delete_user_files(event.user_id)
        self.cache.forget(f"user:{event.user_id}:*")
```

### Request middleware logging

```python
class RequestReceived(Event):
    def __init__(self, method: str, path: str, ip: str):
        self.method = method
        self.path = path
        self.ip = ip

class ResponseSent(Event):
    def __init__(self, status: int, duration_ms: float):
        self.status = status
        self.duration_ms = duration_ms

@dispatcher.listen_any()
def dev_logger(event):
    if config.boolean("app.debug"):
        print(f"[{type(event).__name__}] {vars(event)}")
```

### Validation pipeline with events

```python
class FormSubmitted(Event):
    def __init__(self, data: dict):
        self.data = data
        self.errors: list[str] = []
        self.passed = True

    def fail(self, message: str):
        self.passed = False
        self.errors.append(message)

@dispatcher.listen(FormSubmitted, priority=100)
def validate_required_fields(event: FormSubmitted):
    for field in ["name", "email"]:
        if not event.data.get(field):
            event.fail(f"{field} is required")

@dispatcher.listen(FormSubmitted, priority=90)
def validate_email_format(event: FormSubmitted):
    email = event.data.get("email", "")
    if email and "@" not in email:
        event.fail("Invalid email format")

@dispatcher.listen(FormSubmitted, priority=80)
def normalize_data(event: FormSubmitted):
    if not event.passed:
        return  # Don't normalize invalid data
    event.data["email"] = event.data["email"].lower().strip()
    event.data["name"] = event.data["name"].strip().title()

# Usage
event = dispatcher.dispatch(FormSubmitted({"name": "", "email": "bad"}))
if not event.passed:
    print(event.errors)  # ["name is required", "Invalid email format"]
```

---

## Architecture

### Project Structure

```
lucid-events/
├── src/
│   └── lucid_events/
│       ├── __init__.py            # Public API exports
│       ├── dispatcher.py          # Dispatcher class
│       ├── event.py               # Event base class
│       ├── listener.py            # Listener base class
│       ├── async_listener.py      # AsyncListener base class
│       ├── subscriber.py          # Subscriber base class
│       ├── contract.py            # DispatcherContract ABC
│       └── exceptions.py          # EventError
├── tests/
│   ├── __init__.py
│   ├── test_dispatch.py           # Core dispatch and listener execution
│   ├── test_priority.py           # Priority ordering
│   ├── test_propagation.py        # Stopping propagation with return False
│   ├── test_listener_class.py     # Listener class with handle()
│   ├── test_subscriber.py         # Subscriber registration
│   ├── test_async.py              # Async listeners and dispatch_async
│   ├── test_wildcard.py           # listen_any() global listeners
│   ├── test_mutability.py         # Event mutation across listeners
│   ├── test_container.py          # Container-aware lazy resolution
│   ├── test_forget.py             # Removing listeners
│   └── test_edge_cases.py         # No listeners, unknown events, etc.
├── pyproject.toml
├── README.md
├── LICENSE
└── CHANGELOG.md
```

### Implementation Notes

**Dispatcher internals:**

```python
self._listeners: dict[type, list[tuple[int, int, Callable | type]]]
#                      ^event   ^priority ^insertion_order ^listener
self._wildcard_listeners: list[tuple[int, int, Callable]]
self._container: Container | None
self._insertion_counter: int  # For stable sort within same priority
```

Listeners are stored as `(priority, insertion_order, listener)` tuples. When dispatching, the list is sorted by `(-priority, insertion_order)` — highest priority first, FIFO within the same priority.

**Lazy resolution with container:**

When a listener is registered as a class (not an instance), the dispatcher stores the class itself. On dispatch, it checks:

```python
def _resolve_listener(self, listener):
    if isinstance(listener, type):
        if self._container:
            return self._container.make(listener)
        return listener()  # Fallback: no-arg construction
    return listener  # Already an instance or callable
```

This means listener classes are instantiated per-dispatch. If you want a singleton listener, register an instance or bind it as a singleton in the container.

**Async dispatch:**

```python
async def dispatch_async(self, event):
    for priority, order, listener in self._sorted_listeners(type(event)):
        resolved = self._resolve_listener(listener)
        if isinstance(resolved, AsyncListener):
            result = await resolved.handle(event)
        elif asyncio.iscoroutinefunction(resolved):
            result = await resolved(event)
        elif isinstance(resolved, Listener):
            result = resolved.handle(event)
        else:
            result = resolved(event)

        if result is False:
            break
    return event
```

`dispatch()` (sync) raises `TypeError` if it encounters an async listener. Use `dispatch_async()` when any listener in the chain might be async.

**Subscriber wiring:**

When `dispatcher.subscribe(SomeSubscriber)` is called:

1. If `SomeSubscriber` is a class and a container exists → autowire it.
2. Call `subscriber.subscribe(dispatcher)` — the subscriber registers its own listeners using the dispatcher reference it receives.
3. The subscriber instance is stored so it (and its bound methods) aren't garbage collected.

**Propagation stopping:**

Only `return False` stops propagation. This is checked with `result is False`, not `not result`. So returning `None`, `0`, `""`, or `[]` does NOT stop propagation — only the boolean `False` does.

### Public API (what `__init__.py` exports)

```python
from lucid_events.event import Event
from lucid_events.dispatcher import Dispatcher
from lucid_events.listener import Listener
from lucid_events.async_listener import AsyncListener
from lucid_events.subscriber import Subscriber
from lucid_events.contract import DispatcherContract
from lucid_events.exceptions import EventError

__all__ = [
    "Event",
    "Dispatcher",
    "Listener",
    "AsyncListener",
    "Subscriber",
    "DispatcherContract",
    "EventError",
]
```

### Contracts

```python
from abc import ABC, abstractmethod
from typing import Any, Callable

class DispatcherContract(ABC):
    @abstractmethod
    def listen(self, event_type: type, listener: Callable | type | None = None, priority: int = 0): ...

    @abstractmethod
    def dispatch(self, event: Any) -> Any: ...

    @abstractmethod
    async def dispatch_async(self, event: Any) -> Any: ...

    @abstractmethod
    def subscribe(self, subscriber: Any): ...

    @abstractmethod
    def has_listeners(self, event_type: type) -> bool: ...

    @abstractmethod
    def forget(self, event_type: type, listener: Callable | None = None): ...

    @abstractmethod
    def flush(self): ...
```

### Exceptions

| Exception    | When                                                         |
|--------------|--------------------------------------------------------------|
| `EventError` | Base exception for event system errors.                      |

---

## pyproject.toml Specification

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "lucid-events"
version = "0.1.0"
description = "Event dispatcher with typed events, prioritized listeners, and container autowiring."
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [
    { name = "Your Name", email = "your@email.com" },
]
keywords = [
    "events", "event-dispatcher", "observer", "pub-sub",
    "listeners", "signals", "hooks", "decoupling",
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Typing :: Typed",
]

[project.urls]
Homepage = "https://github.com/yourname/lucid-events"
Documentation = "https://github.com/yourname/lucid-events#readme"
Repository = "https://github.com/yourname/lucid-events"
Issues = "https://github.com/yourname/lucid-events/issues"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.mypy]
strict = true

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-asyncio>=0.21", "mypy>=1.0", "ruff>=0.1"]
```

---

## Test Cases to Implement

### Core Dispatch

- Dispatching an event calls all registered listeners
- Listeners receive the event object
- `dispatch()` returns the event object
- Dispatching an event with no listeners does not raise
- Dispatching a non-Event object works (any object accepted)
- `dispatch_many()` dispatches all events in order

### Listener Registration

- `.listen()` with a function registers it
- `.listen()` as a decorator registers and returns the function
- `.listen()` with a `Listener` subclass instance works
- `.listen()` with a `Listener` subclass class (for container resolution) works
- Multiple listeners on the same event all fire
- Same listener registered twice fires twice

### Priority

- Higher priority listeners run first
- Same priority preserves insertion order (FIFO)
- Default priority is `0`
- Negative priorities run after default
- Priority `100` runs before priority `50` runs before priority `0`

### Stopping Propagation

- Listener returning `False` stops subsequent listeners
- Listener returning `None` does NOT stop propagation
- Listener returning `0` does NOT stop propagation
- Listener returning `""` does NOT stop propagation
- Listener returning `True` does NOT stop propagation
- Only the explicit value `False` (identity check) stops
- Higher priority listener can block lower priority ones
- Stopped event is still returned from `dispatch()`

### Listener Classes

- `Listener` subclass `.handle()` is called with the event
- `Listener` with dependencies works when instantiated manually
- `Listener` registered as a class is resolved via container
- `Listener` registered as a class without container uses no-arg constructor

### Subscribers

- `subscriber.subscribe()` is called with the dispatcher
- Subscriber methods are registered as listeners
- Subscriber with multiple event types registers all
- Subscriber registered as a class is resolved via container
- Subscriber methods with priorities work
- Subscriber instance is retained (not garbage collected)

### Async

- Async function listener is awaited in `dispatch_async()`
- `AsyncListener` subclass `.handle()` is awaited
- Mixed sync and async listeners work in `dispatch_async()`
- Sync `dispatch()` raises `TypeError` for async listeners
- Async listener can stop propagation with `return False`
- Async subscriber methods work
- `dispatch_async()` returns the event

### Wildcard Listeners

- `listen_any()` listener fires for every event type
- `listen_any()` listener receives the event object
- `listen_any()` with priority works
- Multiple wildcard listeners fire in priority order
- Wildcard listeners fire after type-specific listeners (at same priority)
- Wildcard listener returning `False` stops other wildcard listeners
- Type-specific propagation stop does NOT affect wildcard listeners
- Wildcard listener does NOT affect type-specific listeners of other events

### Event Mutability

- Listener can modify event attributes
- Subsequent listeners see the mutations
- Dispatch returns the mutated event
- Multiple listeners mutating the same field — last writer wins

### Forget / Flush

- `forget(EventType, listener)` removes that specific listener
- `forget(EventType)` removes all listeners for that event
- `forget()` on unregistered event is a no-op
- `flush()` removes all listeners for all events
- `flush()` removes wildcard listeners too
- After `forget()`, dispatch no longer calls removed listener

### Container Integration

- Dispatcher with container resolves listener classes on dispatch
- Listener class dependencies are autowired
- Subscriber class dependencies are autowired
- Without container, listener class is instantiated with no args
- Listener resolved per-dispatch (not cached by dispatcher)

### Edge Cases

- Event with no data (empty class) dispatches fine
- Event that is not a subclass of `Event` works
- Listener that raises an exception — exception propagates, remaining listeners don't run
- Registering a listener for a type that was never dispatched is fine
- `has_listeners()` returns False after all listeners forgotten
- `get_listeners()` returns empty list for unknown event
- Very large number of listeners (1000+) on single event works
- Dispatching inside a listener (recursive dispatch) works
- Same function listening to multiple event types works
- Lambda as a listener works

---

## Part of the Lucid Ecosystem

Lucid Events is the fourth package in the **Lucid** ecosystem — the nervous system that connects everything without coupling.

Released:

- `lucid-pipeline` — Clean, expressive pipelines for multi-step data processing.
- `lucid-container` — Dependency injection container with autowiring.
- `lucid-config` — Cascading configuration with dot-notation access and type casting.

Coming soon:

- `lucid-cache` — Multi-driver cache with a unified API.
- `lucid-mail` — Multi-driver mail with a unified API.
- `lucid-queue` — Background job processing with swappable backends.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
