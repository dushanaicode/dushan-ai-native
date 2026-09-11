from ipaddress import AddressValueError, IPv4Address

from pydantic_core import PydanticCustomError


class IPV4:
    """校验 IPv4 地址文本，None 表示未填写的可选值。"""

    @staticmethod
    def require_ipv4(
        field_name: str, value: str | None, error_msg: str | None = None
    ) -> str | None:
        """通过标准库检查地址，拒绝整数和前导零形式。"""
        if value is None:
            return None
        message = error_msg if error_msg is not None else f"{field_name} 必须是 IPv4 地址"
        if not isinstance(value, str):
            raise PydanticCustomError("value_error", message)
        try:
            IPv4Address(value)
        except AddressValueError as exc:
            raise PydanticCustomError("value_error", message) from exc
        return value
