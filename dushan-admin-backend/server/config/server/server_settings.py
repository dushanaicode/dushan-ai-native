"""HTTP 服务启动参数。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from framework.common.enums.application_environment_enum import ApplicationEnvironmentEnum


class ServerSettings(BaseModel):
    """只保存已校验的配置，不在模型内部再次读取进程环境。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(default="渡山 AI Native", min_length=1)
    version: str = "0.0.0"
    env: ApplicationEnvironmentEnum = ApplicationEnvironmentEnum.DEVELOPMENT
    host: str = Field(default="127.0.0.1", min_length=1)
    port: int = Field(default=48080, ge=1, le=65535)
    debug: bool = False
    reload: bool = False
    docs_enabled: bool = True
    docs_url: str = Field(default="/docs", pattern=r"^/([^/?#][^?#]*)?$")
    redoc_url: str = Field(default="/redoc", pattern=r"^/([^/?#][^?#]*)?$")
    openapi_url: str = Field(default="/openapi.json", pattern=r"^/([^/?#][^?#]*)?$")
    root_path: str = Field(default="", pattern=r"^(/([^/?#][^?#]*)?)?$")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value):
        """允许环境配置使用小写日志级别。"""
        return value.upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_runtime_boundaries(self):
        """检查生产模式和内置路由，避免启动配置绕过边界。"""
        if self.env == ApplicationEnvironmentEnum.PRODUCTION:
            if self.debug or self.reload or self.docs_enabled:
                raise ValueError(
                    "生产环境必须关闭 SERVER_DEBUG、SERVER_RELOAD 和 SERVER_DOCS_ENABLED"
                )
        if self.docs_enabled:
            routes = [self.docs_url, self.redoc_url, self.openapi_url, "/health"]
            if len(set(routes)) != len(routes):
                raise ValueError("接口文档路径不能重复，也不能占用 /health")
        return self
