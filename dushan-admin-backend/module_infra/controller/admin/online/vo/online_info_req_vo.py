from typing import Annotated

from pydantic import Field

from framework.common.page.schemas.page_query import PageQuery


class OnlineInfoReqVO(PageQuery):
    """管理后台 - 在线用户分页列表 Request VO"""

    user_name: Annotated[str | None, Field(default=None, description="登录名称")]
    ipaddr: Annotated[str | None, Field(default=None, description="主机")]
    model_config = {
        "json_schema_extra": {"examples": [{"userName": "admin", "ipaddr": "192.168.1.1"}]}
    }
