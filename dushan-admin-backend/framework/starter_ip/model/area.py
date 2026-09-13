from dataclasses import dataclass, field
from typing import ClassVar


@dataclass(frozen=True, slots=True, eq=False)
class Area:
    """地区目录中的只读节点；名称显示不包含父级，完整路径由 AreaService 提供。"""

    ID_GLOBAL: ClassVar[int] = 0
    ID_CHINA: ClassVar[int] = 1

    id: int
    name: str
    type: int
    parent: "Area | None" = field(default=None, repr=False)
    children: "tuple[Area, ...]" = field(default=(), repr=False)

    def __str__(self) -> str:
        return self.name
