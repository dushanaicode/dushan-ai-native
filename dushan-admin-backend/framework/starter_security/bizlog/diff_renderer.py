import inspect
from collections import Counter
from datetime import date, time, timedelta
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel
from pydantic_core import to_jsonable_python

from framework.common.security.field_mask import FieldMask
from framework.common.security.sanitizer import Sanitizer
from framework.starter_security.bizlog.diff_field import DiffField
from framework.starter_security.config.security_settings import SecuritySettings


class DiffRenderer:
    """只比较声明过的字段；集合忽略顺序但保留重复次数，输出有明确上限。"""

    def __init__(self, settings: SecuritySettings, formatters=()):
        """注册本次差异展示使用的内置和业务格式器。"""
        self.settings = settings
        self.formatters = {"_MASK": FieldMask(1, 1).apply}
        for name, function in formatters:
            if not name or name in self.formatters:
                raise ValueError("差异转换函数名称为空或重复")
            self.formatters[name] = function

    @classmethod
    def _project(cls, value):
        """递归提取显式声明字段，保留原始类型供比较与格式器使用。"""
        if isinstance(value, BaseModel):
            return {
                name: cls._project(getattr(value, name))
                for name, info in type(value).model_fields.items()
                if any(isinstance(item, DiffField) and not item.ignore for item in info.metadata)
                and not any(isinstance(item, DiffField) and item.ignore for item in info.metadata)
            }
        if isinstance(value, dict):
            return {name: cls._project(item) for name, item in value.items()}
        if isinstance(value, (list, tuple, set, frozenset)):
            return [cls._project(item) for item in value]
        return value

    async def render(self, before: BaseModel, after: BaseModel) -> str:
        """先比较真实值，再格式化与净化；展示相同时仍标明已变更。"""
        if type(before) is not type(after):
            raise TypeError("差异对象必须使用同一模型")
        source = self._project(before)
        target = self._project(after)
        contents = []
        for name in source:
            old, new = source[name], target[name]
            if old == new:
                continue
            info = next(
                item
                for item in type(before).model_fields[name].metadata
                if isinstance(item, DiffField)
            )
            if (old is None or isinstance(old, list)) and (new is None or isinstance(new, list)):
                added, removed = self._diff_items(
                    [] if old is None else old, [] if new is None else new
                )
                if not added and not removed:
                    continue
                added_text = await self._format_items(added, name, info)
                removed_text = await self._format_items(removed, name, info)
                content = (
                    f"{info.name}已变更"
                    if added_text == removed_text
                    else f"{info.name}: 添加 {added_text}；删除 {removed_text}"
                )
            else:
                old_text = await self._format(old, name, info)
                new_text = await self._format(new, name, info)
                content = (
                    f"{info.name}已变更"
                    if old_text == new_text
                    else f"{info.name}: {old_text} → {new_text}"
                )
            contents.append(content)
        limit = self.settings.bizlog_max_diff_items
        result = "；".join(contents[:limit])
        if len(contents) > limit or len(result) > self.settings.bizlog_max_length:
            result = (
                result[: self.settings.bizlog_max_length - len("[差异已截断]")] + "[差异已截断]"
            )
        return Sanitizer.sanitize_text(result)

    @staticmethod
    def _diff_items(before, after):
        """按原始值相等性逐个抵消集合元素，保留未抵消的增删及重复次数。"""
        # ponytail: 按相等性匹配为 O(n²)，大集合有实际需求时再设计类型保持的索引。
        removed = list(before)
        added = []
        for value in after:
            if value in removed:
                removed.remove(value)
            else:
                added.append(value)
        return added, removed

    async def _format_items(self, values, name, info):
        """只在差异确定后合并相同的安全展示文本。"""
        counts = Counter([await self._format(value, name, info) for value in values])
        return ", ".join(f"{value} (x{count})" for value, count in sorted(counts.items()))

    async def _format(self, value, name, info):
        """格式器接收真实值；未指定格式器的敏感字段只展示掩码。"""
        if info.formatter is not None and value is not None:
            result = self.formatters[info.formatter](value)
            value = await result if inspect.isawaitable(result) else result
        elif Sanitizer._is_sensitive_key(name, redact_input=False):
            return "***"
        return str(Sanitizer.sanitize_log_value(self._serialize(value)))

    @classmethod
    def _serialize(cls, value):
        """明确序列化模型标量，未知对象留给净化器隐藏，不调用其 repr。"""
        if isinstance(value, dict):
            return {name: cls._serialize(item) for name, item in value.items()}
        if isinstance(value, (list, tuple, set, frozenset)):
            return [cls._serialize(item) for item in value]
        if isinstance(value, (Decimal, date, time, timedelta, UUID, Enum)):
            return to_jsonable_python(value)
        return value
