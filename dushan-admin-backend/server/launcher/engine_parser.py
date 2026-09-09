"""命令行启动选项。"""

import argparse
from collections.abc import Sequence
from pathlib import Path


def parse_server_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """选择服务器、运行环境与配置目录。"""
    parser = argparse.ArgumentParser(description="启动渡山后端服务")
    parser.add_argument(
        "--server",
        choices=["granian", "uvicorn"],
        default="granian",
        help="服务器引擎，默认 granian",
    )
    parser.add_argument(
        "--env", choices=["dev", "test", "staging", "prod"], help="显式指定运行环境"
    )
    parser.add_argument("--config-dir", type=Path, help="配置文件目录，默认使用后端目录")
    return parser.parse_args(argv)
