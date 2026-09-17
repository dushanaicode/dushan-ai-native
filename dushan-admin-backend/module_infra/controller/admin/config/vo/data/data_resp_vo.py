from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO
from framework.starter_excel.model.excel_column import ExcelColumn
from module_infra.framework.excel.boolean_converter import BooleanConverter


class ConfigDataRespVO(BaseVO):
    """管理后台 - 配置数据信息 Response VO"""

    id: Annotated[
        SnowflakeIdStr, Field(..., description="参数配置序号"), ExcelColumn(title="参数配置序号")
    ]
    type_id: Annotated[SnowflakeIdStr, Field(..., description="配置类型ID")]
    type_name: Annotated[
        str | None, Field(None, description="配置类型名称"), ExcelColumn(title="配置类型")
    ]
    name: Annotated[str, Field(..., description="参数名称"), ExcelColumn(title="参数名称")]
    key: Annotated[
        str,
        Field(..., description="参数键名", validation_alias="config_key"),
        ExcelColumn(title="参数键名"),
    ]
    value: Annotated[str, Field(..., description="参数键值"), ExcelColumn(title="参数键值")]
    description: Annotated[str | None, Field(None, description="配置描述")]
    input_type: Annotated[str | None, Field(None, description="UI控件类型")]
    input_props: Annotated[str | None, Field(None, description="UI控件属性JSON")]
    sort: Annotated[int, Field(0, description="显示顺序")]
    visible: Annotated[
        bool,
        Field(..., description="是否可见"),
        ExcelColumn(title="是否可见", converter=BooleanConverter()),
    ]
    remark: Annotated[str | None, Field(None, description="备注"), ExcelColumn(title="备注")]
    create_time: Annotated[
        datetime, Field(..., description="创建时间"), ExcelColumn(title="创建时间")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "typeId": 1,
                    "typeName": "系统配置",
                    "name": "数据库名",
                    "key": "dushan.db.username",
                    "value": "1024",
                    "visible": True,
                    "remark": "备注",
                    "createTime": "2020-05-20 05:20:00",
                }
            ]
        }
    }
