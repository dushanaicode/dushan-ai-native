from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class ErrorCode:
    """定义不可变的应用错误码、中文默认提示和国际化消息键。

    例如 ErrorCode(code=1000, description="资源不存在", message_key="resource.missing")。
    framework 与业务模块共用本类型，编号唯一性由注册器检查。
    description 应能安全展示；HTTP 响应与异常诊断、重试策略不属于错误定义。
    """

    code: int
    description: str
    message_key: str

    def __post_init__(self) -> None:
        """校验编号和展示字段，不隐式转换外部输入。"""
        if type(self.code) is not int:
            raise TypeError("错误码必须是 int，不能是 bool 或其他类型")
        for name, value in (("description", self.description), ("message_key", self.message_key)):
            if not isinstance(value, str):
                raise TypeError(f"{name} 必须是字符串")
            if not value.strip():
                raise ValueError(f"{name} 不能为空或只有空白")

    def with_message_key(self, message_key: str) -> "ErrorCode":
        """创建相同编号和提示、使用另一翻译键的错误定义。"""
        return ErrorCode(code=self.code, description=self.description, message_key=message_key)
