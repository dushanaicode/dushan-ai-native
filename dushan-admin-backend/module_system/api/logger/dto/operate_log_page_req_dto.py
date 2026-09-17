from __future__ import annotations

from pydantic import Field

from framework.common.schemas.base_dto import BaseDTO


class OperateLogPageReqDTO(BaseDTO):
    page: int = Field(default=1, ge=1)
    page_size: int | None = Field(default=None, ge=1)
    type: str | None = None
    biz_id: int | None = None
    user_id: int | None = None
