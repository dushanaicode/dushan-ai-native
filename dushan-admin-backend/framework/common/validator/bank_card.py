import re

from pydantic_core import PydanticCustomError


class BankCard:
    """校验 16～19 位卡号格式与 Luhn 校验位，不验证发卡或账户真实性。"""

    @classmethod
    def require_bank_card(
        cls, field_name: str, value: str | None, error_msg: str | None = None
    ) -> str | None:
        """仅接受 ASCII 数字，并验证校验位。"""
        if value is None:
            return None
        if (
            not isinstance(value, str)
            or re.fullmatch(r"[0-9]{16,19}", value) is None
            or not cls._passes_luhn(value)
        ):
            raise PydanticCustomError(
                "value_error",
                error_msg if error_msg is not None else f"{field_name} 卡号格式或校验位不正确",
            )
        return value

    @staticmethod
    def _passes_luhn(value: str) -> bool:
        """从最右侧起每隔一位加倍并求和校验。"""
        total = 0
        for index, character in enumerate(reversed(value)):
            digit = int(character)
            if index % 2:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
        return total % 10 == 0
