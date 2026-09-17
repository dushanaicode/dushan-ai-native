from pydantic import Field, field_validator

from framework.common.schemas.base_request_vo import BaseRequestVO
from module_system.definitions.enums.social.social_type_enum import SocialTypeEnum


class SocialUserBindReqVO(BaseRequestVO):
    type: int
    code: str = Field(min_length=1)
    state: str

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: int) -> int:
        return SocialTypeEnum.from_code(value).code
