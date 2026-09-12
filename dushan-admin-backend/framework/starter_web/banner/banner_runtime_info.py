from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BannerRuntimeInfo:
    """提供经过配置解析的公开启动信息，不包含完整配置或运行服务对象。"""

    app_name: str
    version: str
    environment: str
    engine: str
    host: str
    port: int
    root_path: str
    docs_url: str | None
    redoc_url: str | None
    openapi_url: str | None
    enabled_modules: tuple[str, ...]
    disabled_modules: tuple[str, ...]
