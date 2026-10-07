import asyncio
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from module_infra.service.server import server_service_impl as server_module
from module_infra.service.server.server_service_impl import ServerServiceImpl

pytestmark = pytest.mark.unit


@pytest.fixture
def server_probes(monkeypatch):
    """提供确定的系统探测结果，不访问外部资源。"""
    monkeypatch.setattr(
        server_module.psutil,
        "cpu_times_percent",
        Mock(return_value=SimpleNamespace(user=25, system=5, idle=70)),
    )
    monkeypatch.setattr(server_module.psutil, "cpu_count", Mock(return_value=8))
    monkeypatch.setattr(
        server_module.psutil,
        "virtual_memory",
        Mock(
            return_value=SimpleNamespace(
                total=8192, used=2048, free=4096, available=4096, percent=25
            )
        ),
    )
    monkeypatch.setattr(server_module.socket, "gethostname", Mock(return_value="test-host"))
    monkeypatch.setattr(server_module.socket, "gethostbyname", Mock(return_value="127.0.0.1"))
    monkeypatch.setattr(server_module.platform, "node", Mock(return_value="test-host"))
    monkeypatch.setattr(server_module.platform, "machine", Mock(return_value="x86_64"))
    monkeypatch.setattr(server_module.platform, "platform", Mock(return_value="test-os"))
    monkeypatch.setattr(server_module.platform, "python_version", Mock(return_value="3.12.0"))
    process = SimpleNamespace(
        memory_info=Mock(return_value=SimpleNamespace(rss=1024)),
        create_time=Mock(return_value=0),
        name=Mock(return_value="python"),
        exe=Mock(return_value="python.exe"),
    )
    monkeypatch.setattr(server_module.psutil, "Process", Mock(return_value=process))
    monkeypatch.setattr(server_module.time, "time", Mock(return_value=90060))
    monkeypatch.setattr(server_module.time, "strftime", Mock(return_value="2026-10-06 00:00:00"))
    monkeypatch.setattr(server_module.psutil, "disk_partitions", Mock(return_value=[]))
    return ServerServiceImpl()


async def test_monitor_preserves_response_and_skips_unavailable_disks(server_probes, monkeypatch):
    """系统详情保留 JSON 字段、展示值和不可访问磁盘的跳过语义。"""
    partitions = [
        SimpleNamespace(device=device, mountpoint=device, fstype="ntfs")
        for device in ("blocked", "missing", "invalid", "C:\\")
    ]
    monkeypatch.setattr(server_module.psutil, "disk_partitions", Mock(return_value=partitions))
    disk_usage = Mock(
        side_effect=[
            PermissionError(),
            FileNotFoundError(),
            SystemError(),
            SimpleNamespace(total=8192, used=2048, free=6144, percent=25),
        ]
    )
    monkeypatch.setattr(server_module.psutil, "disk_usage", disk_usage)

    result = await server_probes.get_server_list()

    assert result.model_dump(mode="json", by_alias=True) == {
        "cpu": {"cpuNum": 8, "used": 25.0, "sys": 5.0, "free": 70.0},
        "mem": {"total": "8.0KB", "used": "2.0KB", "free": "4.0KB", "usage": 25.0},
        "sys": {
            "computerIp": "127.0.0.1",
            "computerName": "test-host",
            "osArch": "x86_64",
            "osName": "test-os",
            "userDir": server_module.os.path.abspath(server_module.os.getcwd()),
        },
        "py": {
            "total": "4.0KB",
            "used": "1.0KB",
            "free": "3.0KB",
            "usage": 25.0,
            "name": "python",
            "version": "3.12.0",
            "startTime": "2026-10-06 00:00:00",
            "runTime": "1天1小时1分钟",
            "home": "python.exe",
        },
        "sysFiles": [
            {
                "dirName": "C:\\",
                "sysTypeName": "ntfs",
                "typeName": "本地固定磁盘（C:）",
                "total": "8.0KB",
                "used": "2.0KB",
                "free": "6.0KB",
                "usage": "25%",
            }
        ],
    }
    assert disk_usage.call_count == 4


async def test_blocking_probe_leaves_event_loop_responsive(server_probes, monkeypatch):
    """DNS 采集等待期间，事件循环仍可运行其他回调。"""
    loop = asyncio.get_running_loop()
    loop_thread = threading.get_ident()
    probe_started = asyncio.Event()
    release_probe = threading.Event()

    def resolve_host(hostname):
        """等待事件循环放行，以检测同步探测是否阻塞了请求线程。"""
        assert hostname == "test-host"
        assert threading.get_ident() != loop_thread
        loop.call_soon_threadsafe(probe_started.set)
        assert release_probe.wait(timeout=2)
        return "127.0.0.1"

    monkeypatch.setattr(server_module.socket, "gethostbyname", resolve_host)
    collection = asyncio.create_task(server_probes.get_server_list())
    try:
        await asyncio.wait_for(probe_started.wait(), timeout=2)
        assert not collection.done()
        loop.call_soon(release_probe.set)
        result = await asyncio.wait_for(collection, timeout=2)
        assert result.sys.computer_ip == "127.0.0.1"
    finally:
        release_probe.set()
        await asyncio.gather(collection, return_exceptions=True)


async def test_usage_and_monitor_share_cpu_sampling_thread(server_probes, monkeypatch):
    """轻量用量和完整监控连续采样使用同一线程的 CPU 基线。"""
    samples = {}
    loop_thread = threading.get_ident()

    def sample_cpu():
        """模拟 psutil 按线程保存的 CPU 增量采样。"""
        thread = threading.get_ident()
        previous = samples.get(thread, 0)
        samples[thread] = previous + 1
        return SimpleNamespace(user=previous * 10, system=5, idle=95 - previous * 10)

    monkeypatch.setattr(server_module.psutil, "cpu_times_percent", sample_cpu)

    first = await server_probes.get_server_usage()
    monitor = await server_probes.get_server_list()
    last = await server_probes.get_server_usage()

    assert [first.cpu.used, monitor.cpu.used, last.cpu.used] == [0, 10, 20]
    assert [first.cpu.cpu_num, monitor.cpu.cpu_num, last.cpu.cpu_num] == [None, 8, None]
    assert samples == {loop_thread: 3}
