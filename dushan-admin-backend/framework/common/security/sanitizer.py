import re
from typing import Any

from framework.common.security.serialized_sensitive_value_sanitizer import (
    SerializedSensitiveValueSanitizer,
)


class Sanitizer:
    """清理文本、响应数据和日志扩展字段中的已知敏感信息。

    sanitize_text 处理文本，sanitize_sensitive_data 处理响应数据；
    sanitize_log_message 和 sanitize_log_value 处理日志消息与扩展字段。
    日志中的未知对象只保留类型名称，循环引用会被标记；脱敏规则不能识别
    所有业务秘密，调用方仍应只传入展示或排错所需的信息。
    """

    _SENSITIVE_KEYWORDS = (
        "authorization",
        "authorization_header",
        "authorization_code",
        "cookie",
        "id_token",
        "idtoken",
        "access_token",
        "accesstoken",
        "refresh_token",
        "refreshtoken",
        "token",
        "password",
        "client_secret",
        "clientsecret",
        "secret",
        "secret_key",
        "secret_id",
        "app_secret_key",
        "api_key",
        "apikey",
        "credential",
        "verification_code",
        "verificationcode",
        "sms_code",
        "smscode",
        "captcha_code",
        "captchacode",
        "id_card",
        "idcard",
        "identity_number",
        "identitynumber",
        "identity_no",
        "identityno",
        "captcha_verification",
        "captchaverification",
        "point_json",
        "pointjson",
        "ticket",
        "randstr",
        "password_hash",
        "token_hash",
        "身份证",
        "验证码",
    )

    _SENSITIVE_FIELD_PATTERN = (
        r"authorization|set[-_]?cookie|cookie|client_secret|clientsecret|"
        r"access_token|accesstoken|refresh_token|refreshtoken|id_token|idtoken|"
        r"token|password|secret|api[_-]?key|credential|verification[_-]?code|"
        r"secret[_-]?(?:key|id)|app[_-]?secret[_-]?key|authorization[_-]?(?:code|header)|"
        r"verificationcode|sms[_-]?code|smscode|captcha[_-]?code|captchacode|"
        r"captcha[_-]?verification|captchaverification|point[_-]?json|pointjson|ticket|randstr|"
        r"id[_-]?card|idcard|identity[_-]?(?:number|no)|identitynumber|identityno|"
        r"验证码|身份证(?:号|号码)?"
    )

    _SENSITIVE_TEXT_PATTERN = re.compile(
        rf"(?i)\b({_SENSITIVE_FIELD_PATTERN})(\s*[:=：]\s*)([^&\s,;]+)"
    )

    _QUOTED_SENSITIVE_KEY_PATTERN = re.compile(
        rf"(?i)(?P<key_quote>[\"'])(?:{_SENSITIVE_FIELD_PATTERN})(?P=key_quote)\s*:"
    )

    _COOKIE_HEADER_PATTERN = re.compile(
        r"(?im)(^|[\s,{])(set[-_]?cookie|cookie)(\s*[:=：]\s*)[^\r\n]*"
    )

    _AUTHORIZATION_HEADER_PATTERN = re.compile(
        r"(?im)(^|[\s,{])(authorization)(\s*[:=：]\s*)[^\r\n]*"
    )

    _OAUTH_QUERY_SECRET_PATTERN = re.compile(r"(?i)([?&](?:code|state)=)[^&\s]+")

    _BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[^\s,;]+")

    _BASIC_AUTH_PATTERN = re.compile(r"(?i)\bbasic\s+[A-Za-z0-9+/]+={0,2}(?=$|[\s,;])")

    @staticmethod
    def sanitize_text(value: str) -> str:
        """脱敏字符串中的凭证、令牌和密钥片段。"""
        value = SerializedSensitiveValueSanitizer.sanitize(
            value, Sanitizer._QUOTED_SENSITIVE_KEY_PATTERN
        )
        value = Sanitizer._AUTHORIZATION_HEADER_PATTERN.sub(r"\1\2\3***", value)
        value = Sanitizer._COOKIE_HEADER_PATTERN.sub(r"\1\2\3***", value)
        value = Sanitizer._OAUTH_QUERY_SECRET_PATTERN.sub(r"\1***", value)
        value = Sanitizer._BEARER_PATTERN.sub("Bearer ***", value)
        value = Sanitizer._BASIC_AUTH_PATTERN.sub("Basic ***", value)
        return Sanitizer._SENSITIVE_TEXT_PATTERN.sub(r"\1\2***", value)

    @classmethod
    def sanitize_log_message(cls, message: str, extra: dict[object, object]) -> str:
        """清理最终 message，并遮盖已被格式化进去的敏感 extra 值。"""
        sanitized = cls.sanitize_text(message)
        sensitive_values: set[str] = set()
        redact_entire_message = cls._collect_sensitive_log_values(
            extra,
            sensitive_values,
            set(),
            collect_all=False,
        )
        if redact_entire_message:
            return "***"
        for sensitive_value in sorted(sensitive_values, key=len, reverse=True):
            if sensitive_value != "***":
                sanitized = cls._redact_sensitive_message_value(sanitized, sensitive_value)
        return sanitized

    @staticmethod
    def _redact_sensitive_message_value(message: str, sensitive_value: str) -> str:
        """遮盖消息中的敏感值，并避免短单词误伤较长的普通单词。"""
        if sensitive_value.isalnum():
            pattern = re.compile(rf"(?<!\w){re.escape(sensitive_value)}(?!\w)")
            return pattern.sub("***", message)
        return message.replace(sensitive_value, "***")

    @classmethod
    def _collect_sensitive_log_values(
        cls,
        value: object,
        values: set[str],
        visited: set[int],
        *,
        collect_all: bool,
    ) -> bool:
        """按值的结构收集待遮盖文本，并判断是否需要隐藏整条消息。"""
        if isinstance(value, dict):
            return cls._collect_sensitive_mapping(value, values, visited, collect_all=collect_all)
        if isinstance(value, (list, tuple, set)):
            return cls._collect_sensitive_sequence(value, values, visited, collect_all=collect_all)
        return cls._collect_sensitive_scalar(value, values, collect_all=collect_all)

    @classmethod
    def _collect_sensitive_mapping(
        cls,
        mapping: dict[object, object],
        values: set[str],
        visited: set[int],
        *,
        collect_all: bool,
    ) -> bool:
        """收集敏感字段及其嵌套内容，并跳过循环引用。"""
        mapping_id = id(mapping)
        if mapping_id in visited:
            return False
        visited.add(mapping_id)
        redact_entire_message = False
        try:
            for key, item in mapping.items():
                redact_entire_message = (
                    cls._collect_sensitive_log_values(
                        item,
                        values,
                        visited,
                        collect_all=collect_all or cls._is_sensitive_key(key, redact_input=False),
                    )
                    or redact_entire_message
                )
        finally:
            visited.remove(mapping_id)
        return redact_entire_message

    @classmethod
    def _collect_sensitive_sequence(
        cls,
        sequence: list[object] | tuple[object, ...] | set[object],
        values: set[str],
        visited: set[int],
        *,
        collect_all: bool,
    ) -> bool:
        """收集序列中的敏感值，并跳过循环引用。"""
        sequence_id = id(sequence)
        if sequence_id in visited:
            return False
        visited.add(sequence_id)
        redact_entire_message = False
        try:
            for item in sequence:
                redact_entire_message = (
                    cls._collect_sensitive_log_values(
                        item,
                        values,
                        visited,
                        collect_all=collect_all,
                    )
                    or redact_entire_message
                )
        finally:
            visited.remove(sequence_id)
        return redact_entire_message

    @staticmethod
    def _collect_sensitive_scalar(value: object, values: set[str], *, collect_all: bool) -> bool:
        """记录可安全匹配的敏感标量，未知对象要求隐藏整条消息。"""
        if not collect_all or isinstance(value, bool):
            return False
        if isinstance(value, str):
            if value:
                values.add(value)
            return False
        if isinstance(value, (int, float)):
            values.add(str(value))
            return False
        if isinstance(value, bytes):
            values.add(str(value))
            return False
        return value is not None

    @classmethod
    def sanitize_log_value(cls, value: object) -> object:
        """递归清理日志扩展字段，并把未知对象收敛为类型名称。"""
        return cls._sanitize_log_value(value, set())

    @classmethod
    def _sanitize_log_value(cls, value: object, visited: set[int]) -> object:
        """清理日志值并标记循环引用，不调用未知对象的字符串转换。"""
        if isinstance(value, dict):
            value_id = id(value)
            if value_id in visited:
                return "<recursive>"
            visited.add(value_id)
            try:
                sanitized: dict[str, object] = {}
                for key, item in value.items():
                    sanitized_key = cls._sanitize_log_key(key)
                    sanitized[sanitized_key] = (
                        "***"
                        if cls._is_sensitive_key(key, redact_input=False)
                        else cls._sanitize_log_value(item, visited)
                    )
                return sanitized
            finally:
                visited.remove(value_id)
        if isinstance(value, (list, tuple, set)):
            value_id = id(value)
            if value_id in visited:
                return "<recursive>"
            visited.add(value_id)
            try:
                return [cls._sanitize_log_value(item, visited) for item in value]
            finally:
                visited.remove(value_id)
        if isinstance(value, str):
            return cls.sanitize_text(value)
        if isinstance(value, BaseException):
            try:
                return cls.sanitize_text(str(value))
            except Exception:
                return f"<{type(value).__name__}>"
        if value is None or isinstance(value, (bool, int, float)):
            return value
        return f"<{type(value).__name__}>"

    @classmethod
    def _sanitize_log_key(cls, key: object) -> str:
        """清理日志键名，转换失败时仅保留键的类型。"""
        try:
            return cls.sanitize_text(str(key))
        except Exception:
            return f"<{type(key).__name__}>"

    @staticmethod
    def sanitize_sensitive_data(value: Any, redact_input: bool = False) -> Any:
        """递归脱敏映射、集合和字符串中的敏感数据。"""
        if isinstance(value, dict):
            return {
                key: (
                    "***"
                    if Sanitizer._is_sensitive_key(key, redact_input)
                    else Sanitizer.sanitize_sensitive_data(item, redact_input)
                )
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple, set)):
            return [Sanitizer.sanitize_sensitive_data(item, redact_input) for item in value]
        if isinstance(value, str):
            return Sanitizer.sanitize_text(value)
        return value

    @staticmethod
    def _is_sensitive_key(key: Any, redact_input: bool) -> bool:
        """判断字段名是否命中敏感字段规则。"""
        try:
            key_text = str(key)
        except Exception:
            return True
        normalized = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key_text).replace("-", "_").lower()
        normalized = re.split(r"[:=：]", normalized, maxsplit=1)[0].strip()
        if redact_input and normalized == "input":
            return True
        return any(
            normalized == keyword or normalized.endswith(f"_{keyword}")
            for keyword in Sanitizer._SENSITIVE_KEYWORDS
        )
