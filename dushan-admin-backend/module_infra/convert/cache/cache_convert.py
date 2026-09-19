from typing import Any

from framework.starter_di.public import (
    util,
)
from module_infra.controller.admin.cache.vo.monitor.command_stat import CommandStat
from module_infra.controller.admin.cache.vo.monitor.monitor_resp_vo import MonitorRespVO


@util()
class CacheConvert:
    @staticmethod
    def build_monitor_info(
        info: dict[str, Any], db_size: int, command_stats_parsed: dict[str, dict[str, Any]]
    ) -> MonitorRespVO:
        """使用解析后的数据构建 MonitorRespVO 对象"""
        command_stats_list = [
            CommandStat(
                command=command.replace("cmdstat_", ""),
                calls=int(stats_data.get("calls", 0)),
                usec=int(stats_data.get("usec", 0)),
            )
            for command, stats_data in command_stats_parsed.items()
        ]
        return MonitorRespVO(info=info, db_size=db_size, command_stats=command_stats_list)
