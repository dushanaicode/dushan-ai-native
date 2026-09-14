import asyncio
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from statistics import median, quantiles
from time import perf_counter

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.skipif("DUSHAN_SECURITY_MYSQL" not in os.environ, reason="需要本轮独立 MySQL 和 Redis")
@pytest.mark.parametrize("cached", [False, True])
async def test_two_workers_cold_key_and_warm_mysql_authentication(
    security_factory, tmp_path, cached
):
    target = json.loads(os.environ["DUSHAN_SECURITY_MYSQL"])
    processes, files, clients = [], [], []
    async with security_factory(
        cache=cached, database_url=target["url"], provider_timeout_seconds=4
    ) as case:
        token, session = await case.issue(granted=("read", *(f"resource:{n}" for n in range(63))))
        env = dict(
            os.environ,
            DUSHAN_CONFIG_DIR=str(case.app.state.bootstrap.base_dir),
            DUSHAN_SECURITY_PERMISSION_DELAY="0.8",
            PYTHONDONTWRITEBYTECODE="1",
            PYTHONUTF8="1",
        )
        env["PYTHONPATH"] = os.pathsep.join(
            map(
                str,
                [
                    ROOT / "dushan-admin-backend",
                    ROOT / "dushan-test",
                    ROOT / "dushan-test/framework",
                    tmp_path,
                ],
            )
        )
        try:
            for index in range(2):
                folder = tmp_path / f"worker-{index}"
                folder.mkdir()
                with socket.socket() as reservation:
                    reservation.bind(("127.0.0.1", 0))
                    port = reservation.getsockname()[1]
                process_env = dict(env, **{name: str(folder) for name in ("TEMP", "TMP", "TMPDIR")})
                output = (folder / "server.log").open("w", encoding="utf-8")
                files.append(output)
                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-B",
                        "-m",
                        "starter_security.http_host",
                        "--engine",
                        "uvicorn",
                        "--port",
                        str(port),
                        "--evidence",
                        str(folder),
                    ],
                    cwd=ROOT,
                    env=process_env,
                    stdin=subprocess.DEVNULL,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                processes.append(process)
                client = httpx.AsyncClient(
                    base_url=f"http://127.0.0.1:{port}", timeout=8, trust_env=False
                )
                clients.append(client)
                deadline = perf_counter() + 30
                while True:
                    assert process.poll() is None, (folder / "server.log").read_text(
                        encoding="utf-8"
                    )
                    try:
                        if (await client.get("/health")).json()["data"]["status"] == "ready":
                            break
                    except (httpx.NetworkError, httpx.TimeoutException):
                        pass
                    assert perf_counter() < deadline
                    await asyncio.sleep(0.05)
            headers = {"Authorization": "Bearer " + token}
            cold_started = perf_counter()
            cold = await asyncio.gather(
                *(client.get("/__security_test/protected", headers=headers) for client in clients)
            )
            cold_ms = (perf_counter() - cold_started) * 1000
            assert all(response.json() == {"account": session.account_id} for response in cold)
            cold_stats = [(await client.get("/__security_test/stats")).json() for client in clients]
            assert len({row["pid"] for row in cold_stats}) == 2
            assert sum(row["permission_reads"] for row in cold_stats) == (1 if cached else 2)
            limiter = asyncio.Semaphore(16)

            async def request(index):
                async with limiter:
                    started = perf_counter()
                    response = await clients[index % 2].get(
                        "/__security_test/protected", headers=headers
                    )
                    assert response.json() == {"account": session.account_id}
                    return (perf_counter() - started) * 1000

            started = perf_counter()
            latencies = await asyncio.gather(*(request(index) for index in range(80)))
            elapsed = perf_counter() - started
            stats = [(await client.get("/__security_test/stats")).json() for client in clients]
            result = {
                "cache": cached,
                "database": "MySQL 8.4.9",
                "workers": 2,
                "concurrency": 16,
                "requests": 80,
                "injected_permission_latency_seconds": 0.8,
                "cold_ms": cold_ms,
                "median_ms": median(latencies),
                "p95_ms": quantiles(latencies, n=20)[18],
                "rps": 80 / elapsed,
                "permission_reads": sum(row["permission_reads"] for row in stats),
                "token_reads": sum(row["token_reads"] for row in stats),
                "errors": 0,
            }
            (tmp_path / "measurement.json").write_text(
                json.dumps(result, indent=2), encoding="utf-8"
            )
            assert result["token_reads"] == 82 and result["permission_reads"] == (
                1 if cached else 82
            )
        finally:
            for client in clients:
                try:
                    await client.post("/__security_test/stop")
                except httpx.HTTPError:
                    pass
                await client.aclose()
            for process in processes:
                try:
                    await asyncio.to_thread(process.wait, 15)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    await asyncio.to_thread(process.wait, 10)
                assert process.returncode == 0
            for output in files:
                output.close()
            for index in range(len(processes)):
                closed = json.loads(
                    (tmp_path / f"worker-{index}/closed.json").read_text(encoding="utf-8")
                )
                assert (
                    not closed["ready"]
                    and closed["security_released"]
                    and closed["database_released"]
                    and closed["di_released"]
                )
