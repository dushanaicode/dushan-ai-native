from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class WebSettings(BaseModel):
    """HTTP 边界的启动快照，部署默认值只由公共 YAML 提供。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_body_bytes: int = Field(gt=0)
    max_multipart_bytes: int = Field(gt=0)
    cors_origins: tuple[str, ...]
    cors_credentials: bool
    cors_methods: tuple[str, ...]
    cors_headers: tuple[str, ...]
    cors_expose_headers: tuple[str, ...]
    cors_max_age: int = Field(ge=0)
    gzip_enabled: bool
    gzip_minimum_size: int = Field(ge=0)
    gzip_compresslevel: int = Field(ge=0, le=9)
    access_log_enabled: bool

    @field_validator(
        "max_body_bytes",
        "max_multipart_bytes",
        "cors_max_age",
        "gzip_minimum_size",
        "gzip_compresslevel",
        mode="before",
    )
    @classmethod
    def reject_boolean_numbers(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("Web 数值配置不能是布尔值")
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_origins(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            parsed = urlsplit(value)
            if value != "*" and (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("CORS 来源必须是无路径和凭据的 HTTP(S) origin")
        if len(values) != len(set(values)):
            raise ValueError("CORS 来源不能重复")
        return values

    @model_validator(mode="after")
    def validate_credentials(self) -> "WebSettings":
        if self.cors_credentials and any(
            "*" in values for values in (self.cors_origins, self.cors_methods, self.cors_headers)
        ):
            raise ValueError("携带凭据的 CORS 必须显式列出来源、方法与请求头")
        return self
