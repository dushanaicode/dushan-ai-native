from pydantic import Field

from framework.common.contracts import SnowflakeIdInput
from framework.common.schemas import BaseRequestVO


class RoleIdsReqVO(BaseRequestVO):
    role_ids: list[SnowflakeIdInput] = Field(min_length=1)
