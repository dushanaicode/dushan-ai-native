from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
)
from framework.common.schemas.base_request_vo import BaseRequestVO


class CodegenCreateListReqVO(BaseRequestVO):
    """管理后台 - 代码生成批量导入请求 VO"""

    data_source_config_id: Annotated[SnowflakeIdInput, Field(..., description="数据源配置编号")]
    table_names: Annotated[list[str], Field(..., description="导入的表名称列表")]
    model_config = {
        "json_schema_extra": {
            "examples": [{"dataSourceConfigId": 0, "tableNames": ["system_user", "system_role"]}]
        }
    }
