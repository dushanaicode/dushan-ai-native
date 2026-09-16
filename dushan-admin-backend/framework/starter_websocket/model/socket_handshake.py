from dataclasses import dataclass

from framework.starter_security.model.login_session import LoginSession


@dataclass(frozen=True, slots=True, repr=False)
class SocketHandshake:
    session: LoginSession
    audience: str
    allowed_events: frozenset[str]
    validated_at: float
    client_ip: str | None
    language: str | None
    subprotocol: str | None
