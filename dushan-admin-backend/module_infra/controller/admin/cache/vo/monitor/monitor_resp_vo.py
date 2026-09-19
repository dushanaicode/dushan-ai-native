from typing import Annotated, Any

from pydantic import Field

from framework.common.schemas import BaseVO
from module_infra.controller.admin.cache.vo.monitor.command_stat import CommandStat


class MonitorRespVO(BaseVO):
    """管理后台 - 缓存监控信息 Response VO"""

    info: Annotated[dict[str, Any], Field(description="Redis info 指令结果")]
    db_size: Annotated[int, Field(description="Redis key 数量")]
    command_stats: Annotated[list[CommandStat], Field(description="命令统计数组")]
