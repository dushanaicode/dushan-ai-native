from framework.common.contracts.snowflake_id import SnowflakeIdInput
from framework.common.schemas.base_request_vo import BaseRequestVO


class UserIdReqVO(BaseRequestVO):
    user_id: SnowflakeIdInput
