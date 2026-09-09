"""单个应用的启动状态。"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import FastAPI

from server.config.server.server_settings import ServerSettings


@dataclass(slots=True)
class AppBootstrapContext:
    """应用、配置与日志都由当前实例持有。"""

    app: FastAPI
    base_dir: Path
    settings: ServerSettings
    ready: bool = False
    logger: logging.Logger = field(default_factory=lambda: logging.Logger("dushan.server"))
