from dataclasses import dataclass

from framework.starter_mq.enums.message_state import MessageState
from framework.starter_mq.model.message_context import MessageContext


@dataclass(frozen=True, slots=True)
class ConsumeRecord:
    context: MessageContext
    state: MessageState
    elapsed_seconds: float
    error_type: str | None
    observation_error_types: tuple[str, ...]
