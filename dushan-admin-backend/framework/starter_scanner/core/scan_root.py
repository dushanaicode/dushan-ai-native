from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ScanRoot:
    """调用方明确关联模块 ID、导入包与允许的物理目录。"""

    module: str
    package: str
    path: Path
