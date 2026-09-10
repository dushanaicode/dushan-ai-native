from pydantic import BaseModel, ConfigDict, Field, model_validator

from framework.common.enums.application_environment_enum import ApplicationEnvironmentEnum


class ServerSettings(BaseModel):
    """HTTP 服务的配置，包括端口、运行环境和接口文档开关。"""

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

    @model_validator(mode="after")
    def validate_runtime_boundaries(self):
        """检查生产环境的开关和接口文档路径。

        生产环境必须关闭调试、热重载和接口文档；开启文档时，
        各个文档路径不能重复，也不能占用 /health。
        """
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
