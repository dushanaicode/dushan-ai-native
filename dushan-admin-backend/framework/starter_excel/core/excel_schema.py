import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any, get_args

from pydantic import BaseModel

from framework.starter_excel.definitions.constants.excel_error_codes import ExcelErrorCodes
from framework.starter_excel.exception.excel_exception import ExcelException
from framework.starter_excel.model.excel_column import ExcelColumn


class ExcelSchema:
    """单一列元数据入口，统一导入映射、导出选择与敏感字段策略。"""

    _SENSITIVE = (
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "private_key",
        "credential",
        "cookie",
        "authorization",
    )

    def __init__(self, model: type[BaseModel]) -> None:
        self.model = model
        self.columns: dict[str, ExcelColumn] = {}
        titles: set[str] = set()
        for name, field in model.model_fields.items():
            metadata = [item for item in field.metadata if isinstance(item, ExcelColumn)]
            if not metadata:
                continue
            if len(metadata) != 1:
                raise ExcelException(ExcelErrorCodes.CONFIG, f"字段 {name} 重复声明 ExcelColumn")
            column = metadata[0]
            if (
                not column.title.strip()
                or column.title != column.title.strip()
                or column.title in titles
            ):
                raise ExcelException(ExcelErrorCodes.CONFIG, "Excel 列名必须唯一、非空且无首尾空白")
            if column.options is not None and len(set(column.options)) != len(column.options):
                raise ExcelException(ExcelErrorCodes.CONFIG, "Excel 静态下拉选项不能重复")
            titles.add(column.title)
            self.columns[name] = column
        if not self.columns:
            raise ExcelException(ExcelErrorCodes.CONFIG, "模型未声明 ExcelColumn 元数据")

    def export_columns(self, fields: list[str] | None = None) -> dict[str, ExcelColumn]:
        """只允许声明且可导出的字段；未知或禁止字段明确失败，不静默忽略。"""
        allowed = {
            name: column
            for name, column in self.columns.items()
            if column.exportable
            and not column.sensitive
            and not self.model.model_fields[name].exclude
            and name.lower() != "pwd"
            and not any(part in name.lower() for part in self._SENSITIVE)
        }
        if fields is not None:
            if len(fields) != len(set(fields)) or set(fields) - allowed.keys():
                raise ExcelException(ExcelErrorCodes.CONFIG, "导出字段包含重复、未知或禁止的字段")
            allowed = {name: column for name, column in allowed.items() if name in fields}
        if not allowed:
            raise ExcelException(ExcelErrorCodes.CONFIG, "没有可导出的字段")
        return allowed

    def export_fields(self) -> list[dict[str, str]]:
        return [
            {"field": name, "title": column.title} for name, column in self.export_columns().items()
        ]

    def normalize(self, field_name: str, value: Any) -> Any:
        """保留 None；字符列接受 Excel 数字；日期拒绝无格式序号，数字拒绝布尔值。"""
        if value is None:
            return None
        annotation = self.model.model_fields[field_name].annotation
        args = tuple(arg for arg in get_args(annotation) if arg is not type(None))
        if len(args) == 1:
            annotation = args[0]
        if isinstance(value, bool) and annotation in (int, float, Decimal):
            raise ValueError("布尔值不能作为数字")
        if annotation in (date, datetime) and isinstance(value, (int, float, bool)):
            raise ValueError("日期必须使用日期单元格或 ISO 日期文本")
        if annotation is str and isinstance(value, (int, float)) and not isinstance(value, bool):
            if isinstance(value, float):
                if not math.isfinite(value):
                    raise ValueError("数字必须是有限值")
                return str(int(value)) if value.is_integer() else str(value)
            return str(value)
        return value
