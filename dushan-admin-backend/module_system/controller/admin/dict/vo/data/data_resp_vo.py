from datetime import datetime
from typing import Annotated, Any

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.enums.status_enum import StatusEnum
from framework.common.schemas.base_vo import BaseVO
from framework.starter_excel.converter.enum_converter import EnumConverter
from framework.starter_excel.model.excel_column import ExcelColumn


class DictDataRespVO(BaseVO):
    """管理后台 - 字典数据信息 Response VO"""

    id: Annotated[
        SnowflakeIdStr | None,
        Field(None, description="字典数据编号"),
        ExcelColumn(title="字典编码"),
    ]
    sort: Annotated[int, Field(..., description="显示顺序"), ExcelColumn(title="字典排序")]
    label: Annotated[str, Field(..., description="字典标签"), ExcelColumn(title="字典标签")]
    value: Annotated[str, Field(..., description="字典值"), ExcelColumn(title="字典键值")]
    dict_type: Annotated[str, Field(..., description="字典类型"), ExcelColumn(title="字典类型")]
    status: Annotated[
        int,
        Field(..., description="状态,见 StatusEnum 枚举"),
        ExcelColumn(title="状态", converter=EnumConverter(StatusEnum)),
    ]
    color_type: Annotated[
        str | None,
        Field(None, description="颜色类型,default、primary、success、info、warning、danger"),
    ]
    tag_style: Annotated[dict[str, Any] | None, Field(None, description="标签样式")]
    permission: Annotated[str | None, Field(None, description="权限标识")]
    remark: Annotated[str | None, Field(None, description="备注")]
    create_time: Annotated[
        datetime, Field(..., description="创建时间"), ExcelColumn(title="创建时间")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "sort": 1024,
                    "label": "渡山",
                    "value": "dushan",
                    "dictType": "sys_common_sex",
                    "status": 1,
                    "colorType": "default",
                    "tagStyle": {"color": "#cf1322", "variant": "solid", "textColor": ""},
                    "remark": "备注",
                    "createTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }
