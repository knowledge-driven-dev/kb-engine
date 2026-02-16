"""Tests for kdd.infrastructure.events.bus."""

from dataclasses import dataclass

from kdd.infrastructure.events.bus import InMemoryEventBus


@dataclass(frozen=True)
class FakeEventA:
    value: str


@dataclass(frozen=True)
class FakeEventB:
    count: int


class TestInMemoryEventBus:
    def test_publish_calls_handler(self):
        bus = InMemoryEventBus()
        received = []
        bus.subscribe(FakeEventA, lambda e: received.append(e))

        bus.publish(FakeEventA(value="hello"))

        assert len(received) == 1
        assert received[0].value == "hello"

    def test_multiple_handlers(self):
        bus = InMemoryEventBus()
        results_1 = []
        results_2 = []
        bus.subscribe(FakeEventA, lambda e: results_1.append(e.value))
        bus.subscribe(FakeEventA, lambda e: results_2.append(e.value.upper()))

        bus.publish(FakeEventA(value="test"))

        assert results_1 == ["test"]
        assert results_2 == ["TEST"]

    def test_different_event_types(self):
        bus = InMemoryEventBus()
        a_events = []
        b_events = []
        bus.subscribe(FakeEventA, lambda e: a_events.append(e))
        bus.subscribe(FakeEventB, lambda e: b_events.append(e))

        bus.publish(FakeEventA(value="a"))
        bus.publish(FakeEventB(count=42))

        assert len(a_events) == 1
        assert len(b_events) == 1
        assert b_events[0].count == 42

    def test_no_handler_is_noop(self):
        bus = InMemoryEventBus()
        # Should not raise
        bus.publish(FakeEventA(value="ignored"))

    def test_handler_order_preserved(self):
        bus = InMemoryEventBus()
        order = []
        bus.subscribe(FakeEventA, lambda e: order.append(1))
        bus.subscribe(FakeEventA, lambda e: order.append(2))
        bus.subscribe(FakeEventA, lambda e: order.append(3))

        bus.publish(FakeEventA(value="x"))

        assert order == [1, 2, 3]
