from collections.abc import Sequence
from typing import Any, Self

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class BaseVO(BaseModel):
    """定义面向 Web 的可验证数据，默认使用 camelCase 输出。

    Python 字段名和显式别名均可构造；未知字段拒绝，字符串原样保留。
    输入模型可继承 BaseRequestVO；输出字段由模型定义和 Field(exclude=True) 控制。
    例如 user_name 字段通过 to_response() 输出为 userName。
    批量输出使用 UserVO.list_to_response(items)，列表和元组均可传入。
    本类不做隐式脱敏、实体写回或任意运行时对象的序列化兜底。
    """

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        validate_assignment=True,
        validate_default=True,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
        loc_by_alias=True,
        alias_generator=to_camel,
    )

    def to_response(self) -> dict[str, Any]:
        """按模型声明转换为可输出的 camelCase JSON 数据。"""
        return self.model_dump(by_alias=True, mode="json")

    @classmethod
    def list_to_response(cls, items: Sequence[Self]) -> list[dict[str, Any]]:
        """逐项输出模型，不绕过各模型的字段序列化规则。"""
        return [item.to_response() for item in items]
