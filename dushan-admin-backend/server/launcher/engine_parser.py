import argparse
from collections.abc import Sequence
from pathlib import Path

from server.enums.server_engine_enum import ServerEngineEnum


def parse_server_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """解析命令行中的服务器类型、运行环境和配置目录。"""
    parser = argparse.ArgumentParser(description="启动渡山后端服务")
    parser.add_argument(
        "--server",
        type=ServerEngineEnum,
        choices=list(ServerEngineEnum),
        help="服务器引擎；未指定时采用 server.engine 配置",
    )
    parser.add_argument(
        "--env", choices=["dev", "test", "staging", "prod"], help="显式指定运行环境"
    )
    parser.add_argument("--config-dir", type=Path, help="配置文件目录，默认使用后端目录")
    return parser.parse_args(argv)
