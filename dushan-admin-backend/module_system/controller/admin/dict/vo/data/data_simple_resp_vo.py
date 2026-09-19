from typing import Annotated, Any

from pydantic import Field

from framework.common.schemas import BaseVO


class DictDataSimpleRespVO(BaseVO):
    """管理后台 - 字典数据精简信息 Response VO"""

    dict_type: Annotated[str, Field(..., description="字典类型")]
    value: Annotated[str, Field(..., description="字典键值")]
    label: Annotated[str, Field(..., description="字典标签")]
    color_type: Annotated[
        str | None,
        Field(None, description="颜色类型，default、primary、success、info、warning、danger"),
    ]
    tag_style: Annotated[dict[str, Any] | None, Field(None, description="标签样式")]
    permission: Annotated[
        str | None, Field(None, description="权限标识（该选项所需的权限码，None表示无需权限）")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "dictType": "gender",
                    "value": "1",
                    "label": "男",
                    "colorType": "default",
                    "tagStyle": {"color": "primary", "backgroundColor": "blue"},
                }
            ]
        }
    }
