from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProtectionEvent:
    """可选观测接点的最小事件；禁止携带业务参数、身份、键、owner 或异常文本。"""

    feature: str
    action: str
    outcome: str
    elapsed_ms: float
