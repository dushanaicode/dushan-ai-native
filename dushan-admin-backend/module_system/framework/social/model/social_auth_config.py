from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SocialAuthConfig(BaseModel):
    """社交客户端 auth_config 列的结构，字段与授权组件的客户端配置一一对应。

    只约束结构和类型，未填写的部分保持空值，渠道自身的要求仍由授权组件在使用时校验。
    多余字段直接拒绝：redirectUri 这类驼峰写法会被当成未知字段，在保存时就报错，
    不会存进库之后在登录阶段才暴露成缺字段。
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    redirect_uri: str | None = None
    frontend_redirect_uri: str | None = None
    scopes: tuple[str, ...] = ()
    pkce: bool = False
    options: dict[str, str] = Field(default_factory=dict)
    credentials: dict[str, str] = Field(default_factory=dict)

    @field_validator("frontend_redirect_uri")
    @classmethod
    def validate_frontend_redirect(cls, value):
        if value is None:
            return value
        url = urlsplit(value)
        local = url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"}
        if (
            (url.scheme != "https" and not local)
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError("前端回调必须是 HTTPS 或本机 HTTP 地址，不含账号、查询串或片段")
        return value
