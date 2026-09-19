from pydantic import BaseModel, ConfigDict

from framework.starter_mq.definitions.enums.message_mode import MessageMode
from framework.starter_mq.model.message_envelope import MessageEnvelope


class PreparedMessage(BaseModel):
    """可写入业务 outbox 的固定传输数据，不包含可执行类型或序列化对象。"""

    model_config = ConfigDict(frozen=True, extra="forbid")
    mode: MessageMode
    envelope: MessageEnvelope
