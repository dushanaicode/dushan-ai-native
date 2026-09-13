from dataclasses import dataclass, field
from typing import Any

from framework.starter_excel.config.excel_settings import ExcelSettings
from framework.starter_excel.model.excel_providers import ExcelProviders


@dataclass
class ConversionContext:
    """单次操作拥有查询快照；不会跨请求、应用或实例复用业务数据。"""

    settings: ExcelSettings
    providers: ExcelProviders
    lookups: dict[tuple[str, str], Any] = field(default_factory=dict)
