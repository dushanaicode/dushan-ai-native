import math
from collections.abc import Mapping

from framework.common.security.sanitizer import Sanitizer
from framework.starter_monitor.config.monitor_settings import MonitorSettings


class MonitorAttributePolicy:
    """采集只接受白名单标量，拒绝任意对象、原始异常文本及原始SQL。"""

    KEYS = frozenset(
        {
            "code.function.name",
            "http.request.method",
            "http.response.status_code",
            "http.route",
            "db.operation.name",
            "db.namespace",
            "db.query.summary",
            "db.query.fingerprint",
            "db.duration_ms",
            "db.success",
            "exception.type",
            "exception.escaped",
            "error.code",
            "operation.cancelled",
            "biz.id",
            "biz.type",
            "biz.generated_ids",
            "performance.duration_ms",
            "performance.level",
            "captcha.provider",
        }
    )

    def __init__(self, settings: MonitorSettings) -> None:
        self.settings = settings
        self.keys = self.KEYS | frozenset(settings.attribute_keys)

    def text(self, value: str) -> str:
        return (
            Sanitizer.sanitize_text(value)
            .encode("utf-8")[: self.settings.max_attribute_length]
            .decode("utf-8", "ignore")
        )

    def attributes(self, values: Mapping[str, object] | None) -> dict:
        result = {}
        if values is None:
            return result
        for key, value in values.items():
            if len(result) >= self.settings.max_attributes:
                break
            if key not in self.keys:
                continue
            if key.startswith("biz.") and not self.settings.capture_business_ids:
                if key != "biz.generated_ids":
                    continue
            if key == "biz.generated_ids":
                if self.settings.capture_generated_ids and type(value) in (tuple, list):
                    result[key] = tuple(
                        str(item)
                        for item in value[: self.settings.max_generated_ids]
                        if type(item) is int and item.bit_length() <= 63
                    )
                continue
            if type(value) is str:
                result[key] = self.text(value)
            elif type(value) is bool or type(value) is int and value.bit_length() <= 63:
                result[key] = value
            elif type(value) is float and math.isfinite(value):
                result[key] = value
        return result
