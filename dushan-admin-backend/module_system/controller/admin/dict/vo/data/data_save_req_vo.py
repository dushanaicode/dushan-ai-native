from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.enums.status_enum import StatusEnum
from framework.common.schemas.base_request_vo import BaseRequestVO
from framework.common.validator.in_enum import InEnum
from framework.common.validator.not_empty import NotEmpty
from framework.common.validator.not_null import NotNull
from framework.common.validator.size import Size


class DictDataSaveReqVO(BaseRequestVO):
    """管理后台 - 字典数据创建/修改 Request VO"""

    id: Annotated[SnowflakeIdInput | None, Field(None, description="字典数据编号")]
    sort: Annotated[int, Field(..., description="显示顺序")]
    label: Annotated[str, Field(..., description="字典标签")]
    value: Annotated[str, Field(..., description="字典值")]
    dict_type: Annotated[str, Field(..., description="字典类型")]
    status: Annotated[int, Field(..., description="状态,见 StatusEnum 枚举")]
    color_type: Annotated[
        str | None,
        Field(None, description="颜色类型,default、primary、success、info、warning、danger"),
    ]
    tag_style: Annotated[dict[str, Any] | None, Field(None, description="按钮样式")]
    permission: Annotated[
        str | None, Field(None, description="权限标识（该选项所需的权限码，空表示无需权限）")
    ]
    remark: Annotated[str | None, Field(None, description="备注")]
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
                    "tagStyle": {"color": "primary", "backgroundColor": "blue"},
                    "remark": "我是一个角色",
                }
            ]
        }
    }

    @field_validator("sort", mode="before")
    @classmethod
    def _validate_sort(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="sort", value=v, error_msg="显示顺序不能为空")
        return v

    @field_validator("label", mode="before")
    @classmethod
    def _validate_label(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="label", value=v, error_msg="字典标签不能为空")
        Size.require_size(
            field_name="label",
            value=v,
            min_length=0,
            max_length=100,
            error_msg="字典标签长度不能超过100个字符",
        )
        return v

    @field_validator("value", mode="before")
    @classmethod
    def _validate_value(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="value", value=v, error_msg="字典键值不能为空")
        Size.require_size(
            field_name="value",
            value=v,
            min_length=0,
            max_length=100,
            error_msg="字典键值长度不能超过100个字符",
        )
        return v

    @field_validator("dict_type", mode="before")
    @classmethod
    def _validate_dict_type(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="dict_type", value=v, error_msg="字典类型不能为空")
        Size.require_size(
            field_name="dict_type",
            value=v,
            min_length=0,
            max_length=100,
            error_msg="字典类型长度不能超过100个字符",
        )
        return v

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="status", value=v, error_msg="状态不能为空")
        InEnum.require_in_enum(
            field_name="status", value=v, enum_class=StatusEnum, error_msg="修改状态必须是 {values}"
        )
        return v
