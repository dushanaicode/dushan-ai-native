from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MessageContext:
    """每次执行的非敏感定位信息；message_id 可供业务事务幂等使用。"""

    message_id: str
    consumer_key: str
    destination: str
    attempt: int
    tenant_id: str | None
