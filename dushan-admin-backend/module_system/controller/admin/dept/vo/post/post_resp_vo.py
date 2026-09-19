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


class PostRespVO(BaseVO):
    """管理后台 - 岗位信息 Response VO"""

    id: Annotated[
        SnowflakeIdStr | None, Field(..., description="岗位序号"), ExcelColumn(title="岗位序号")
    ]
    name: Annotated[str, Field(..., description="岗位名称"), ExcelColumn(title="岗位名称")]
    code: Annotated[str, Field(..., description="岗位编码"), ExcelColumn(title="岗位编码")]
    sort: Annotated[int, Field(..., description="显示顺序"), ExcelColumn(title="岗位排序")]
    status: Annotated[
        int,
        Field(..., description="状态"),
        ExcelColumn(title="状态", converter=EnumConverter(StatusEnum)),
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
                    "name": "渡山",
                    "code": "dushan",
                    "sort": 1024,
                    "status": 1,
                    "remark": "快乐的备注",
                    "createTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }
