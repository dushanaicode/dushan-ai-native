from framework.starter_scanner.core.scan_diagnostics import ScanDiagnostics


class ScanRecorder:
    """每次扫描独立记录；样例和慢模块数量由已校验配置限制。"""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.phases = {name: 0.0 for name in ("enumeration", "validation", "import", "collection")}
        self.skipped: dict[str, int] = {}
        self.examples: list[tuple[str, str]] = []
        self.slow: list[tuple[str, float]] = []

    def skip(self, reason: str, name: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1
        if len(self.examples) < self.limit:
            self.examples.append((reason, name))

    def imported(self, name: str, seconds: float) -> None:
        self.phases["import"] += seconds
        self.slow.append((name, seconds))
        self.slow.sort(key=lambda value: (-value[1], value[0]))
        del self.slow[self.limit :]

    def snapshot(self) -> ScanDiagnostics:
        return ScanDiagnostics(
            tuple(self.phases.items()),
            tuple(sorted(self.skipped.items())),
            tuple(self.examples),
            tuple(self.slow),
        )
