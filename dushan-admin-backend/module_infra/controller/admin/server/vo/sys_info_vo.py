from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseVO


class SysInfoVO(BaseVO):
    """管理后台 - 系统信息 VO"""

    computer_ip: Annotated[str | None, Field(description="服务器IP")] = None
    computer_name: Annotated[str | None, Field(description="服务器名称")] = None
    os_arch: Annotated[str | None, Field(description="系统架构")] = None
    os_name: Annotated[str | None, Field(description="操作系统")] = None
    user_dir: Annotated[str | None, Field(description="项目路径")] = None
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "computerIp": "192.168.1.100",
                    "computerName": "server-01",
                    "osArch": "x86_64",
                    "osName": "Linux",
                    "userDir": "/home/app/server",
                }
            ]
        }
    }
