"""手动运行的短样本测量；输出目录必须显式位于当前 cwd/Temp 内。"""

import argparse
import asyncio
import base64
import ctypes
import json
import platform
import statistics
import sys
import threading
import time
from pathlib import Path

import yaml


class ProcessMemory(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def memory():
    counters = ProcessMemory()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ProcessMemory),
        ctypes.c_ulong,
    ]
    if not psapi.GetProcessMemoryInfo(
        kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return counters.WorkingSetSize


async def main(output, samples):
    from framework.starter_captcha.core.captcha_service import CaptchaService
    from framework.starter_di.context.get_bean import get_bean
    from server.starter_server import create_app

    scenarios = []
    for provider in ("block_puzzle", "click_word"):
        for concurrency in (1, 4):
            values = yaml.safe_load(
                Path("dushan-admin-backend/application.yaml").read_text(encoding="utf-8")
            )
            values["log"]["enable_file_overall"] = False
            values["banner"]["enabled"] = False
            values["config"]["models"]["cache"].update(
                enabled=True,
                host="127.0.0.1",
                port=27379,
                password=None,
                clients=[{"name": "default", "db": 0}],
            )
            values["config"]["models"]["captcha"].update(
                enabled=True, provider=provider, generation_limit=10000
            )
            config = output / f"{provider}-{concurrency}"
            config.mkdir(exist_ok=True)
            (config / "application.yaml").write_text(
                yaml.safe_dump(values, allow_unicode=True), encoding="utf-8"
            )
            app = create_app(base_dir=config, environ={})
            async with app.router.lifespan_context(app):
                with app.state.application_context.execution():
                    service = get_bean(CaptchaService)
                    gate = asyncio.Semaphore(concurrency)
                    measurements = []
                    rss_start, rss_peak = memory(), memory()
                    threads_peak = threading.active_count()

                    async def sample(index):
                        nonlocal rss_peak, threads_peak
                        async with gate:
                            start = time.perf_counter()
                            challenge = await service.create("login")
                            generated = time.perf_counter()
                            store = service.store
                            key = store.cache.build_full_key(
                                store.key, store.identifier("login", "challenge", challenge.token)
                            )
                            record = json.loads(
                                await store.cache.get_client(store.key).hget(key, "payload")
                            )
                            check_start = time.perf_counter()
                            proof = await service.check(
                                challenge.token, "login", {"points": record["points"]}
                            )
                            checked = time.perf_counter()
                            await service.consume(proof.verification, "login")
                            consumed = time.perf_counter()
                            measurements.append(
                                [
                                    (generated - start) * 1000,
                                    (checked - check_start) * 1000,
                                    (consumed - checked) * 1000,
                                    len(challenge.model_dump_json().encode()),
                                ]
                            )
                            rss_peak = max(rss_peak, memory())
                            threads_peak = max(threads_peak, threading.active_count())
                            if index == 0:
                                (config / "example.png").write_bytes(
                                    base64.b64decode(challenge.data["image"])
                                )
                                if "piece" in challenge.data:
                                    (config / "piece.png").write_bytes(
                                        base64.b64decode(challenge.data["piece"])
                                    )

                    # 预热独立测量，不计入 80 个统计样本。
                    for index in range(5):
                        await sample(index + 1)
                    measurements.clear()
                    cpu, started = time.process_time(), time.perf_counter()
                    await asyncio.gather(*(sample(index) for index in range(samples)))
                    elapsed, cpu = time.perf_counter() - started, time.process_time() - cpu
                    stats = {}
                    for column, name in enumerate(
                        ("generate_ms", "check_ms", "consume_ms", "response_bytes")
                    ):
                        data = sorted(row[column] for row in measurements)
                        stats[name] = {
                            "median": round(statistics.median(data), 3),
                            "p95": round(data[int(0.95 * (len(data) - 1))], 3),
                            "max": round(max(data), 3),
                        }
                    scenarios.append(
                        {
                            "provider": provider,
                            "concurrency": concurrency,
                            "samples": samples,
                            "elapsed_s": round(elapsed, 3),
                            "flows_per_second": round(samples / elapsed, 2),
                            "cpu_seconds": round(cpu, 3),
                            "rss_start_bytes": rss_start,
                            "rss_peak_sampled_bytes": rss_peak,
                            "threads_peak": threads_peak,
                            **stats,
                        }
                    )
            assert service._pool is None and not service._jobs
    result = {
        "python": sys.version,
        "platform": platform.platform(),
        "cpu": platform.processor(),
        "scope": "单机 Windows / WSL Redis 7.0.15；4 场景，每场景 5 次预热 + 80 次本地正确校验；吞吐包含测试读取答案的额外 Redis 往返；不外推生产容量或抗自动化能力。",
        "scenarios": scenarios,
        "threads_after_close": threading.active_count(),
    }
    (output / "performance.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--samples", type=int, default=80)
    args = parser.parse_args()
    output = args.output.resolve()
    if (
        not output.is_relative_to((Path.cwd() / "Temp").resolve())
        or output == (Path.cwd() / "Temp").resolve()
    ):
        raise ValueError("输出必须为当前 cwd/Temp 下的具体子目录")
    output.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(Path("dushan-admin-backend").resolve()))
    asyncio.run(main(output, args.samples))
