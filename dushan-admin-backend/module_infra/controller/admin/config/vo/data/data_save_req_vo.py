from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.not_null import NotNull
from framework.common.validator.size import Size


class ConfigDataSaveReqVO(BaseRequestVO):
    """管理后台 - 配置数据创建/修改 Request VO"""

    id: Annotated[SnowflakeIdInput | None, Field(None, description="参数配置序号")]
    type_id: Annotated[SnowflakeIdInput, Field(..., description="配置类型ID")]
    name: Annotated[str, Field(..., description="参数名称", max_length=100)]
    key: Annotated[str, Field(..., description="参数键名", max_length=100)]
    value: Annotated[str, Field(..., description="参数键值", max_length=500)]
    description: Annotated[str | None, Field(None, description="配置描述", max_length=500)]
    input_type: Annotated[str | None, Field(None, description="UI控件类型", max_length=20)]
    input_props: Annotated[str | None, Field(None, description="UI控件属性JSON")]
    sort: Annotated[int, Field(0, description="显示顺序")]
    visible: Annotated[bool, Field(..., description="是否可见")]
    remark: Annotated[str | None, Field(None, description="备注")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "typeId": 1,
                    "name": "数据库名",
                    "key": "dushan.db.username",
                    "value": "1024",
                    "visible": True,
                    "remark": "备注",
                }
            ]
        }
    }

    @field_validator("type_id", mode="before")
    @classmethod
    def _validate_type_id(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="type_id", value=v, error_msg="配置类型不能为空")
        return v

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="name", value=v, error_msg="参数名称不能为空")
        Size.require_size(
            field_name="name", value=v, max_length=100, error_msg="参数名称长度不能超过100个字符"
        )
        return v

    @field_validator("key", mode="before")
    @classmethod
    def _validate_key(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="key", value=v, error_msg="参数键名不能为空")
        Size.require_size(
            field_name="key", value=v, max_length=100, error_msg="参数键名长度不能超过100个字符"
        )
        return v

    @field_validator("value", mode="before")
    @classmethod
    def _validate_value(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="value", value=v, error_msg="参数键值不能为空")
        Size.require_size(
            field_name="value", value=v, max_length=500, error_msg="参数键值长度不能超过500个字符"
        )
        return v
