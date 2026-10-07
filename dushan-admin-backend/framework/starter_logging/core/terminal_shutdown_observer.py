from dataclasses import dataclass


@dataclass(slots=True)
class TerminalShutdownObserver:
    """记录调用方是否已停止等待后台日志清理。"""

    detached: bool = False
