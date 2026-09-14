from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RateReservation:
    """一次真实预留的释放凭据；owner 不进入 repr 或日志。"""

    identifier: str = field(repr=False)
    owner: str = field(repr=False)
