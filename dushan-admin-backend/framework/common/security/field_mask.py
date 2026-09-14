from dataclasses import dataclass
from typing import Annotated

from pydantic import PlainSerializer


@dataclass(frozen=True, slots=True)
class FieldMask:
    """字段展示脱敏；不改变模型原始值，不承担日志净化或请求鉴权。"""

    prefix: int
    suffix: int

    def __post_init__(self) -> None:
        if type(self.prefix) is not int or type(self.suffix) is not int:
            raise TypeError("保留长度必须是整数")
        if self.prefix < 0 or self.suffix < 0:
            raise ValueError("保留长度不能为负数")

    def apply(self, value: str) -> str:
        masked = len(value) - self.prefix - self.suffix
        if masked <= 0:
            return "*" * len(value)
        suffix = value[-self.suffix :] if self.suffix else ""
        return value[: self.prefix] + "*" * masked + suffix

    @staticmethod
    def email(value: str) -> str:
        if not value:
            return value
        local, separator, domain = value.partition("@")
        if not separator or not local or not domain:
            return "****"
        return f"{local[0]}****@{domain}"


DesensitizedApiKey = Annotated[str, PlainSerializer(FieldMask(4, 4).apply, return_type=str)]
DesensitizedBankCard = Annotated[str, PlainSerializer(FieldMask(6, 2).apply, return_type=str)]
DesensitizedCarLicense = Annotated[str, PlainSerializer(FieldMask(3, 1).apply, return_type=str)]
DesensitizedChineseName = Annotated[str, PlainSerializer(FieldMask(1, 0).apply, return_type=str)]
DesensitizedFixedPhone = Annotated[str, PlainSerializer(FieldMask(4, 2).apply, return_type=str)]
DesensitizedIdCard = Annotated[str, PlainSerializer(FieldMask(6, 2).apply, return_type=str)]
DesensitizedMobile = Annotated[str, PlainSerializer(FieldMask(3, 4).apply, return_type=str)]
DesensitizedPassword = Annotated[str, PlainSerializer(FieldMask(0, 0).apply, return_type=str)]
DesensitizedEmail = Annotated[str, PlainSerializer(FieldMask.email, return_type=str)]
