from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommitAction:
    callback: Callable
    name: str
    required: bool
