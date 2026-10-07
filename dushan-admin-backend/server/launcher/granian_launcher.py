import sys

from server.config.granian.granian_settings import GranianSettings
from server.config.server.server_settings import ServerSettings
from server.launcher.worker_count_guard import WorkerCountGuard


class GranianLauncher:
    @staticmethod
    def build_command(server: ServerSettings, engine: GranianSettings) -> list[str]:
        """根据服务配置生成 Granian 启动命令。"""
        command = [
            sys.executable,
            "-B",
            "-m",
            "granian",
            "--interface",
            "asgi",
            "--no-access-log",
            "server.asgi:app",
            "--host",
            server.host,
            "--port",
            str(server.port),
            "--workers",
            str(WorkerCountGuard.resolve(engine.workers, server.reload)),
        ]
        if server.reload:
            command += [
                "--reload",
                "--reload-ignore-dirs",
                "Temp",
                "--reload-ignore-dirs",
                ".venv",
            ]
        else:
            command += ["--runtime-threads", str(engine.threads)]
        return command
