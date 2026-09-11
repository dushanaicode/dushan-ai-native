import json
import re
from collections.abc import Callable, Sequence
from typing import Any, ClassVar

from framework.common.exception.core.error_details import ErrorDetails
from framework.common.exception.core.field_error import FieldError
from framework.common.security.sanitizer import Sanitizer


class ValidationErrorMapper:
    """将请求校验明细转换为表单可读取的公开字段错误。

    不输出input、ctx、url或异常对象；body/query前缀移除，其他请求位置保留。
    例如('body', 'contacts', 0, 'mobile')转换为contacts[0].mobile。
    """

    messages: ClassVar[dict[str, str]] = {
        "required": "此项为必填项",
        "invalid_type": "值的类型不正确",
        "invalid_format": "格式不正确",
        "invalid_choice": "请选择允许的值",
        "extra_field": "不允许提交此字段",
        "too_short": "长度至少为 {0}",
        "too_long": "长度最多为 {0}",
        "greater_than": "数值必须大于 {0}",
        "greater_than_equal": "数值不能小于 {0}",
        "less_than": "数值必须小于 {0}",
        "less_than_equal": "数值不能大于 {0}",
        "invalid_value": "输入值不符合要求",
    }

    @classmethod
    def map(
        cls,
        errors: Sequence[dict[str, Any]],
        translate: Callable[[str, str, Sequence[Any] | None], str],
    ) -> ErrorDetails:
        """保留每个字段的全部错误，文案由当前请求的翻译函数生成。"""
        fields = []
        for error in errors:
            kind = error["type"]
            arguments = None
            if kind == "missing":
                key = "required"
            elif kind == "extra_forbidden":
                key = "extra_field"
            elif kind in ("enum", "literal_error"):
                key = "invalid_choice"
            elif kind in ("greater_than", "greater_than_equal", "less_than", "less_than_equal"):
                key = kind
                bound = {
                    "greater_than": "gt",
                    "greater_than_equal": "ge",
                    "less_than": "lt",
                    "less_than_equal": "le",
                }[kind]
                arguments = (error["ctx"][bound],)
            elif kind in ("string_too_short", "bytes_too_short", "too_short"):
                key, arguments = "too_short", (error["ctx"]["min_length"],)
            elif kind in ("string_too_long", "bytes_too_long", "too_long"):
                key, arguments = "too_long", (error["ctx"]["max_length"],)
            elif kind in ("string_pattern_mismatch", "url_parsing", "uuid_parsing", "json_invalid"):
                key = "invalid_format"
            elif kind.endswith(("_type", "_parsing")):
                key = "invalid_type"
            else:
                key = "invalid_value"
            message = cls.messages[key]
            if arguments:
                message = message.format(*arguments)
            # 自定义校验器的msg是其公开提示契约；仍经过统一脱敏。
            if kind == "value_error":
                message = error["msg"]
            else:
                message = translate(f"validation.{key}", message, arguments)
            fields.append(
                FieldError(
                    field=cls.field_path(error["loc"]), message=Sanitizer.sanitize_text(message)
                )
            )
        return ErrorDetails(fields=tuple(fields))

    @staticmethod
    def field_path(location: Sequence[str | int]) -> str:
        """生成Vben支持的字段路径，带点或引号的字段名使用括号引用。"""
        parts = location[1:] if location and location[0] in ("body", "query") else location
        result = ""
        for part in parts:
            if isinstance(part, int):
                result += f"[{part}]"
            elif re.fullmatch(r"[A-Za-z_$][\w$]*", part):
                result += f".{part}" if result else part
            else:
                result += f"[{json.dumps(part, ensure_ascii=False)}]"
        return result
