from pydantic import Field

from framework.common.schemas.base_request_vo import BaseRequestVO


class ExportFieldsReqVO(BaseRequestVO):
    fields: list[str] | None = Field(None, description="导出的字段列表")
