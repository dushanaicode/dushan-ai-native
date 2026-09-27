from framework.common.schemas import BaseVO


class MqConsumerRespVO(BaseVO):
    key: str
    topic: str
    retry_count: int
