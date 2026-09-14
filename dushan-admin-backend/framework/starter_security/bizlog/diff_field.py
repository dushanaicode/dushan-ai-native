from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DiffField:
    """Pydantic Annotated 字段的显式差异投影；ignore 优先于名称和格式器。"""

    name: str
    formatter: str | None = None
    ignore: bool = False
