import re
from typing import TypeVar
from urllib.parse import urlsplit

from pydantic import BaseModel, HttpUrl, TypeAdapter, ValidationError

Model = TypeVar("Model", bound=BaseModel)


class ValidationUtils:
    """提供格式判断和显式模型校验，不通过反射猜测对象的必填字段。"""

    _email = re.compile(
        r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}"
    )
    _http_url = TypeAdapter(HttpUrl)

    @staticmethod
    def validate_mobile(mobile: str) -> bool:
        """判断中国大陆手机号的基本外形，不维护会变化的运营商号段清单。"""
        return re.fullmatch(r"1[3-9][0-9]{9}", mobile) is not None

    @classmethod
    def validate_email(cls, email: str) -> bool:
        """检查常见 ASCII 邮箱格式，不声称覆盖全部 RFC 语法或地址真实性。"""
        local, separator, _ = email.partition("@")
        return (
            bool(separator)
            and len(email) <= 254
            and len(local) <= 64
            and cls._email.fullmatch(email) is not None
        )

    @classmethod
    def is_url(cls, url: str) -> bool:
        """判断完整 HTTP(S) URL，禁止控制字符、空白、反斜杠和内嵌凭据。"""
        if (
            not url
            or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in url)
            or "\\" in url
        ):
            return False
        try:
            parsed = urlsplit(url)
            if (
                parsed.scheme.lower() not in ("http", "https")
                or not parsed.netloc
                or parsed.username is not None
                or parsed.password is not None
            ):
                return False
            cls._http_url.validate_python(url)
        except (ValueError, ValidationError):
            return False
        return True

    @staticmethod
    def is_xml_ncname(value: str) -> bool:
        """检查 ASCII NCName 子集；冒号、美元符号和非 ASCII 字符不在本契约中。"""
        return re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", value) is not None

    @staticmethod
    def validate(data: object, model_class: type[Model]) -> Model:
        """通过调用方指定的 Pydantic 模型验证数据。"""
        return model_class.model_validate(data)
