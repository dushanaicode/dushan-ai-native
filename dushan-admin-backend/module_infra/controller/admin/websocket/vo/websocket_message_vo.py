from pydantic import Field, JsonValue

from framework.common.schemas import BaseRequestVO


class WebsocketMessageVO(BaseRequestVO):
    type: str = Field(min_length=1, max_length=128)
    payload: JsonValue = None
    request_id: str | None = None
