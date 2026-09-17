from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_vo import BaseVO
from module_infra.controller.admin.codegen.vo.codegen_column_resp_vo import CodegenColumnRespVO
from module_infra.controller.admin.codegen.vo.codegen_table_resp_vo import CodegenTableRespVO


class CodegenDetailRespVO(BaseVO):
    """管理后台 - 代码生成详情响应 VO（表 + 列）"""

    table: Annotated[CodegenTableRespVO, Field(..., description="表信息")]
    columns: Annotated[list[CodegenColumnRespVO], Field(default_factory=list, description="列信息")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "table": {"id": 1, "tableName": "system_user", "className": "User"},
                    "columns": [{"id": 1, "tableId": 1, "columnName": "id", "dataType": "bigint"}],
                }
            ]
        }
    }
