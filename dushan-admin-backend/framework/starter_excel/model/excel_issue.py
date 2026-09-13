from dataclasses import dataclass


@dataclass(frozen=True)
class ExcelIssue:
    """行列均从 1 开始；column=None 表示整行或模型级错误，不保存原始值。"""

    row: int
    column: int | None
    field: str
    message: str
