from typing import Annotated, Literal

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeCursorStr,
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO


class AuthMenuRespVO(BaseVO):
    """管理后台 - 登录用户的菜单信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="菜单ID")]
    parent_id: Annotated[SnowflakeCursorStr, Field(..., description="父菜单ID")]
    name: Annotated[str, Field(..., description="菜单名称")]
    path: Annotated[
        str | None, Field(None, description="路由地址,仅菜单类型为菜单或者目录时，才需要传")
    ]
    component: Annotated[
        str | None, Field(None, description="组件路径,仅菜单类型为菜单时，才需要传")
    ]
    component_name: Annotated[str | None, Field(None, description="组件名")]
    icon: Annotated[
        str | None, Field(None, description="菜单图标,仅菜单类型为菜单或者目录时，才需要传")
    ]
    visible: Annotated[bool, Field(..., description="是否可见")]
    keep_alive: Annotated[bool, Field(..., description="是否缓存")]
    always_show: Annotated[bool | None, Field(None, description="是否总是显示")]
    children: Annotated[list["AuthMenuRespVO"] | None, Field(None, description="子路由")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "parentId": 1024,
                    "name": "渡山",
                    "path": "post",
                    "component": "system/post/index",
                    "componentName": "SystemUser",
                    "icon": "/menu/list",
                    "visible": False,
                    "keepAlive": False,
                    "alwaysShow": False,
                    "children": [
                        {
                            "id": 2,
                            "parentId": 1,
                            "name": "子菜单",
                            "path": "child",
                            "component": "system/post/child",
                            "componentName": "SystemChild",
                            "icon": "/menu/child",
                            "visible": True,
                            "keepAlive": True,
                            "alwaysShow": True,
                            "children": [],
                        }
                    ],
                }
            ]
        }
    }
    kind: Literal["group", "page", "action", "link", "iframe"]
    url: str | None = None
    data_permission: bool = False
