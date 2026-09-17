from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.page.schemas.page_query import PageQuery
from module_infra.definitions.enums.config.config_module_enum import ConfigModuleEnum


class ConfigDataPageReqVO(PageQuery):
    """管理后台 - 配置数据分页列表 Request VO"""

    module: Annotated[ConfigModuleEnum | None, Field(None, description="所属模块标识过滤")]
    name: Annotated[str | None, Field(None, description="数据源名称，模糊匹配")]
    type_id: Annotated[SnowflakeIdInput | None, Field(None, description="配置类型ID")]
    create_time: Annotated[
        list[datetime] | None, Field(None, exclude=True, description="创建时间范围")
    ]
    fields: Annotated[list[str] | None, Field(None, description="导出的字段列表")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "名称",
                    "typeId": 1,
                    "createTime": ["2020-05-20 05:20:00", "2020-05-20 13:14:00"],
                    "fields": ["name", "key", "typeId", "createTime"],
                }
            ]
        }
    }
