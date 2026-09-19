from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.schemas import BaseVO
from framework.common.validator import NotEmpty


class Client(BaseVO):
    """管理后台 - OAuth2 客户端信息 VO"""

    name: Annotated[str, Field(..., description="应用名")]
    logo: Annotated[str, Field(default="", description="应用图标")]
    model_config = {
        "json_schema_extra": {
            "examples": [{"name": "渡山", "logo": "https://www.dushan.info/xx.png"}]
        }
    }

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="name", value=v, error_msg="应用名不能为空")
        return v
