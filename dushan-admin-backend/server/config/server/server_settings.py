from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from framework.common.enums.application_environment_enum import ApplicationEnvironmentEnum
from server.enums.server_engine_enum import ServerEngineEnum


class ServerSettings(BaseModel):
    """HTTP 服务的配置，包括端口、运行环境和接口文档开关。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    version: str
    env: ApplicationEnvironmentEnum
    engine: ServerEngineEnum
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    debug: bool
    reload: bool
    docs_enabled: bool
    docs_url: str = Field(pattern="^/([^/?#][^?#]*)?$")
    redoc_url: str = Field(pattern="^/([^/?#][^?#]*)?$")
    openapi_url: str = Field(pattern="^/([^/?#][^?#]*)?$")
    root_path: str = Field(pattern="^(/([^/?#][^?#]*)?)?$")

    @field_validator("port", mode="before")
    @classmethod
    def reject_boolean_port(cls, value):
        """端口不接受布尔值，环境变量数字字符串交给模型解析。"""
        if isinstance(value, bool):
            raise ValueError("端口不能是布尔值")
        return value

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
