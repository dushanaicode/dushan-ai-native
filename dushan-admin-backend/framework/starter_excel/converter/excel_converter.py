from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from framework.starter_excel.model.conversion_context import ConversionContext


class ExcelConverter(Protocol):
    """显式双向转换接口；None 由读写器统一处理，不进入转换器。"""

    async def to_excel(self, value: Any, context: ConversionContext) -> Any: ...

    async def to_python(self, value: Any, context: ConversionContext) -> Any: ...
