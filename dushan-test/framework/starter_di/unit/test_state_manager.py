import pytest

from framework.starter_di.core.state.state_key import StateKey
from framework.starter_di.core.state.state_manager import StateManager
from framework.starter_di.exception.di_exception import DiException

pytestmark = pytest.mark.unit


def test_typed_state_batches_are_atomic_and_instances_independent():
    count, flag = StateKey("count", int), StateKey("flag", bool)
    first, second = StateManager(), StateManager()
    first.register_state(count, 2)
    with pytest.raises(DiException):
        first.register_states(((count, 3), (flag, "bad")))
    assert first.require_state(count) == 2
    assert first.find_state(flag) is None and second.find_state(count) is None
    snapshot = first.snapshot()
    snapshot.clear()
    assert first.require_state(count) == 2
    assert first.remove_state(count) and not first.remove_state(count)
    with pytest.raises(DiException):
        first.require_state(count)


def test_state_listener_reentry_is_ordered_and_errors_follow_commit():
    states, events = StateManager(), []
    key = StateKey("revision", int)

    def first(value):
        events.append(("first", value))
        if value == 1:
            states.register_state(key, 2)

    def second(value):
        events.append(("second", value))
        if value == 2:
            raise ValueError("notification failure")

    states.add_state_listener(key, first)
    states.add_state_listener(key, second)
    with pytest.raises(ValueError, match="notification failure"):
        states.register_state(key, 1)
    assert events == [("first", 1), ("second", 1), ("first", 2), ("second", 2)]
    assert states.require_state(key) == 2
    assert states.remove_state_listener(key, second)
    states.clear()
    assert states.snapshot() == {}
