from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.in_enum import InEnum
from framework.common.validator.not_empty import NotEmpty
from framework.common.validator.not_null import NotNull
from framework.common.validator.size import Size
from module_system.definitions.enums.announcement.announcement_category_enum import (
    AnnouncementCategoryEnum,
)


class AnnouncementSaveReqVO(BaseRequestVO):
    """管理后台 - 公告创建/修改 Request VO"""

    id: Annotated[SnowflakeIdInput | None, Field(None, description="公告编号")]
    title: Annotated[str, Field(..., description="公告标题")]
    content: Annotated[str, Field(..., description="公告内容")]
    is_top: Annotated[bool, Field(False, description="是否置顶")]
    status: Annotated[int, Field(..., description="状态，参见 AnnouncementStatusEnum 枚举类")]
    sort: Annotated[int, Field(0, description="排序序号（数值越小越靠前）")]
    publisher: Annotated[str, Field(..., min_length=1, max_length=64, description="发布人")]
    category: Annotated[int, Field(..., description="类别，参见 AnnouncementCategoryEnum 枚举类")]
    publish_time: Annotated[datetime | None, Field(None, description="发布时间")]
    expire_time: Annotated[datetime | None, Field(None, description="过期时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "1024",
                    "title": "系统升级通知",
                    "content": "系统将于2023年10月1日进行升级，届时将暂停服务2小时",
                    "isTop": True,
                    "status": 1,
                    "sort": 0,
                    "publisher": "张三",
                    "category": 1,
                    "publishTime": "2023-10-01T08:00:00Z",
                    "expireTime": "2023-10-10T08:00:00Z",
                }
            ]
        }
    }

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="title", value=v, error_msg="公告标题不能为空")
        Size.require_size(
            field_name="title",
            value=v,
            min_length=0,
            max_length=100,
            error_msg="公告标题不能超过100个字符",
        )
        return v

    @field_validator("content", mode="before")
    @classmethod
    def _validate_content(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="content", value=v, error_msg="公告内容不能为空")
        return v

    @field_validator("category", mode="before")
    @classmethod
    def _validate_category(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="category", value=v, error_msg="公告类别不能为空")
        InEnum.require_in_enum(
            field_name="category",
            value=v,
            enum_class=AnnouncementCategoryEnum,
            error_msg="公告类别必须在指定范围内",
        )
        return v
