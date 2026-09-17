from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.enums.status_enum import StatusEnum
from framework.common.schemas.base_vo import BaseVO
from framework.starter_excel.converter.enum_converter import EnumConverter
from framework.starter_excel.model.excel_column import ExcelColumn


class ConfigTypeRespVO(BaseVO):
    """管理后台 - 配置类型信息 Response VO"""

    id: Annotated[
        SnowflakeIdStr | None,
        Field(None, description="配置类型编号"),
        ExcelColumn(title="配置类型主键"),
    ]
    module: Annotated[str, Field(..., description="所属模块标识")]
    name: Annotated[str, Field(..., description="配置类型名称"), ExcelColumn(title="配置类型名称")]
    code: Annotated[str, Field(..., description="配置类型编码"), ExcelColumn(title="配置类型编码")]
    status: Annotated[
        int,
        Field(..., description="状态，参见 StatusEnum 枚举类"),
        ExcelColumn(title="状态", converter=EnumConverter(StatusEnum)),
    ]
    remark: Annotated[str | None, Field(None, description="备注")]
    create_time: Annotated[datetime, Field(..., description="创建时间")]
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
                    "createTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }
