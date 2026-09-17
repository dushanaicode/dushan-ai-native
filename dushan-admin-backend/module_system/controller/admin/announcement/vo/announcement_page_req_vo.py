from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.page.schemas.page_query import PageQuery
from framework.common.validator.in_enum import InEnum
from module_system.definitions.enums.announcement.announcement_category_enum import (
    AnnouncementCategoryEnum,
)
from module_system.definitions.enums.announcement.announcement_status_enum import (
    AnnouncementStatusEnum,
)


class AnnouncementPageReqVO(PageQuery):
    """管理后台 - 公告分页列表 Request VO"""

    title: Annotated[str | None, Field(None, description="公告标题，模糊匹配")]
    status: Annotated[
        int | None, Field(None, description="状态，参见 AnnouncementStatusEnum 枚举类")
    ]
    is_top: Annotated[bool | None, Field(None, description="是否置顶")]
    category: Annotated[
        int | None, Field(None, description="类别，参见 AnnouncementCategoryEnum 枚举类")
    ]
    create_time: Annotated[
        list[datetime] | None, Field(None, exclude=True, description="创建时间范围")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "title": "系统升级",
                    "status": 1,
                    "isTop": True,
                    "category": 1,
                    "createTime": ["2020-05-20 05:20:00", "2020-05-20 13:14:00"],
                    "pageNo": 1,
                    "pageSize": 10,
                }
            ]
        }
    }

    @field_validator("status", mode="after")
    @classmethod
    def _validate_status(cls, v: Any) -> Any:
        if v is not None:
            InEnum.require_in_enum(
                field_name="status",
                value=v,
                enum_class=AnnouncementStatusEnum,
                error_msg="状态必须在指定范围",
            )
        return v

    @field_validator("category", mode="after")
    @classmethod
    def _validate_category(cls, v: Any) -> Any:
        if v is not None:
            InEnum.require_in_enum(
                field_name="category",
                value=v,
                enum_class=AnnouncementCategoryEnum,
                error_msg="类别必须在指定范围",
            )
        return v
