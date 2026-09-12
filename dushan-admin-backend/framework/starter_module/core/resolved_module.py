from dataclasses import dataclass
from pathlib import Path

from framework.starter_module.config.module_definition import ModuleDefinition


@dataclass(frozen=True, slots=True)
class ResolvedModule:
    """已校验声明及其物理归属，类定义和资源都以此包为边界。"""

    definition: ModuleDefinition
    root: Path
