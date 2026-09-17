from copy import deepcopy
from typing import Any

_SENSITIVE_KEY_PARTS = ("secret", "password", "privatekey", "credential", "token")
_SENSITIVE_KEY_NAMES = frozenset({"apikey", "accesskey", "signingkey"})


class SocialAuthConfigSecurity:
    @staticmethod
    def is_sensitive_auth_config_key(key: str) -> bool:
        """判断扩展认证配置字段是否承载凭据。"""
        normalized_key = "".join((character for character in key.lower() if character.isalnum()))
        return (
            any((part in normalized_key for part in _SENSITIVE_KEY_PARTS))
            or normalized_key in _SENSITIVE_KEY_NAMES
        )

    @staticmethod
    def contains_private_key(value: Any) -> bool:
        """识别未使用敏感字段名包装的私钥文本。"""
        return isinstance(value, str) and "PRIVATE KEY-----" in value.upper()

    @staticmethod
    def sanitize_auth_config(value: dict[str, Any]) -> dict[str, Any]:
        """递归移除管理端响应中的认证凭据。"""
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if SocialAuthConfigSecurity.is_sensitive_auth_config_key(
                key
            ) or SocialAuthConfigSecurity.contains_private_key(item):
                continue
            sanitized[key] = SocialAuthConfigSecurity._sanitize_value(item)
        return sanitized

    @staticmethod
    def validate_auth_config_secret_values(value: Any) -> None:
        """拒绝以空值表达新增或轮换的扩展认证凭据。"""
        if isinstance(value, dict):
            for key, item in value.items():
                if SocialAuthConfigSecurity.is_sensitive_auth_config_key(
                    key
                ) and SocialAuthConfigSecurity._is_blank_secret_value(item):
                    raise ValueError(f"认证配置敏感字段 {key} 不能为空")
                SocialAuthConfigSecurity.validate_auth_config_secret_values(item)
        elif isinstance(value, list):
            for item in value:
                SocialAuthConfigSecurity.validate_auth_config_secret_values(item)

    @staticmethod
    def merge_preserved_auth_config_secrets(
        existing: dict[str, Any], replacement: dict[str, Any]
    ) -> dict[str, Any]:
        """更新完整配置时补回管理端响应中已隐藏且未轮换的凭据。"""
        merged = deepcopy(replacement)
        for key, existing_value in existing.items():
            if SocialAuthConfigSecurity.is_sensitive_auth_config_key(
                key
            ) or SocialAuthConfigSecurity.contains_private_key(existing_value):
                if key not in replacement:
                    merged[key] = deepcopy(existing_value)
                continue
            replacement_value = replacement.get(key)
            if isinstance(existing_value, dict):
                if isinstance(replacement_value, dict):
                    merged[key] = SocialAuthConfigSecurity.merge_preserved_auth_config_secrets(
                        existing_value, replacement_value
                    )
                elif key not in replacement:
                    sensitive_values = SocialAuthConfigSecurity._extract_sensitive_values(
                        existing_value
                    )
                    if sensitive_values:
                        merged[key] = sensitive_values
            elif isinstance(existing_value, list) and isinstance(replacement_value, list):
                merged[key] = SocialAuthConfigSecurity._merge_list_secrets(
                    existing_value, replacement_value
                )
        return merged

    @staticmethod
    def _sanitize_value(value: Any) -> Any:
        if isinstance(value, dict):
            return SocialAuthConfigSecurity.sanitize_auth_config(value)
        if isinstance(value, list):
            return [
                SocialAuthConfigSecurity._sanitize_value(item)
                for item in value
                if not SocialAuthConfigSecurity.contains_private_key(item)
            ]
        return value

    @staticmethod
    def _is_blank_secret_value(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ""
        if isinstance(value, dict | list | tuple | set):
            return len(value) == 0
        return False

    @staticmethod
    def _extract_sensitive_values(value: dict[str, Any]) -> dict[str, Any]:
        sensitive_values: dict[str, Any] = {}
        for key, item in value.items():
            if SocialAuthConfigSecurity.is_sensitive_auth_config_key(
                key
            ) or SocialAuthConfigSecurity.contains_private_key(item):
                sensitive_values[key] = deepcopy(item)
            elif isinstance(item, dict):
                nested_values = SocialAuthConfigSecurity._extract_sensitive_values(item)
                if nested_values:
                    sensitive_values[key] = nested_values
            elif isinstance(
                item, list
            ) and SocialAuthConfigSecurity._list_contains_sensitive_values(item):
                sensitive_values[key] = deepcopy(item)
        return sensitive_values

    @staticmethod
    def _list_contains_sensitive_values(value: list[Any]) -> bool:
        return any(
            (
                SocialAuthConfigSecurity.contains_private_key(item)
                or (
                    isinstance(item, dict)
                    and bool(SocialAuthConfigSecurity._extract_sensitive_values(item))
                )
                or (
                    isinstance(item, list)
                    and SocialAuthConfigSecurity._list_contains_sensitive_values(item)
                )
                for item in value
            )
        )

    @staticmethod
    def _merge_list_secrets(existing: list[Any], replacement: list[Any]) -> list[Any]:
        merged = deepcopy(replacement)
        for index, existing_item in enumerate(existing):
            if index >= len(merged):
                if SocialAuthConfigSecurity.contains_private_key(existing_item):
                    merged.append(deepcopy(existing_item))
                continue
            replacement_item = merged[index]
            if isinstance(existing_item, dict) and isinstance(replacement_item, dict):
                merged[index] = SocialAuthConfigSecurity.merge_preserved_auth_config_secrets(
                    existing_item, replacement_item
                )
            elif isinstance(existing_item, list) and isinstance(replacement_item, list):
                merged[index] = SocialAuthConfigSecurity._merge_list_secrets(
                    existing_item, replacement_item
                )
        return merged
