from collections.abc import Callable
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from framework.common.schemas.base_vo import BaseVO

T = TypeVar("T")
V = TypeVar("V")
Model = TypeVar("Model", bound=BaseModel)


class PageResult(BaseVO, Generic[T]):
    """用 items/total 返回分页数据，与前端表格列表契约一致。

    items 可以为空而 total 非零，表示请求页超出范围；总数始终是已知的非负整数。
    map 用于普通转换函数，convert 用于有明确字段声明的 Pydantic 响应模型。
    """

    items: list[T] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)

    @classmethod
    def empty(cls, total: int = 0) -> "PageResult[T]":
        """构建空页并保留查询得到的总数。"""
        return cls(items=[], total=total)

    def map(self, converter: Callable[[T], V]) -> "PageResult[V]":
        """按转换函数映射元素，不改变总数。"""
        return PageResult[V](items=[converter(item) for item in self.items], total=self.total)

    def convert(self, model: type[Model]) -> "PageResult[Model]":
        """按目标模型校验每个元素，属性读取由目标模型的配置决定。"""
        return PageResult[model](
            items=[model.model_validate(item) for item in self.items], total=self.total
        )
