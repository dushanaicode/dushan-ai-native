import sys

from server.config.server.server_settings import ServerSettings
from server.config.uvicorn.uvicorn_settings import UvicornSettings
from server.launcher.worker_count_guard import resolve_effective_worker_count


def build_uvicorn_cmd(server: ServerSettings, engine: UvicornSettings) -> list[str]:
    """生成 Uvicorn 启动命令，要求启动步骤完成后再处理请求。"""
    command = [
        sys.executable,
        "-B",
        "-m",
        "uvicorn",
        "server.starter_server:app",
        "--host",
        server.host,
        "--port",
        str(server.port),
        "--workers",
        str(resolve_effective_worker_count(engine.workers, server.reload)),
        "--log-level",
        engine.log_level,
        "--lifespan",
        "on",
        "--no-proxy-headers",
        "--no-access-log",
    ]
    if server.reload:
        command += [
            "--reload",
            "--reload-exclude",
            "Temp/*",
            "--reload-exclude",
            ".venv/*",
        ]
    return command
