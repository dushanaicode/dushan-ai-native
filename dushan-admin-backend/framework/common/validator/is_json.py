from pydantic_core import PydanticCustomError

from framework.common.utils.json.json_utils import JsonUtils


class IsJSON:
    """校验严格 JSON 字符串，不改变字符串值。"""

    @staticmethod
    def require_json(
        field_name: str, value: str | None, error_msg: str | None = None
    ) -> str | None:
        """拒绝空串、重复键和非标准数值。"""
        if value is None:
            return None
        if not isinstance(value, str) or not JsonUtils.is_valid_json(value):
            raise PydanticCustomError(
                "value_error",
                error_msg if error_msg is not None else f"{field_name} 必须是合法 JSON",
            )
        return value
