from pydantic import field_validator

from framework.common.contracts.snowflake_id import SnowflakeIdInput
from framework.common.enums.status_enum import StatusEnum
from framework.common.schemas.base_request_vo import BaseRequestVO


class UpdateStatusReqVO(BaseRequestVO):
    id: SnowflakeIdInput
    status: int

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, value: object) -> int:
        return StatusEnum.from_code(value).code
