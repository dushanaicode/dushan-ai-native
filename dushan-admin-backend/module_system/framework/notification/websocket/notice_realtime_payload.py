from framework.common.contracts import SnowflakeIdStr
from framework.common.schemas import BaseVO


class NoticeRealtimePayload(BaseVO):
    message_id: SnowflakeIdStr
