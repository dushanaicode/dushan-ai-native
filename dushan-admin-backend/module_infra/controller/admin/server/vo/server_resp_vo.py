from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_vo import BaseVO
from module_infra.controller.admin.server.vo.cpu_info_vo import CpuInfoVO
from module_infra.controller.admin.server.vo.memory_info_vo import MemoryInfoVO
from module_infra.controller.admin.server.vo.py_info_vo import PyInfoVO
from module_infra.controller.admin.server.vo.sys_files_vo import SysFilesVO
from module_infra.controller.admin.server.vo.sys_info_vo import SysInfoVO


class ServerMonitorRespVO(BaseVO):
    """管理后台 - 服务监控信息 Response VO"""

    cpu: Annotated[CpuInfoVO, Field(description="CPU相关信息")]
    py: Annotated[PyInfoVO, Field(description="Python相关信息")]
    mem: Annotated[MemoryInfoVO, Field(description="內存相关信息")]
    sys: Annotated[SysInfoVO, Field(description="服务器相关信息")]
    sys_files: Annotated[list[SysFilesVO], Field(description="磁盘相关信息")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "cpu": {"cpuNum": 8, "used": 30.5, "sys": 10.2, "free": 59.3},
                    "py": {
                        "total": "16GB",
                        "used": "8GB",
                        "free": "8GB",
                        "usage": 50.0,
                        "name": "CPython",
                        "version": "3.10.0",
                        "startTime": "2023-01-01 00:00:00",
                        "runTime": "10天12小时30分钟",
                        "home": "/usr/local/bin/python",
                    },
                    "mem": {"total": "16GB", "used": "8GB", "free": "8GB", "usage": 50.0},
                    "sys": {
                        "computerIp": "192.168.1.100",
                        "computerName": "server-01",
                        "osArch": "x86_64",
                        "osName": "Linux",
                        "userDir": "/home/app/server",
                    },
                    "sysFiles": [
                        {
                            "dirName": "/",
                            "sysTypeName": "ext4",
                            "typeName": "本地磁盘",
                            "total": "500GB",
                            "used": "200GB",
                            "free": "300GB",
                            "usage": "40%",
                        }
                    ],
                }
            ]
        }
    }
