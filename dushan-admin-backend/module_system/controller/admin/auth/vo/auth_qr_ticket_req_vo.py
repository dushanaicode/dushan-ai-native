from pydantic import Field

from framework.common.schemas import BaseVO


class AuthQrTicketReqVO(BaseVO):
    ticket: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
