from collections import Counter
from threading import Lock

from framework.starter_monitor.core.sdk_log_guard import SdkLogGuard


class MonitorDiagnostics:
    """仅保存有界种类的计数，诊断不保留原始异常、RPC详情或导出载荷。"""

    def __init__(self) -> None:
        self._lock = Lock()
        self._counts: Counter[str] = Counter()
        self.logger = None

    def increment(self, key: str, count: int = 1, *, warn: bool = False) -> None:
        with self._lock:
            self._counts[key] += count
            total = self._counts[key]
        # 首次及2的幂次输出，持续故障不形成逐Span日志洪流。
        if warn and self.logger is not None and total & (total - 1) == 0:
            try:
                with SdkLogGuard.quiet():
                    self.logger.warning("追踪诊断：{}，累计 {}", key, total)
            except BaseException:
                pass

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counts)
