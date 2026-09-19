from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.schemas import BaseRequestVO
from framework.common.validator import NotEmpty, NotNull, Size
from module_infra.definitions.enums.config.config_module_enum import ConfigModuleEnum


class ConfigTypeSaveReqVO(BaseRequestVO):
    """管理后台 - 配置类型创建/修改 Request VO"""

    id: Annotated[SnowflakeIdInput | None, Field(None, description="配置类型编号")]
    module: Annotated[ConfigModuleEnum, Field(ConfigModuleEnum.SYSTEM, description="所属模块标识")]
    name: Annotated[str, Field(..., description="配置类型名称")]
    code: Annotated[str, Field(..., description="配置类型编码")]
    status: Annotated[int, Field(..., description="状态，参见 StatusEnum 枚举类")]
    remark: Annotated[str | None, Field(None, description="备注")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "module": "system",
                    "name": "系统配置",
                    "code": "system_config",
                    "status": 1,
                    "remark": "系统相关配置",
                }
            ]
        }
    }

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="name", value=v, error_msg="配置类型名称不能为空")
        Size.require_size(
            field_name="name",
            value=v,
            min_length=0,
            max_length=100,
            error_msg="配置类型名称长度不能超过100个字符",
        )
        return v

    @field_validator("code", mode="before")
    @classmethod
    def _validate_code(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="code", value=v, error_msg="配置类型编码不能为空")
        Size.require_size(
            field_name="code",
            value=v,
            min_length=0,
            max_length=100,
            error_msg="配置类型编码长度不能超过 100 个字符",
        )
        return v

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="status", value=v, error_msg="状态不能为空")
        return v
