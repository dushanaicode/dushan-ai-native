import re
from typing import Annotated

from pydantic import BeforeValidator, WithJsonSchema

SIGNED_BIGINT_MAX = (1 << 63) - 1
ID_SCHEMA = {"type": "string", "pattern": "^[1-9][0-9]{0,18}$"}


class SnowflakeId:
    """将可选采用的雪花整数与 API 十进制字符串衔接，避免 JavaScript 整数精度丢失。

    请求声明 SnowflakeIdInput，响应声明 SnowflakeIdStr；不改变其他业务 ID 类型。
    只校验编码范围，不证明来源或权限，游标单独允许字符串或整数零。
    """

    @staticmethod
    def format(value: object) -> str:
        """只接受正整数或规范十进制字符串，拒绝布尔、前导零和超范围值。"""
        if type(value) is int:
            number = value
        elif isinstance(value, str) and re.fullmatch(r"[1-9][0-9]{0,18}", value):
            number = int(value)
        else:
            raise ValueError("ID 必须是正整数或规范十进制字符串")
        if not 0 < number <= SIGNED_BIGINT_MAX:
            raise ValueError("ID 超出正有符号 64 位整数范围")
        return str(number)

    @classmethod
    def parse_input(cls, value: object) -> int:
        """请求只接受字符串，禁止先经过 JavaScript Number 再提交数字。"""
        if not isinstance(value, str):
            raise ValueError("请求 ID 必须是十进制字符串")
        return int(cls.format(value))

    @classmethod
    def format_cursor(cls, value: object) -> str:
        """额外接受明确的整数零或字符串零，不将 False 识别为游标零。"""
        if type(value) is int and value == 0 or type(value) is str and value == "0":
            return "0"
        return cls.format(value)


SnowflakeIdStr = Annotated[str, BeforeValidator(SnowflakeId.format)]
SnowflakeIdInput = Annotated[
    int, BeforeValidator(SnowflakeId.parse_input), WithJsonSchema(ID_SCHEMA)
]
SnowflakeCursorStr = Annotated[str, BeforeValidator(SnowflakeId.format_cursor)]
