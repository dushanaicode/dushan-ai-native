from typing import Annotated

from pydantic import Field

from framework.common.page import PageQuery


class CodegenTablePageReqVO(PageQuery):
    """管理后台 - 代码生成表分页查询 Request VO"""

    table_name: Annotated[str | None, Field(None, description="表名称")]
    table_comment: Annotated[str | None, Field(None, description="表描述")]
    create_time: Annotated[list[str] | None, Field(None, description="创建时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tableName": "system_user",
                    "tableComment": "用户",
                    "createTime": ["2020-05-20T05:20:00Z", "2026-07-01T23:59:59Z"],
                    "pageNo": 1,
                    "pageSize": 10,
                }
            ]
        }
    }
