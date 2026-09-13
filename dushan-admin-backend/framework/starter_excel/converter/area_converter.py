from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from framework.starter_excel.model.conversion_context import ConversionContext
from framework.starter_excel.spi.area_provider import AreaProvider

if TYPE_CHECKING:
    from framework.starter_ip.model.area import Area


@dataclass(frozen=True)
class AreaConverter:
    """默认使用含国家的完整地区路径，可无歧义回读；path=False 仅用于名称展示。"""

    path: bool = True

    @staticmethod
    def _service(context: ConversionContext) -> AreaProvider[Area]:
        service = context.providers.areas
        if service is None:
            raise ValueError("未提供地区服务")
        return service

    async def to_excel(self, value: Area, context: ConversionContext) -> str:
        if not self.path:
            return str(value)
        path = self._service(context).format_area_path(value.id)
        if path is None:
            raise ValueError("地区不存在")
        return path

    async def to_python(self, value: str, context: ConversionContext) -> Area:
        if not self.path:
            raise ValueError("单节点地区名称不能唯一反向转换，请使用完整路径")
        area = self._service(context).parse_area_path(value)
        if area is None:
            raise ValueError("完整地区路径不存在")
        return area
