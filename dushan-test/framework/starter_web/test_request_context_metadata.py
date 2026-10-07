import pytest
from starlette.requests import HTTPConnection

from framework.starter_ip.core.client_ip_resolver import ClientIpResolver
from framework.starter_web.public import RequestContext

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("accept_language", [None, "", "en-US,en;q=0.9,zh-CN;q=0.8"])
def test_accept_language_preserves_negotiation_input(accept_language):
    """上下文仅提供原始语言偏好，由翻译器统一协商。"""
    headers = [] if accept_language is None else [(b"accept-language", accept_language.encode())]
    connection = HTTPConnection({"type": "http", "headers": headers})
    with RequestContext.bind(connection, "request-1", None) as context:
        assert context.accept_language == accept_language


@pytest.mark.parametrize("user_agent", [None, "", "Mozilla/5.0", "A" * 700])
def test_user_agent_preserves_header_without_applying_log_limits(user_agent):
    """请求上下文保留完整头值，缺失头仍有明确的空串表示。"""
    headers = [] if user_agent is None else [(b"user-agent", user_agent.encode())]
    connection = HTTPConnection({"type": "http", "headers": headers})
    with RequestContext.bind(connection, "request-1", "192.0.2.1") as context:
        assert RequestContext.current() is context
        assert context.user_agent == ("" if user_agent is None else user_agent)


@pytest.mark.parametrize("client_ip", ["192.0.2.1", "2001:db8::1"])
def test_ip_accessors_preserve_resolved_client_address(client_ip):
    """地址访问器只消费已解析的可信地址，不从请求头重新猜测。"""
    connection = HTTPConnection(
        {"type": "http", "headers": [(b"x-forwarded-for", b"203.0.113.99")]}
    )
    with RequestContext.bind(connection, "request-1", client_ip) as context:
        assert context.client_ip_text == client_ip
        assert context.require_client_ip() == client_ip


def test_missing_client_can_be_displayed_but_cannot_be_used_for_required_audit():
    """没有 socket 地址时不信任转发头，展示与必填审计使用不同合同。"""
    connection = HTTPConnection(
        {"type": "http", "headers": [(b"x-forwarded-for", b"203.0.113.99")]}
    )
    client_ip = ClientIpResolver.resolve_client_ip(connection.headers, None, ())
    with RequestContext.bind(connection, "request-1", client_ip) as context:
        assert context.client_ip is None
        assert context.client_ip_text == ""
        with pytest.raises(RuntimeError, match="缺少客户端 IP"):
            context.require_client_ip()
