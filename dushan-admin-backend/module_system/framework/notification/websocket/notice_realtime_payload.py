from framework.common.contracts.snowflake_id import SnowflakeIdStr
from framework.common.schemas.base_vo import BaseVO


class NoticeRealtimePayload(BaseVO):
    message_id: SnowflakeIdStr
