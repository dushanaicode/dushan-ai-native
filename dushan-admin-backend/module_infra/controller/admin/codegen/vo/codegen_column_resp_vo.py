from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdStr,
)
from framework.common.schemas import BaseVO


class CodegenColumnRespVO(BaseVO):
    """管理后台 - 代码生成列响应 VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="编号")]
    table_id: Annotated[SnowflakeIdStr, Field(..., description="表编号")]
    column_name: Annotated[str, Field(..., description="字段列名")]
    column_comment: Annotated[str, Field(default="", description="字段描述")]
    data_type: Annotated[str, Field(..., description="字段物理类型")]
    field_type: Annotated[str, Field(default="str", description="Python字段类型")]
    field_name: Annotated[str, Field(default="", description="Python属性名")]
    create_operation: Annotated[bool, Field(default=True, description="是否参与新增操作")]
    update_operation: Annotated[bool, Field(default=True, description="是否参与编辑操作")]
    list_operation: Annotated[bool, Field(default=False, description="是否作为查询条件")]
    list_operation_result: Annotated[bool, Field(default=True, description="是否在列表中展示")]
    list_operation_condition: Annotated[str, Field(default="=", description="查询方式")]
    nullable: Annotated[bool, Field(default=True, description="是否允许为空")]
    html_type: Annotated[str, Field(default="input", description="显示类型")]
    dict_type: Annotated[str | None, Field(None, description="关联字典类型")]
    example: Annotated[str | None, Field(None, description="示例值")]
    order_no: Annotated[int, Field(default=0, description="排序")]
    primary_key: Annotated[bool, Field(default=False, description="是否主键")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "tableId": 1,
                    "columnName": "id",
                    "columnComment": "编号",
                    "dataType": "bigint",
                    "fieldType": "int",
                    "fieldName": "id",
                    "createOperation": False,
                    "updateOperation": False,
                    "listOperation": False,
                    "listOperationResult": True,
                    "listOperationCondition": "=",
                    "nullable": False,
                    "htmlType": "input",
                    "dictType": None,
                    "example": "1024",
                    "orderNo": 0,
                    "primaryKey": True,
                }
            ]
        }
    }
