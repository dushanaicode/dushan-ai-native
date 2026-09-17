from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_request_vo import BaseRequestVO


class DeptListReqVO(BaseRequestVO):
    """管理后台 - 部门列表 Request VO"""

    name: Annotated[str | None, Field(None, description="部门名称，模糊匹配")]
    status: Annotated[int | None, Field(None, description="展示状态，参见 StatusEnum 枚举类")]
    model_config = {"json_schema_extra": {"examples": [{"name": "", "status": 1}]}}
