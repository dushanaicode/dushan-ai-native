from pydantic import Field

from framework.common.contracts.snowflake_id import SnowflakeIdInput
from framework.common.schemas.base_request_vo import BaseRequestVO


class RoleIdsReqVO(BaseRequestVO):
    role_ids: list[SnowflakeIdInput] = Field(min_length=1)
