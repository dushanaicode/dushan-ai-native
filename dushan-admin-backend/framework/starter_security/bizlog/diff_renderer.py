import inspect
import json
from collections import Counter

from pydantic import BaseModel

from framework.common.security.field_mask import FieldMask
from framework.common.security.sanitizer import Sanitizer
from framework.starter_security.bizlog.diff_field import DiffField
from framework.starter_security.config.security_settings import SecuritySettings


class DiffRenderer:
    """只比较声明过的字段；集合忽略顺序但保留重复次数，输出有明确上限。"""

    def __init__(self, settings: SecuritySettings, formatters=()):
        self.settings = settings
        self.formatters = {"_MASK": FieldMask(1, 1).apply}
        for name, function in formatters:
            if not name or name in self.formatters:
                raise ValueError("差异转换函数名称为空或重复")
            self.formatters[name] = function

    @classmethod
    def _project(cls, value):
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
        if type(before) is not type(after):
            raise TypeError("差异对象必须使用同一模型")
        source = Sanitizer.sanitize_log_value(self._project(before))
        target = Sanitizer.sanitize_log_value(self._project(after))
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
            if isinstance(old, list) or isinstance(new, list):
                if old is None or isinstance(old, list):
                    if new is None or isinstance(new, list):
                        old_items, new_items = self._items(old or []), self._items(new or [])
                        added, removed = new_items - old_items, old_items - new_items
                        if added or removed:
                            contents.append(
                                f"{info.name}: 添加 {await self._format_items(added, info)}；删除 {await self._format_items(removed, info)}"
                            )
                        continue
            contents.append(
                f"{info.name}: {await self._format(old, info)} → {await self._format(new, info)}"
            )
        limit = self.settings.bizlog_max_diff_items
        result = "；".join(contents[:limit])
        if len(contents) > limit or len(result) > self.settings.bizlog_max_length:
            result = (
                result[: self.settings.bizlog_max_length - len("[差异已截断]")] + "[差异已截断]"
            )
        return Sanitizer.sanitize_text(result)

    @staticmethod
    def _items(values):
        return Counter(json.dumps(value, ensure_ascii=False, sort_keys=True) for value in values)

    async def _format_items(self, values, info):
        return ", ".join(
            [
                f"{await self._format(json.loads(value), info)} (x{count})"
                for value, count in sorted(values.items())
            ]
        )

    async def _format(self, value, info):
        if info.formatter is not None and value is not None:
            result = self.formatters[info.formatter](value)
            value = await result if inspect.isawaitable(result) else result
        return str(Sanitizer.sanitize_log_value(value))
