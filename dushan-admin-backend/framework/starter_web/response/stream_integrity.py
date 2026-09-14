from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class StreamIntegrity:
    """业务声明的完整性协议；发送方与消费方实现验证，Web 不注入或解析流内容。"""

    ATTRIBUTE: ClassVar[str] = "__stream_integrity__"
    protocol: str
    completion_marker: str | None = None

    def __post_init__(self) -> None:
        if not self.protocol.strip() or any(char in self.protocol for char in "\r\n"):
            raise ValueError("流完整性协议必须有明确名称")
        if self.completion_marker is not None and not self.completion_marker:
            raise ValueError("流结束标记不能为空")

    def __call__(self, owner):
        previous = getattr(owner, self.ATTRIBUTE, None)
        if previous is not None and previous != self:
            raise ValueError("流完整性声明冲突")
        setattr(owner, self.ATTRIBUTE, self)
        return owner
