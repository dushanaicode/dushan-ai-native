from typing import Annotated

from pydantic import Field

from module_infra.controller.admin.server.vo.memory_info_vo import MemoryInfoVO


class PyInfoVO(MemoryInfoVO):
    """管理后台 - Python 进程信息 VO"""

    name: Annotated[str | None, Field(description="Python名称")] = None
    version: Annotated[str | None, Field(description="Python版本")] = None
    start_time: Annotated[str | None, Field(description="启动时间")] = None
    run_time: Annotated[str | None, Field(description="运行时长")] = None
    home: Annotated[str | None, Field(description="安装路径")] = None
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "total": "16GB",
                    "used": "8GB",
                    "free": "8GB",
                    "usage": 50.0,
                    "name": "CPython",
                    "version": "3.10.0",
                    "startTime": "2023-01-01 00:00:00",
                    "runTime": "10天12小时30分钟",
                    "home": "/usr/local/bin/python",
                }
            ]
        }
    }
