import json
import math
from typing import Any

from framework.starter_excel.model.conversion_context import ConversionContext


class JsonConverter:
    """严格 JSON 对象或数组；拒绝非有限数字、重复键和错误输入。"""

    async def to_excel(self, value: dict | list, context: ConversionContext) -> str:
        if not isinstance(value, (dict, list)):
            raise ValueError("JSON 字段必须是对象或数组")
        return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))

    async def to_python(self, value: str, context: ConversionContext) -> Any:
        parsed = json.loads(
            value,
            parse_constant=self._reject_constant,
            parse_float=self._float,
            object_pairs_hook=self._object,
        )
        if not isinstance(parsed, (dict, list)):
            raise ValueError("JSON 字段必须是对象或数组")
        return parsed

    @staticmethod
    def _float(value: str) -> float:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("JSON 不允许非有限数字")
        return number

    @staticmethod
    def _reject_constant(value: str) -> None:
        raise ValueError("JSON 不允许非有限数字")

    @staticmethod
    def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = dict(pairs)
        if len(result) != len(pairs):
            raise ValueError("JSON 对象不允许重复键")
        return result
