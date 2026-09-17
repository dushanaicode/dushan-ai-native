from typing import Annotated

from pydantic import Field

from framework.common.page.schemas.page_query import PageQuery


class MailAccountPageReqVO(PageQuery):
    """管理后台 - 邮箱账号分页列表 Request VO"""

    mail: Annotated[str | None, Field(default=None, description="邮箱账号，用于查询过滤")]
    username: Annotated[str | None, Field(default=None, description="用户名称，用于查询过滤")]
    model_config = {
        "json_schema_extra": {"examples": [{"mail": "729227973@qq.com", "username": "dushan"}]}
    }
