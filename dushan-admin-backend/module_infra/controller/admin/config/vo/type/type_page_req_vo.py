from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.page import PageQuery
from framework.common.validator import Size
from module_infra.definitions.enums.config.config_module_enum import ConfigModuleEnum


class ConfigTypePageReqVO(PageQuery):
    """管理后台 - 配置类型分页列表 Request VO"""

    module: Annotated[ConfigModuleEnum | None, Field(None, description="所属模块标识过滤")]
    name: Annotated[str | None, Field(None, description="配置类型名称，模糊匹配")]
    code: Annotated[str | None, Field(None, description="配置类型编码，模糊匹配")]
    status: Annotated[int | None, Field(None, description="展示状态，参见 StatusEnum 枚举类")]
    create_time: Annotated[
        list[datetime] | None, Field(None, exclude=True, description="创建时间范围")
    ]
    fields: Annotated[list[str] | None, Field(None, description="导出的字段列表")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "系统配置",
                    "code": "system_config",
                    "status": 1,
                    "createTime": ["2023-05-02 05:20:00", "2023-05-02 13:14:00"],
                    "fields": ["name", "code", "status", "createTime"],
                }
            ]
        }
    }

    @field_validator("code", mode="before")
    @classmethod
    def _validate_code(cls, v: Any) -> Any:
        if v is not None:
            Size.require_size(
                field_name="code",
                value=v,
                min_length=0,
                max_length=100,
                error_msg="配置类型编码长度不能超过100个字符",
            )
        return v
