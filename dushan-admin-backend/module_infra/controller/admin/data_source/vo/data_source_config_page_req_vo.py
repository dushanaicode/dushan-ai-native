from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.enums.status_enum import StatusEnum
from framework.common.page.schemas.page_query import PageQuery
from framework.common.validator.in_enum import InEnum
from framework.common.validator.size import Size
from module_infra.definitions.enums.data_source.data_source_type_enum import DataSourceTypeEnum


class DataSourceConfigPageReqVO(PageQuery):
    """管理后台 - 数据源配置分页列表 Request VO"""

    name: Annotated[str | None, Field(None, description="数据源名称，模糊匹配")]
    status: Annotated[int | None, Field(None, description="状态，参见 StatusEnum 枚举类")]
    db_type: Annotated[str | None, Field(None, description="数据库类型")]
    source_type: Annotated[
        int | None, Field(None, description="数据源类型，参见 DataSourceTypeEnum 枚举类")
    ]
    create_time: Annotated[
        list[datetime] | None, Field(None, exclude=True, description="创建时间范围")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "主数据库",
                    "status": 0,
                    "dbType": "mysql",
                    "sourceType": 1,
                    "createTime": ["2023-01-01T00:00:00", "2023-12-31T23:59:59"],
                }
            ]
        }
    }

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> Any:
        if v is not None:
            Size.require_size(
                field_name="name",
                value=v,
                min_length=0,
                max_length=100,
                error_msg="数据源名称长度不能超过100个字符",
            )
        return v

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: Any) -> Any:
        if v is not None:
            InEnum.require_in_enum(field_name="status", value=v, enum_class=StatusEnum)
        return v

    @field_validator("source_type", mode="before")
    @classmethod
    def _validate_source_type(cls, v: Any) -> Any:
        if v is not None:
            InEnum.require_in_enum(field_name="source_type", value=v, enum_class=DataSourceTypeEnum)
        return v
