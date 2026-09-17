from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_vo import BaseVO
from module_system.controller.admin.auth.vo.menu_vo import MenuVO
from module_system.controller.admin.auth.vo.user_vo import UserVO


class AuthPermissionInfoRespVO(BaseVO):
    """管理后台 - 登录用户的权限信息 Response VO"""

    user: Annotated["UserVO", Field(..., description="用户信息")]
    roles: Annotated[list[str], Field(..., description="角色标识数组")]
    permissions: Annotated[list[str], Field(..., description="操作权限数组")]
    menus: Annotated[list["MenuVO"], Field(..., description="菜单树")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user": {
                        "id": 1024,
                        "nickname": "渡山源码",
                        "avatar": "https://www.dushan.info/xx.jpg",
                        "deptId": 2048,
                        "username": "dushan",
                        "email": "729227973@qq.com",
                    },
                    "roles": ["admin", "common"],
                    "permissions": ["system:user:list", "system:user:create", "system:user:update"],
                    "menus": [
                        {
                            "id": 1024,
                            "parentId": 0,
                            "name": "系统管理",
                            "path": "system",
                            "component": "system/index",
                            "componentName": "System",
                            "icon": "/system",
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
