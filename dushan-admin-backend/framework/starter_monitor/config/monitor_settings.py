import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator

from framework.common.security.sanitizer import Sanitizer
from framework.starter_config.config.config_model import ConfigModel
from framework.starter_config.decorator.config_decorator import config_model
from framework.starter_config.enums.config_source_enum import ConfigSourceEnum


@config_model(
    "monitor",
    env_prefix="MONITOR_",
    sources=(ConfigSourceEnum.ENVIRONMENT, ConfigSourceEnum.YAML),
    field_keys={"service_name": "server.name", "service_version": "server.version"},
)
class MonitorSettings(ConfigModel):
    """应用独立的追踪启动快照；默认值由公共 YAML 提供。"""

    enabled: bool
    service_name: str = Field(min_length=1, max_length=128)
    service_version: str = Field(min_length=1, max_length=64)
    instance_id: str | None = Field(max_length=64)
    sampler: Literal[
        "always_on",
        "always_off",
        "traceidratio",
        "parentbased_always_on",
        "parentbased_always_off",
        "parentbased_traceidratio",
    ]
    sample_ratio: float = Field(strict=True, ge=0, le=1, allow_inf_nan=False)
    exporter: Literal["otlp", "none"]
    endpoint: str
    export_headers: dict[str, SecretStr]
    export_timeout_seconds: float = Field(strict=True, ge=0.05, le=10, allow_inf_nan=False)
    flush_timeout_seconds: float = Field(strict=True, gt=0, le=30, allow_inf_nan=False)
    shutdown_timeout_seconds: float = Field(strict=True, gt=0, le=30, allow_inf_nan=False)
    max_queue_size: int = Field(strict=True, ge=1, le=4096)
    max_batch_size: int = Field(strict=True, ge=1, le=512)
    schedule_delay_millis: int = Field(strict=True, ge=1, le=60000)
    max_attributes: int = Field(strict=True, ge=1, le=64)
    max_attribute_length: int = Field(strict=True, ge=16, le=2048)
    max_events: int = Field(strict=True, ge=0, le=8)
    attribute_keys: tuple[str, ...]
    propagators: tuple[Literal["tracecontext", "baggage"], ...]
    baggage_keys: tuple[str, ...]
    max_propagation_bytes: int = Field(strict=True, ge=64, le=8192)
    http_enabled: bool
    excluded_paths: tuple[str, ...]
    response_trace_header: bool
    query_enabled: bool
    capture_business_ids: bool
    capture_generated_ids: bool
    max_generated_ids: int = Field(strict=True, ge=1, le=64)
    performance_medium_ms: float = Field(strict=True, gt=0, allow_inf_nan=False)
    performance_slow_ms: float = Field(strict=True, gt=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_contract(self) -> "MonitorSettings":
        url = urlsplit(self.endpoint)
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.port is None
            or not 1 <= url.port <= 65535
            or url.username is not None
            or url.password is not None
            or url.path not in {"", "/"}
            or url.query
            or url.fragment
        ):
            raise ValueError("OTLP gRPC 地址必须为明确的 http(s)://host:port，不含凭据或路径参数")
        if self.instance_id is not None and not self.instance_id.strip():
            raise ValueError("instance_id 只能是非空标识或 null")
        if self.max_batch_size > self.max_queue_size:
            raise ValueError("导出批次不能大于队列容量")
        if (
            min(self.flush_timeout_seconds, self.shutdown_timeout_seconds)
            < 2 * self.export_timeout_seconds
        ):
            raise ValueError("flush/关闭预算至少为单批导出超时的两倍")
        if self.performance_medium_ms > self.performance_slow_ms:
            raise ValueError("中等耗时阈值不能大于慢操作阈值")
        for values in (
            self.attribute_keys,
            self.propagators,
            self.baggage_keys,
            self.excluded_paths,
        ):
            if len(values) != len(set(values)):
                raise ValueError("追踪白名单与传播器不能重复")
        if any(not path.startswith("/") or "?" in path for path in self.excluded_paths):
            raise ValueError("排除项必须是不含查询串的绝对路径")
        if "baggage" in self.propagators and not self.baggage_keys:
            raise ValueError("启用 baggage 必须明确白名单")
        if len(self.attribute_keys) > 32 or len(self.baggage_keys) > 16:
            raise ValueError("追踪白名单超过上限")
        forbidden = {
            "exception.message",
            "exception.stacktrace",
            "db.statement",
            "http.url",
            "url.full",
        }
        for key in (*self.attribute_keys, *self.baggage_keys):
            if (
                re.fullmatch(r"[a-z][a-z0-9_.-]{0,63}", key) is None
                or key in forbidden
                or Sanitizer.sanitize_sensitive_data({key.replace(".", "_"): "probe"}).get(
                    key.replace(".", "_")
                )
                != "probe"
            ):
                raise ValueError("追踪白名单包含无效或敏感字段")
        for key, value in self.export_headers.items():
            if re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", key) is None or key.endswith("-bin"):
                raise ValueError("导出认证头必须是普通小写 gRPC metadata 名称")
            text = value.get_secret_value()
            if (
                len(text) > 4096
                or not text.isascii()
                or any(ord(c) < 32 or ord(c) == 127 for c in text)
            ):
                raise ValueError("导出认证头包含无效字符或超长值")
        return self
