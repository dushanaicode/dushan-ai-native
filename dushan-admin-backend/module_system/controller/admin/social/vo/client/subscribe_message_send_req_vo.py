from pydantic import Field, field_validator

from framework.common.contracts import SnowflakeIdInput
from framework.common.enums import UserTypeEnum
from framework.common.schemas import BaseRequestVO


class SubscribeMessageSendReqVO(BaseRequestVO):
    user_id: SnowflakeIdInput
    user_type: int
    template_title: str = Field(min_length=1)
    page: str | None = None
    messages: dict[str, str] | None = None

    @field_validator("user_type")
    @classmethod
    def validate_user_type(cls, value: int) -> int:
        return UserTypeEnum.from_code(value).code
