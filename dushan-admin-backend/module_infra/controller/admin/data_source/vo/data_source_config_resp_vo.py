from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdStr,
)
from framework.common.enums import StatusEnum
from framework.common.schemas import BaseVO
from framework.starter_excel.public import (
    EnumConverter,
    ExcelColumn,
)
from module_infra.definitions.enums.data_source.data_source_type_enum import DataSourceTypeEnum


class DataSourceConfigRespVO(BaseVO):
    """管理后台 - 数据源配置信息 Response VO"""

    id: Annotated[
        SnowflakeIdStr | None,
        Field(None, description="数据源配置编号"),
        ExcelColumn(title="数据源编号"),
    ]
    name: Annotated[str, Field(..., description="数据源名称"), ExcelColumn(title="数据源名称")]
    url: Annotated[str, Field(..., exclude=True)]
    status: Annotated[
        int,
        Field(..., description="状态，参见 StatusEnum 枚举类"),
        ExcelColumn(title="状态", converter=EnumConverter(StatusEnum)),
    ]
    db_type: Annotated[str, Field(..., description="数据库类型"), ExcelColumn(title="数据库类型")]
    source_type: Annotated[
        int,
        Field(..., description="数据源类型，参见 DataSourceTypeEnum 枚举类"),
        ExcelColumn(title="数据源类型", converter=EnumConverter(DataSourceTypeEnum)),
    ]
    is_default: Annotated[bool, Field(..., description="是否默认数据源")]
    pool_size: Annotated[int, Field(..., description="连接池大小")]
    max_overflow: Annotated[int, Field(..., description="最大溢出连接数")]
    pool_recycle: Annotated[int, Field(..., description="连接最大复用时间（秒）")]
    pool_timeout: Annotated[int, Field(..., description="获取连接最大等待时间（秒）")]
    echo: Annotated[bool, Field(..., description="是否开启SQL日志")]
    remark: Annotated[str | None, Field(None, description="备注")]
    create_time: Annotated[
        datetime, Field(..., description="创建时间"), ExcelColumn(title="创建时间")
    ]
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
                    "createTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }
