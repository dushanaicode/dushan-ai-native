from dataclasses import dataclass
from http import HTTPStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class ErrorCode:
    """定义不可变的错误码、中文默认提示和国际化消息键。

    例如 ErrorCode(code=1000, description="资源不存在", message_key="resource.missing")。
    业务异常持有本对象；description 应能安全展示，message_key 用于查找翻译。
    http_status 是可选的传输状态，不从 code 自动推导；编号唯一性由注册器检查。
    """

    code: int
    description: str
    message_key: str
    http_status: int | HTTPStatus | None = None

    def __post_init__(self) -> None:
        """校验错误码类型、非空提示和可选 HTTP 状态，不转换外部输入。"""
        if type(self.code) is not int:
            raise TypeError("错误码必须是 int，不能是 bool 或其他类型")
        for name, value in (("description", self.description), ("message_key", self.message_key)):
            if not isinstance(value, str):
                raise TypeError(f"{name} 必须是字符串")
            if not value.strip():
                raise ValueError(f"{name} 不能为空或只有空白")
        if self.http_status is not None:
            if isinstance(self.http_status, bool) or not isinstance(self.http_status, int):
                raise TypeError("http_status 必须是整数 HTTP 状态")
            if not 100 <= self.http_status <= 599:
                raise ValueError("http_status 必须在 100～599 之间")

    def with_message_key(self, message_key: str) -> "ErrorCode":
        """创建一个相同 code、不同 message_key 的 ErrorCode。"""
        return ErrorCode(
            code=self.code,
            description=self.description,
            message_key=message_key,
            http_status=self.http_status,
        )
