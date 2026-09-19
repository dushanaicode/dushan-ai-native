from dataclasses import dataclass
from uuid import uuid4

from pydantic import BaseModel

from framework.starter_mq.definitions.enums.message_mode import MessageMode


@dataclass(frozen=True, slots=True)
class PublishCommand:
    """消息 ID 可由业务幂等键确定；租户和身份不能由调用参数指定。"""

    destination: str
    mode: MessageMode
    message: BaseModel
    message_id: str | None = None
    capability: str | None = None

    def id(self) -> str:
        return uuid4().hex if self.message_id is None else self.message_id
