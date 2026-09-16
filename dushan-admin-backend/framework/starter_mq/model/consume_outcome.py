from dataclasses import dataclass

from framework.starter_mq.enums.message_state import MessageState


@dataclass(frozen=True, slots=True)
class ConsumeOutcome:
    state: MessageState
    error: BaseException | None = None
    observation_errors: tuple[BaseException, ...] = ()
