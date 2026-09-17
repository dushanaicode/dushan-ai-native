from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_request_vo import BaseRequestVO


class CommandStat(BaseRequestVO):
    """管理后台 - Redis 命令统计 VO"""

    command: Annotated[str, Field(description="Redis 命令")]
    calls: Annotated[int, Field(description="调用次数")]
    usec: Annotated[int, Field(description="消耗 CPU 秒数")]
