import argparse
import asyncio
import importlib
import json
import os
import socket
import sys
import threading
from pathlib import Path


async def verify(arguments):
    # -I -S 启动后只显式加入 wheel 安装目录、宿主快照与现有运行依赖，不处理 editable .pth。
    sys.path[:0] = [str(arguments.installed), str(arguments.host), str(arguments.dependencies)]
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("普通导入不应创建连接或线程")

    originals = socket.socket.connect, socket.create_connection, threading.Thread.start
    socket.socket.connect = forbidden
    socket.create_connection = forbidden
    threading.Thread.start = forbidden
    modules = []
    framework_root = arguments.installed / "framework"
    try:
        for path in sorted(framework_root.rglob("*.py")):
            relative = path.relative_to(arguments.installed).with_suffix("")
            parts = relative.parts[:-1] if relative.name == "__init__" else relative.parts
            module = importlib.import_module(".".join(parts))
            assert Path(module.__file__).resolve().is_relative_to(framework_root.resolve())
            modules.append(module.__name__)
    finally:
        socket.socket.connect, socket.create_connection, threading.Thread.start = originals
    assert not attempts

    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    os.environ["DUSHAN_CONFIG_DIR"] = str(arguments.configuration)
    os.environ["SERVER_ENV"] = "test"
    os.environ["SERVER_ENGINE"] = "uvicorn"
    os.environ["SERVER_PORT"] = str(port)
    import httpx
    import uvicorn

    from server.starter_server import create_app

    app = create_app()
    server = uvicorn.Server(
        uvicorn.Config(
            app, host="127.0.0.1", port=port, proxy_headers=False, access_log=False, lifespan="on"
        )
    )
    task = asyncio.create_task(server.serve())
    try:
        async with asyncio.timeout(15):
            while not server.started:
                if task.done():
                    await task
                    raise AssertionError("服务未就绪即退出")
                await asyncio.sleep(0.02)
        async with httpx.AsyncClient(trust_env=False) as client:
            response = await client.get(f"http://127.0.0.1:{port}/health")
            assert response.status_code == 200 and response.json()["data"]["status"] == "ready"
            openapi = await client.get(f"http://127.0.0.1:{port}/openapi.json")
            assert "/health" in openapi.json()["paths"]
        runtime = app.state.application_context
        assert runtime.get_statistics()["executions"] == 0
    finally:
        server.should_exit = True
        await asyncio.wait_for(task, 15)
    assert app.state.application_context is None
    assert app.state.bootstrap.definitions is None
    assert not app.state.bootstrap.ready
    assert not app.state.bootstrap.logging_starter.initialized
    result = {
        "modules": len(modules),
        "module_names": modules,
        "resource_creation_attempts": len(attempts),
        "http_health": response.status_code,
        "http_openapi": openapi.status_code,
        "di_state_after_shutdown": runtime.state.value,
        "logging_closed": True,
        "framework_root": str(framework_root),
    }
    arguments.result.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "module_names"},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("installed", "host", "dependencies", "configuration", "result"):
        parser.add_argument("--" + name, type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
