from __future__ import annotations

import os
import platform
import socket
import time
from typing import override

import psutil

from framework.starter_di.decorators.components import service
from module_infra.controller.admin.server.vo.cpu_info_vo import CpuInfoVO
from module_infra.controller.admin.server.vo.memory_info_vo import MemoryInfoVO
from module_infra.controller.admin.server.vo.py_info_vo import PyInfoVO
from module_infra.controller.admin.server.vo.server_resp_vo import ServerMonitorRespVO
from module_infra.controller.admin.server.vo.server_usage_resp_vo import ServerUsageRespVO
from module_infra.controller.admin.server.vo.sys_files_vo import SysFilesVO
from module_infra.controller.admin.server.vo.sys_info_vo import SysInfoVO
from module_infra.service.server.server_service import ServerService


@service(interface=ServerService)
class ServerServiceImpl(ServerService):
    @override
    async def get_server_usage(self) -> ServerUsageRespVO:
        return ServerUsageRespVO(cpu=self._get_cpu_info(), mem=self._get_mem_info())

    @override
    async def get_server_list(self) -> ServerMonitorRespVO:
        cpu = self._get_cpu_info(include_num=True)
        mem = self._get_mem_info()
        hostname = socket.gethostname()
        sys = SysInfoVO(
            computerIp=socket.gethostbyname(hostname),
            computerName=platform.node(),
            osArch=platform.machine(),
            osName=platform.platform(),
            userDir=os.path.abspath(os.getcwd()),
        )
        process = psutil.Process(os.getpid())
        memory_info = psutil.virtual_memory()
        process_mem = process.memory_info()
        run_seconds = time.time() - process.create_time()
        days = int(run_seconds // 86400)
        hours = int(run_seconds % 86400 // 3600)
        minutes = int(run_seconds % 3600 // 60)
        py = PyInfoVO(
            name=process.name(),
            version=platform.python_version(),
            startTime=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(process.create_time())),
            runTime=f"{days}天{hours}小时{minutes}分钟",
            home=process.exe(),
            total=self._bytes2human(memory_info.available),
            used=self._bytes2human(process_mem.rss),
            free=self._bytes2human(memory_info.available - process_mem.rss),
            usage=round(process_mem.rss / memory_info.available * 100, 2),
        )
        sys_files = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.device)
                sys_files.append(
                    SysFilesVO(
                        dirName=partition.device,
                        sysTypeName=partition.fstype,
                        typeName="本地固定磁盘（" + partition.mountpoint.replace("\\", "") + "）",
                        total=self._bytes2human(usage.total),
                        used=self._bytes2human(usage.used),
                        free=self._bytes2human(usage.free),
                        usage=f"{usage.percent}%",
                    )
                )
            except (PermissionError, FileNotFoundError, SystemError):
                continue
        return ServerMonitorRespVO(cpu=cpu, mem=mem, sys=sys, py=py, sysFiles=sys_files)

    def _get_cpu_info(self, include_num: bool = False) -> CpuInfoVO:
        cpu_times = psutil.cpu_times_percent()
        kwargs = dict(used=cpu_times.user, sys=cpu_times.system, free=cpu_times.idle)
        if include_num:
            kwargs["cpuNum"] = psutil.cpu_count(logical=True)
        return CpuInfoVO(**kwargs)

    def _get_mem_info(self) -> MemoryInfoVO:
        mem = psutil.virtual_memory()
        return MemoryInfoVO(
            total=self._bytes2human(mem.total),
            used=self._bytes2human(mem.used),
            free=self._bytes2human(mem.free),
            usage=mem.percent,
        )

    @staticmethod
    def _bytes2human(n: int) -> str:
        """将字节数转换为人类可读格式"""
        symbols = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        prefix = {}
        for i, s in enumerate(symbols[1:]):
            prefix[s] = 1 << (i + 1) * 10
        for symbol in reversed(symbols[1:]):
            if n >= prefix[symbol]:
                value = float(n) / prefix[symbol]
                return f"{value:.1f}{symbol}"
        return f"{n:.1f}{symbols[0]}"
