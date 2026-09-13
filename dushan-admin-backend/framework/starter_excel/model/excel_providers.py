from dataclasses import dataclass
from typing import Any

from framework.starter_excel.spi.area_provider import AreaProvider
from framework.starter_excel.spi.dict_data_provider import DictDataProvider
from framework.starter_excel.spi.name_provider import NameProvider


@dataclass(frozen=True)
class ExcelProviders:
    """由当前应用显式传入的业务依赖；未提供的能力只在使用时明确失败。"""

    dictionaries: DictDataProvider | None = None
    departments: NameProvider | None = None
    posts: NameProvider | None = None
    areas: AreaProvider[Any] | None = None
