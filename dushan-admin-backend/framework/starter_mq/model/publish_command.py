from dataclasses import dataclass
from uuid import uuid4

from pydantic import BaseModel

from framework.starter_mq.definitions.enums.message_mode import MessageMode


@dataclass(frozen=True, slots=True)
class PublishCommand:
    """消息 ID 接受 32 位小写十六进制业务幂等键；租户和身份取自可信上下文。

    workload_capability 仅声明工作负载路径所需能力，会话发布不携带该能力。
    """

    destination: str
    mode: MessageMode
    message: BaseModel
    message_id: str | None = None
    workload_capability: str | None = None

    def id(self) -> str:
        return uuid4().hex if self.message_id is None else self.message_id
