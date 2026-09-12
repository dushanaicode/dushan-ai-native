from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScanDiagnostics:
    """自动扫描的分段耗时、跳过计数及有界样例；不保存类实例或配置值。"""

    phase_seconds: tuple[tuple[str, float], ...]
    skipped_counts: tuple[tuple[str, int], ...]
    skipped_examples: tuple[tuple[str, str], ...]
    slow_imports: tuple[tuple[str, float], ...]
