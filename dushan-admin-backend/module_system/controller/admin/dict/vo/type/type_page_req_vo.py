from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.page import PageQuery
from framework.common.validator import Size


class DictTypePageReqVO(PageQuery):
    """管理后台 - 字典类型分页列表 Request VO"""

    name: Annotated[str | None, Field(None, description="字典类型名称，模糊匹配")]
    type: Annotated[str | None, Field(None, description="字典类型，模糊匹配")]
    status: Annotated[int | None, Field(None, description="展示状态，参见 StatusEnum 枚举类")]
    create_time: Annotated[
        list[datetime] | None, Field(None, exclude=True, description="创建时间范围")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "渡山",
                    "type": "sys_common_sex",
                    "status": 1,
                    "createTime": ["2020-05-20T05:20:00Z", "2022-07-01T23:59:59Z"],
                }
            ]
        }
    }

    @field_validator("type", mode="before")
    @classmethod
    def _validate_type(cls, v: Any) -> Any:
        if v is not None:
            Size.require_size(
                field_name="type",
                value=v,
                min_length=0,
                max_length=100,
                error_msg="字典类型类型长度不能超过100个字符",
            )
        return v
