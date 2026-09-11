from typing import Literal

from pydantic import Field

from framework.common.schemas.base_request_vo import BaseRequestVO


class SortField(BaseRequestVO):
    """描述客户端排序意图，字段必须再经过调用方提供的白名单映射。"""

    field: str = Field(
        pattern=r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$", max_length=128
    )
    order: Literal["asc", "desc"] = "asc"
