from ipaddress import IPv4Network, IPv6Network
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator

from framework.starter_config.config.config_model import ConfigModel
from framework.starter_config.decorator.config_decorator import config_model
from framework.starter_config.enums.config_source_enum import ConfigSourceEnum


@config_model("ip", env_prefix="IP_", sources=(ConfigSourceEnum.ENVIRONMENT, ConfigSourceEnum.YAML))
class IpSettings(ConfigModel):
    """IP 资源和 Provider 的启动快照；部署默认值仅来自公共 YAML。"""

    enabled: bool
    area_csv_path: str | None
    local_enabled: bool
    local_families: tuple[Literal["ipv4", "ipv6"], ...] = Field(min_length=1)
    local_data_dir: str | None
    online_enabled: bool
    online_providers: tuple[str, ...]
    online_timeout_seconds: float = Field(gt=0, allow_inf_nan=False)
    query_budget_seconds: float = Field(gt=0, allow_inf_nan=False)
    online_failure_policy: Literal["raise", "continue"]
    online_max_connections: int = Field(gt=0)
    online_max_response_bytes: int = Field(gt=0)
    pconline_api_url: str
    vore_api_url: str
    trusted_proxy_cidrs: tuple[IPv4Network | IPv6Network, ...]
    cache_max_size: int = Field(ge=0)
    cache_ttl_seconds: float = Field(gt=0, allow_inf_nan=False)
    unknown_cache_ttl_seconds: float = Field(ge=0, allow_inf_nan=False)

    @field_validator(
        "online_timeout_seconds",
        "query_budget_seconds",
        "online_max_connections",
        "online_max_response_bytes",
        "cache_max_size",
        "cache_ttl_seconds",
        "unknown_cache_ttl_seconds",
        mode="before",
    )
    @classmethod
    def reject_boolean_numbers(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("IP 数值配置不能是布尔值")
        return value

    @field_validator("area_csv_path", "local_data_dir")
    @classmethod
    def validate_path(cls, value: str | None) -> str | None:
        if value is not None and not Path(value).is_absolute():
            raise ValueError("资源覆盖路径必须为绝对路径，null 使用打包资源")
        return value

    @field_validator("local_families")
    @classmethod
    def validate_families(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(values) != len(set(values)):
            raise ValueError("本地 IP 地址族不能重复")
        return values

    @field_validator("trusted_proxy_cidrs", mode="before")
    @classmethod
    def validate_proxy_inputs(cls, values: object) -> object:
        if not isinstance(values, (list, tuple)) or any(
            not isinstance(value, (str, IPv4Network, IPv6Network)) for value in values
        ):
            raise ValueError("可信代理必须是 CIDR 字符串或已解析网络对象的列表")
        return values

    @field_validator("pconline_api_url", "vore_api_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.fragment
        ):
            raise ValueError("在线 IP Provider 必须使用无凭据的 HTTPS URL")
        return value

    @model_validator(mode="after")
    def validate_providers(self) -> "IpSettings":
        if len(set(self.online_providers)) != len(self.online_providers) or any(
            not name for name in self.online_providers
        ):
            raise ValueError("在线 Provider 名称不能为空或重复")
        if self.online_enabled and not self.online_providers:
            raise ValueError("启用在线查询必须指定 Provider")
        return self
