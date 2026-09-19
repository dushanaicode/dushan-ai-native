from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.schemas import BaseDTO
from framework.common.validator import NotEmpty


class SocialWxQrcodeReqDTO(BaseDTO):
    """获取小程序码 Request DTO"""

    scene: Annotated[str | None, Field(default=None, description="场景")]
    path: Annotated[str | None, Field(default=None, description="页面路径")]
    width: Annotated[int | None, Field(default=430, description="二维码宽度")]
    auto_color: Annotated[bool | None, Field(default=True, description="是否需要透明底色")]
    check_path: Annotated[bool | None, Field(default=True, description="是否检查 page 是否存在")]
    hyaline: Annotated[bool | None, Field(default=True, description="是否需要透明底色")]

    @field_validator("scene", mode="before")
    @classmethod
    def _validate_scene(cls, v: Any) -> Any:
        return NotEmpty.require_not_empty(field_name="scene", value=v, error_msg="场景不能为空")

    @field_validator("path", mode="before")
    @classmethod
    def _validate_path(cls, v: Any) -> Any:
        return NotEmpty.require_not_empty(field_name="path", value=v, error_msg="页面路径不能为空")
