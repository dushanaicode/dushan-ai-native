import time
from collections import deque
from collections.abc import Callable
from threading import RLock
from typing import Any, TypeVar

from framework.starter_di.core.state.state_key import StateKey
from framework.starter_di.core.state.state_metadata import StateMetadata
from framework.starter_di.definitions.constants.di_error_codes import DiErrorCodes
from framework.starter_di.exception.di_exception import DiException

T = TypeVar("T")
StateListener = Callable[[Any], None]


class StateManager:
    """应用独立的类型化状态表，先原子提交，再按提交顺序通知。"""

    def __init__(self) -> None:
        self._lock = RLock()
        self._metadata: dict[StateKey, StateMetadata] = {}
        self._listeners: dict[StateKey, list[StateListener]] = {}
        self._queue: deque[tuple[tuple[StateListener, ...], object]] = deque()
        self._dispatching = False

    def register_state(self, key: StateKey[T], instance: T) -> None:
        self.register_states(((key, instance),))

    def register_states(self, states: tuple[tuple[StateKey, Any], ...]) -> None:
        """整批类型验证失败时不写入任何状态。"""
        if not states or len({key for key, _ in states}) != len(states):
            raise ValueError("状态批次不能为空或包含重复键")
        for key, instance in states:
            if instance is None or not isinstance(instance, key.value_type):
                raise DiException(
                    error_code=DiErrorCodes.INVALID_STATE, msg=f"运行状态类型不匹配：{key.name}"
                )
        with self._lock:
            now = time.time()
            for key, instance in states:
                previous = self._metadata.get(key)
                self._metadata[key] = StateMetadata(
                    key, instance, now if previous is None else previous.created_at, now
                )
                self._queue.append((tuple(self._listeners.get(key, ())), instance))
            if self._dispatching:
                return
            self._dispatching = True
        self._dispatch()

    def _dispatch(self) -> None:
        errors = []
        while True:
            with self._lock:
                if not self._queue:
                    self._dispatching = False
                    break
                listeners, instance = self._queue.popleft()
            for listener in listeners:
                try:
                    listener(instance)
                except BaseException as error:
                    errors.append(error)
        if errors:
            if len(errors) == 1:
                raise errors[0]
            raise BaseExceptionGroup("运行状态已提交，部分监听器失败", errors)

    def require_state(self, key: StateKey[T]) -> T:
        with self._lock:
            if key not in self._metadata:
                raise DiException(
                    error_code=DiErrorCodes.STATE_NOT_FOUND, msg=f"必需运行状态未注册：{key.name}"
                )
            return self._metadata[key].instance

    def find_state(self, key: StateKey[T]) -> T | None:
        with self._lock:
            entry = self._metadata.get(key)
            return entry.instance if entry is not None else None

    def remove_state(self, key: StateKey) -> bool:
        return self.remove_states((key,)) == 1

    def remove_states(self, keys: tuple[StateKey, ...]) -> int:
        if len(set(keys)) != len(keys):
            raise ValueError("状态移除不能包含重复键")
        with self._lock:
            found = set(keys) & self._metadata.keys()
            for key in found:
                del self._metadata[key]
            return len(found)

    def snapshot(self) -> dict[StateKey, StateMetadata]:
        with self._lock:
            return dict(self._metadata)

    def add_state_listener(self, key: StateKey, listener: StateListener) -> None:
        with self._lock:
            self._listeners.setdefault(key, []).append(listener)

    def remove_state_listener(self, key: StateKey, listener: StateListener) -> bool:
        with self._lock:
            listeners = self._listeners.get(key)
            if listeners is None or listener not in listeners:
                return False
            listeners.remove(listener)
            if not listeners:
                del self._listeners[key]
            return True

    def clear(self) -> None:
        """释放当前应用的状态与监听引用，不关闭其他所有者的资源。"""
        with self._lock:
            self._metadata.clear()
            self._listeners.clear()
            self._queue.clear()
