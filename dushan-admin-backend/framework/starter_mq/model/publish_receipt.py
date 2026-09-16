from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class PublishReceipt:
    """Broker 确认不代表消费者已处理，Pub/Sub 仅确认在线分发。"""

    message_id: str
    confirmation: Literal["stream_entry", "publisher_confirm", "partition_offset", "broadcast"]
    broker_reference: str
