from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, field_validator

from framework.common.contracts import (
    SnowflakeCursorStr,
    SnowflakeIdStr,
)
from framework.common.schemas import BaseVO
from framework.common.validator import NotEmpty, NotNull, Size


class MenuRespVO(BaseVO):
    """管理后台 - 菜单信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="菜单编号")]
    name: Annotated[str, Field(..., description="菜单名称")]
    permission: Annotated[
        str | None, Field(None, description="权限标识,仅菜单类型为按钮时，才需要传递")
    ]
    kind: Literal["group", "page", "action", "link", "iframe"]
    sort: Annotated[int, Field(..., description="显示顺序")]
    parent_id: Annotated[SnowflakeCursorStr, Field(..., description="父菜单 ID")]
    path: Annotated[
        str | None, Field(None, description="路由地址,仅菜单类型为菜单或者目录时，才需要传")
    ]
    icon: Annotated[
        str | None, Field(None, description="菜单图标,仅菜单类型为菜单或者目录时，才需要传")
    ]
    component: Annotated[
        str | None, Field(None, description="组件路径,仅菜单类型为菜单时，才需要传")
    ]
    component_name: Annotated[str | None, Field(None, description="组件名")]
    status: Annotated[int, Field(..., description="状态,见 StatusEnum 枚举")]
    visible: Annotated[bool | None, Field(None, description="是否可见")]
    keep_alive: Annotated[bool | None, Field(None, description="是否缓存")]
    create_time: Annotated[datetime, Field(..., description="创建时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "name": "渡山",
                    "permission": "sys:menu:add",
                    "type": 1,
                    "sort": 1024,
                    "parentId": 1024,
                    "path": "post",
                    "icon": "/menu/list",
                    "component": "system/post/index",
                    "componentName": "SystemUser",
                    "status": 1,
                    "visible": False,
                    "keepAlive": False,
                    "createTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        NotEmpty.require_not_empty(field_name="name", value=v, error_msg="菜单名称不能为空")
        Size.require_size(
            field_name="name",
            value=v,
            min_length=0,
            max_length=50,
            error_msg="菜单名称长度不能超过50个字符",
        )
        return v

    @field_validator("permission", mode="before")
    @classmethod
    def _validate_permission(cls, v: str | None) -> str | None:
        if v:
            Size.require_size(
                field_name="permission",
                value=v,
                min_length=0,
                max_length=100,
                error_msg="权限标识长度不能超过100个字符",
            )
        return v

    @field_validator("kind", mode="before")
    @classmethod
    def _validate_kind(cls, v: int) -> int:
        NotNull.require_not_null(field_name="kind", value=v, error_msg="菜单类型不能为空")
        return v

    @field_validator("sort", mode="before")
    @classmethod
    def _validate_sort(cls, v: int) -> int:
        NotNull.require_not_null(field_name="sort", value=v, error_msg="显示顺序不能为空")
        return v

    @field_validator("parent_id", mode="before")
    @classmethod
    def _validate_parent_id(cls, v: int) -> int:
        NotNull.require_not_null(field_name="parent_id", value=v, error_msg="父菜单 ID 不能为空")
        return v

    @field_validator("path", mode="before")
    @classmethod
    def _validate_path(cls, v: str | None) -> str | None:
        if v:
            Size.require_size(
                field_name="path",
                value=v,
                min_length=0,
                max_length=200,
                error_msg="路由地址不能超过200个字符",
            )
        return v

    @field_validator("component", mode="before")
    @classmethod
    def _validate_component(cls, v: str | None) -> str | None:
        if v:
            Size.require_size(
                field_name="component",
                value=v,
                min_length=0,
                max_length=200,
                error_msg="组件路径不能超过200个字符",
            )
        return v

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: int) -> int:
        NotNull.require_not_null(field_name="status", value=v, error_msg="状态不能为空")
        return v

    url: str | None = None
    data_permission: bool = False
