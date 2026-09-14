from dataclasses import dataclass, field

from fastapi import Request

from framework.common.security.sanitizer import Sanitizer
from framework.starter_web.context.request_context import RequestContext


@dataclass(frozen=True, slots=True)
class RequestAudit:
    """冻结必要的请求审计投影；URL 是路由模板，不含查询串或路径凭据。"""

    request_method: str
    request_url: str
    user_ip: str | None = field(repr=False)
    user_agent: str | None = field(repr=False)

    @classmethod
    def from_request(cls, request: Request, credential: str) -> "RequestAudit":
        method = (
            request.method
            if request.method
            in {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE"}
            else "OTHER"
        )
        path = request.scope["state"].get("web_route_template", request.scope["route"].path)
        agent = request.headers.get("user-agent")
        return cls(
            method,
            Sanitizer.sanitize_text(path)[:255],
            RequestContext.current().client_ip,
            None
            if agent is None
            else Sanitizer.sanitize_text(agent.replace(credential, "***"))[:200],
        )
