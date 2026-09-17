from framework.common.contracts.snowflake_id import SnowflakeIdInput
from framework.common.schemas.base_request_vo import BaseRequestVO


class IdReqVO(BaseRequestVO):
    id: SnowflakeIdInput
