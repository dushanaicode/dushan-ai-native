from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RemoteErrorDetail:
    """保存上游调用详情，交给 RemoteServiceException 的 detail 参数用于内部排错。

    例如 RemoteErrorDetail(service="支付服务", http_status=503)。
    url 和 raw 可能包含凭据或内部响应，不能直接放入对外响应。
    """

    service: str | None = None
    url: str | None = None
    http_status: int | None = None
    internal_code: int | None = None
    raw: Any = None
