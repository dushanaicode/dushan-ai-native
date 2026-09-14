from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class LogRecordReservation:
    """提供者拥有的持久预留；handle 仅交还同一提供者，不写日志。"""

    event_id: str
    persistent: bool
    handle: str = field(repr=False)
