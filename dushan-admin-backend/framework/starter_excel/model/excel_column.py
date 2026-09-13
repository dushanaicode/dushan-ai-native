from dataclasses import dataclass

from framework.starter_excel.converter.excel_converter import ExcelConverter


@dataclass(frozen=True)
class ExcelColumn:
    """放入 Pydantic Annotated 字段元数据，列顺序沿用模型声明顺序。"""

    title: str
    converter: ExcelConverter | None = None
    options: tuple[str, ...] | None = None
    exportable: bool = True
    sensitive: bool = False
    trim: bool = True
    number_format: str | None = None
