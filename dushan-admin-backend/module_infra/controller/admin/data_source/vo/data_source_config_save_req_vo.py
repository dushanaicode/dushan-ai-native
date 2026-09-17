from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.enums.status_enum import StatusEnum
from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.in_enum import InEnum
from framework.common.validator.not_empty import NotEmpty
from framework.common.validator.not_null import NotNull
from framework.common.validator.size import Size
from module_infra.definitions.enums.data_source.data_source_type_enum import DataSourceTypeEnum


class DataSourceConfigSaveReqVO(BaseRequestVO):
    """管理后台 - 数据源配置创建/修改 Request VO"""

    id: Annotated[SnowflakeIdInput | None, Field(None, description="数据源配置编号")]
    name: Annotated[str, Field(..., description="数据源名称")]
    url: Annotated[str | None, Field(None, description="数据源连接URL")]
    status: Annotated[int, Field(..., description="状态，参见 StatusEnum 枚举类")]
    db_type: Annotated[str, Field(..., description="数据库类型")]
    source_type: Annotated[
        int, Field(..., description="数据源类型，参见 DataSourceTypeEnum 枚举类")
    ]
    is_default: Annotated[bool, Field(False, description="是否默认数据源")]
    pool_size: Annotated[int, Field(10, description="连接池大小")]
    max_overflow: Annotated[int, Field(20, description="最大溢出连接数")]
    pool_recycle: Annotated[int, Field(3600, description="连接最大复用时间（秒）")]
    pool_timeout: Annotated[int, Field(30, description="获取连接最大等待时间（秒）")]
    echo: Annotated[bool, Field(False, description="是否开启SQL日志")]
    remark: Annotated[str | None, Field(None, description="备注")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "name": "主数据库",
                    "url": "mysql+aiomysql://root:123456@127.0.0.1:3306/test",
                    "status": 0,
                    "dbType": "mysql",
                    "sourceType": 1,
                    "isDefault": True,
                    "poolSize": 10,
                    "maxOverflow": 20,
                    "poolRecycle": 3600,
                    "poolTimeout": 30,
                    "echo": False,
                    "remark": "主数据库配置",
                }
            ]
        }
    }

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="name", value=v, error_msg="数据源名称不能为空")
        Size.require_size(
            field_name="name",
            value=v,
            min_length=0,
            max_length=100,
            error_msg="数据源名称长度不能超过100个字符",
        )
        return v

    @field_validator("url", mode="before")
    @classmethod
    def _validate_url(cls, v: Any) -> Any:
        if v is None:
            return v
        NotEmpty.require_not_empty(field_name="url", value=v, error_msg="数据源连接URL不能为空")
        Size.require_size(
            field_name="url",
            value=v,
            min_length=0,
            max_length=500,
            error_msg="数据源连接URL长度不能超过500个字符",
        )
        return v

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="status", value=v, error_msg="状态不能为空")
        InEnum.require_in_enum(
            field_name="status", value=v, enum_class=StatusEnum, error_msg="修改状态必须是 {values}"
        )
        return v

    @field_validator("source_type", mode="before")
    @classmethod
    def _validate_source_type(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="source_type", value=v, error_msg="数据源类型不能为空")
        InEnum.require_in_enum(
            field_name="source_type",
            value=v,
            enum_class=DataSourceTypeEnum,
            error_msg="数据源类型必须是 {values}",
        )
        return v
