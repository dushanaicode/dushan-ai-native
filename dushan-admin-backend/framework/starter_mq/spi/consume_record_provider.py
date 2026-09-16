from typing import Protocol

from framework.starter_mq.model.consume_record import ConsumeRecord


class ConsumeRecordProvider(Protocol):
    async def append(self, record: ConsumeRecord) -> None:
        """独立观测写入；不携带消息正文、证明或凭证，失败不重执业务。"""
        ...
