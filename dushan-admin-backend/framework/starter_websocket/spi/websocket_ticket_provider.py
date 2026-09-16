from typing import Protocol

from framework.starter_security.model.login_session import LoginSession


class WebSocketTicketProvider(Protocol):
    async def consume(self, ticket: str, *, application_id: str, domain: str) -> LoginSession:
        """原子消费短期一次性票据并返回服务端会话引用。

        签发属于 System/业务；必须验证票据、期限和消费域。框架还会通过当前
        TokenProvider 重读会话，客户端传入的用户/租户字段不能构造返回值。
        """
        ...
