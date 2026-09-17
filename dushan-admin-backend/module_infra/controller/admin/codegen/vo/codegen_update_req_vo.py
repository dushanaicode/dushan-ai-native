from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_request_vo import BaseRequestVO
from module_infra.controller.admin.codegen.vo.codegen_column_update_req_vo import (
    CodegenColumnUpdateReqVO,
)
from module_infra.controller.admin.codegen.vo.codegen_table_update_req_vo import (
    CodegenTableUpdateReqVO,
)


class CodegenUpdateReqVO(BaseRequestVO):
    """管理后台 - 代码生成更新请求 VO"""

    table: Annotated[CodegenTableUpdateReqVO, Field(..., description="表信息")]
    columns: Annotated[
        list[CodegenColumnUpdateReqVO], Field(default_factory=list, description="列信息")
    ]
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
