from collections.abc import Iterable
from typing import TypeVar

from pydantic import BaseModel

from framework.common.page.schemas.page_result import PageResult

Model = TypeVar("Model", bound=BaseModel)


class ConversionUtils:
    """按明确的 Pydantic 模型转换对象、集合与分页结果。"""

    @staticmethod
    def item_to_vo(item: object | None, vo_class: type[Model]) -> Model | None:
        """保留明确的空对象，否则按目标模型校验。"""
        return None if item is None else vo_class.model_validate(item)

    @staticmethod
    def list_to_vo_list(items: Iterable[object], vo_class: type[Model]) -> list[Model]:
        """转换实际存在的集合；缺失集合应由调用方处理。"""
        return [vo_class.model_validate(item) for item in items]

    @staticmethod
    def converter_do_to_vo(
        page_result: PageResult[object], vo_class: type[Model]
    ) -> PageResult[Model]:
        """复用 PageResult.convert，保留 items/total 契约。"""
        return page_result.convert(vo_class)
