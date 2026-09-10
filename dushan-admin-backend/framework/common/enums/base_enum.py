from enum import Enum, unique
from typing import Self


class BaseEnum(Enum):
    """定义带显示名称的业务枚举。

    成员按 (编码, 名称) 填写，例如 ENABLE = (1, "开启")。
    同一组编码类型要一致，编码和名称都不能重复。
    外部输入通过 from_code 校验，页面展示读取 label。
    编码用于存储和传输，修改显示名称时保持编码不变。
    """

    _value_: int | str
    _label_: str

    def __new__(cls, code: int | str, label: str) -> Self:
        # True 和 1 在 Python 中相等，这里必须先检查类型。
        if type(code) not in (int, str):
            raise TypeError("枚举编码必须是 int 或 str，不能是 bool 或其他类型")
        if isinstance(code, str) and (not code or code != code.strip()):
            raise ValueError("字符串枚举编码不能为空或包含首尾空白")
        if not isinstance(label, str):
            raise TypeError("枚举标签必须是字符串")
        if not label or label != label.strip():
            raise ValueError("枚举标签不能为空或包含首尾空白")

        member = object.__new__(cls)
        member._value_ = code
        member._label_ = label
        return member

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        # Enum 会把重复编码当成同一个成员，这里直接报错。
        unique(cls)
        if len({type(member.code) for member in cls}) > 1:
            raise TypeError(f"{cls.__name__} 的编码不能混用整数和字符串")
        labels = [member.label for member in cls]
        if len(labels) != len(set(labels)):
            raise ValueError(f"{cls.__name__} 的标签不能重复")

    @property
    def code(self) -> int | str:
        """返回业务编码，与 value 相同。"""
        return self._value_

    @property
    def label(self) -> str:
        """返回页面上显示的名称。"""
        return self._label_

    @classmethod
    def get_by_code(cls, code: object) -> Self | None:
        """按编码查找，类型不符或找不到时返回 None。"""
        if type(code) not in (int, str):
            return None
        try:
            return cls(code)
        except ValueError:
            return None

    @classmethod
    def from_code(cls, value: object) -> Self:
        """把编码转成枚举成员，已有的本类成员可以直接传入。

        不会把 True、1.0 或 "1" 当成整数编码 1；校验失败时抛出 ValueError。
        接口字段可写成 Annotated[StatusEnum, BeforeValidator(StatusEnum.from_code)]。
        只标注 StatusEnum 类型时，Pydantic 仍会使用自己的转换规则。
        错误文案不附带传入的值，避免把请求中的敏感内容带出去。
        """
        if isinstance(value, cls):
            return value
        member = cls.get_by_code(value)
        if member is None:
            raise ValueError(f"{cls.__name__} 编码无效，请使用定义中的整数或字符串编码")
        return member

    @classmethod
    def get_by_label(cls, label: object) -> Self | None:
        """按显示名称原样查找，找不到时返回 None。"""
        if not isinstance(label, str):
            return None
        return next((member for member in cls if member.label == label), None)

    @classmethod
    def choices(cls) -> list[tuple[int | str, str]]:
        """按定义顺序列出 (编码, 显示名称)。"""
        return [(member.code, member.label) for member in cls]

    def __str__(self) -> str:
        """返回编码的字符串形式。"""
        return str(self._value_)
