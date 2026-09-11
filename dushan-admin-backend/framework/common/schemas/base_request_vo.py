import re
from collections.abc import Mapping, Set
from types import MappingProxyType
from typing import Any, ClassVar, cast

from pydantic import ConfigDict, SecretStr, ValidationInfo, field_validator

from framework.common.schemas.base_vo import BaseVO


class BaseRequestVO(BaseVO):
    r"""校验 Web 请求，并通过明确的字段白名单提取写入数据。

    masked_patterns 按 Python 字段名声明完整占位模式，例如
    {"mobile": r"\d{3}\*{4}\d{4}"}；匹配后拒绝输入，不把字段改为 None。
    未提供字段与显式 None 保持区别，to_write_dict(fields={...}) 默认只取已提供字段。
    例如 ContactPatchVO(mobile=None).to_write_dict(fields={"mobile"}) 返回 {"mobile": None}。
    白名单使用 Python 字段名；SecretStr 保持封装，嵌套值遵循字段自身的序列化规则。
    白名单只决定可提取字段；鉴权、哈希、实体映射与事务仍由业务服务负责。
    """

    model_config = ConfigDict(from_attributes=False)
    masked_patterns: ClassVar[Mapping[str, str]] = MappingProxyType({})

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """在模型定义完成后检查字段策略，并冻结当前类自己的配置副本。"""
        super().__pydantic_init_subclass__(**kwargs)
        patterns = dict(cls.masked_patterns)
        for name, pattern in patterns.items():
            if name not in cls.model_fields:
                raise ValueError(f"脱敏占位策略引用了未声明字段: {name}")
            if not pattern:
                raise ValueError(f"脱敏占位模式不能为空: {name}")
            try:
                re.compile(pattern)
            except re.error as error:
                raise ValueError(f"脱敏占位模式无效: {name}") from error
        cls.masked_patterns = MappingProxyType(patterns)

    @field_validator("*", mode="after")
    @classmethod
    def reject_masked_placeholder(cls, value: Any, info: ValidationInfo) -> Any:
        """拒绝配置字段的完整掩码占位值，保留正常字符串与原有字段类型。"""
        pattern = cls.masked_patterns.get(cast(str, info.field_name))
        text = value.get_secret_value() if isinstance(value, SecretStr) else value
        if pattern is not None and isinstance(text, str) and re.fullmatch(pattern, text):
            raise ValueError("不能提交脱敏占位值，请提供真实值或省略该字段")
        return value

    def to_write_dict(self, *, fields: Set[str], exclude_unset: bool = True) -> dict[str, Any]:
        """按 Python 字段白名单提取数据，显式空值不会变成未提供字段。"""
        selected = set(fields)
        if selected - type(self).model_fields.keys():
            raise ValueError("写入白名单只能包含模型声明的 Python 字段名")
        return self.model_dump(
            mode="python", by_alias=False, include=selected, exclude_unset=exclude_unset
        )
