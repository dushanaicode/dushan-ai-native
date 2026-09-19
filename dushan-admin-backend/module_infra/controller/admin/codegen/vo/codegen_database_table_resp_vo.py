from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseVO


class DatabaseTableRespVO(BaseVO):
    """管理后台 - 数据库表信息响应 VO（用于导入表时展示）"""

    name: Annotated[str, Field(..., description="表名称")]
    comment: Annotated[str | None, Field(None, description="表描述")]
    model_config = {
        "json_schema_extra": {"examples": [{"name": "system_user", "comment": "用户表"}]}
    }
