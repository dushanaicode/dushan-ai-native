from dataclasses import dataclass
from pathlib import Path

from framework.common.component.component_metadata import ComponentMetadata


@dataclass(frozen=True, slots=True)
class ComponentDefinition:
    """已发现类的静态来源快照，不保存实例或可变应用配置。"""

    component: type
    module: str
    source: Path
    metadata: ComponentMetadata
