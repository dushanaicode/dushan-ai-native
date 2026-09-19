from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseVO


class DataSourceConfigTestRespVO(BaseVO):
    """管理后台 - 数据源配置连接测试 Response VO"""

    success: Annotated[bool, Field(description="是否成功")]
    message: Annotated[str, Field(description="错误提示")]
    model_config = {
        "json_schema_extra": {"examples": [{"success": True, "message": "数据源连接测试成功"}]}
    }
