import re
from datetime import date

from pydantic_core import PydanticCustomError


class IDCard:
    """校验 18 位身份证的格式、出生日期和校验位，不替代实名核验。"""

    @staticmethod
    def require_id_card(
        field_name: str, value: str | None, error_msg: str | None = None
    ) -> str | None:
        """保持原值，允许末位 x；不猜测地址码是否已由行政区划分配。"""
        if value is None:
            return None
        message = (
            error_msg if error_msg is not None else f"{field_name} 身份证格式、日期或校验位不正确"
        )
        if not isinstance(value, str) or re.fullmatch(r"[1-9][0-9]{16}[0-9Xx]", value) is None:
            raise PydanticCustomError("value_error", message)
        try:
            date(int(value[6:10]), int(value[10:12]), int(value[12:14]))
        except ValueError as exc:
            raise PydanticCustomError("value_error", message) from exc
        weights = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
        expected = "10X98765432"[
            sum(int(char) * weight for char, weight in zip(value[:17], weights, strict=True)) % 11
        ]
        if value[-1].upper() != expected or value[14:17] == "000":
            raise PydanticCustomError("value_error", message)
        return value
