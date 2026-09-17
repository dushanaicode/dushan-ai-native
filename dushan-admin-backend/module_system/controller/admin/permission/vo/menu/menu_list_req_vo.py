from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_request_vo import BaseRequestVO


class MenuListReqVO(BaseRequestVO):
    """管理后台 - 菜单列表 Request VO"""

    name: Annotated[str | None, Field(None, description="菜单名称，模糊匹配")]
    status: Annotated[int | None, Field(None, description="展示状态，参见 StatusEnum 枚举类")]
    paginate: Annotated[bool, Field(True, description="是否分页")]
    model_config = {
        "json_schema_extra": {"examples": [{"name": "渡山", "status": 1, "paginate": True}]}
    }
