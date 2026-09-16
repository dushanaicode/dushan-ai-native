import asyncio
import json
import os
import statistics
import time
from contextlib import AsyncExitStack
from pathlib import Path

import pytest
from websockets.asyncio.client import connect

from starter_websocket.conftest import ORIGIN


@pytest.mark.parametrize("ws_engine", ["uvicorn", "granian"], indirect=True)
async def test_representative_connections_and_resource_terminal(socket_case, ws_engine, tmp_path):
    case = socket_case
    samples = []
    body = "x" * 1024
    async with AsyncExitStack() as stack:
        clients = []
        for _ in range(4):
            websocket = await stack.enter_async_context(
                connect(case.url(await case.ticket()), origin=ORIGIN, proxy=None)
            )
            await websocket.recv()
            clients.append(websocket)

        async def roundtrips(websocket, client_index):
            for index in range(20):
                request = f"c{client_index}-{index}"
                message = json.dumps(
                    {"type": "echo", "payload": {"text": body}, "requestId": request}
                )
                begin = time.perf_counter()
                await websocket.send(message)
                result = json.loads(await websocket.recv())
                samples.append(time.perf_counter() - begin)
                assert result["requestId"] == request and result["payload"]["text"] == body

        started = time.perf_counter()
        await asyncio.gather(*(roundtrips(client, index) for index, client in enumerate(clients)))
        elapsed = time.perf_counter() - started
    state = await case.wait_state(lambda value: value["runtime"]["connections"] == 0)
    assert (
        state["active_contexts"]
        == state["runtime"]["active_handlers"]
        == state["runtime"]["outbound"]
        == 0
    )
    assert state["runtime"]["peak_inbound"] <= 16 and state["runtime"]["peak_outbound"] <= 64
    assert state["runtime"]["error_types"] == []
    report = {
        "engine": ws_engine,
        "connections": 4,
        "messages": 80,
        "text_bytes": 1024,
        "handler_concurrency_per_connection": 1,
        "elapsed_seconds": elapsed,
        "roundtrips_per_second": 80 / elapsed,
        "p50_ms": statistics.median(samples) * 1000,
        "p95_ms": sorted(samples)[75] * 1000,
        "resource_terminal": state["runtime"],
        "scope": "本机真实进程与 WebSocket；包含实时 Security/Redis 身份验证，不外推生产容量",
    }
    output = Path(os.environ.get("DUSHAN_DP_REPORT_DIR", str(tmp_path)))
    output.mkdir(parents=True, exist_ok=True)
    (output / f"websocket-{ws_engine}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
