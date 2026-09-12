from framework.starter_scanner.config.scanner_config import ScannerConfig


class PathFilter:
    """在文件读取和 import 前按完整包前缀剪枝；排除优先于包含。"""

    def __init__(self, config: ScannerConfig) -> None:
        self.config = config

    def accepts(self, package: str, *, traverse: bool = False) -> bool:
        """遍历包含范围的父包，但不会把父包的类作为命中结果。"""
        return self.reason(package, traverse=traverse) is None

    def reason(self, package: str, *, traverse: bool = False) -> str | None:
        if any(
            package == excluded or package.startswith(excluded + ".")
            for excluded in self.config.exclude_packages
        ):
            return "excluded_prefix"
        included = self.config.include_packages
        accepted = included is None or any(
            package == prefix
            or package.startswith(prefix + ".")
            or (traverse and prefix.startswith(package + "."))
            for prefix in included
        )
        return None if accepted else "outside_include"
