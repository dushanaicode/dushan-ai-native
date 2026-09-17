from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdInput,
    SnowflakeReferenceInput,
)
from framework.common.schemas.base_request_vo import BaseRequestVO


class CodegenTableUpdateReqVO(BaseRequestVO):
    """管理后台 - 代码生成表响应 VO"""

    id: Annotated[SnowflakeIdInput, Field(..., description="编号")]
    data_source_config_id: Annotated[SnowflakeIdInput, Field(..., description="数据源配置编号")]
    table_name: Annotated[str, Field(..., description="表名称")]
    table_comment: Annotated[str, Field(default="", description="表描述")]
    class_name: Annotated[str, Field(..., description="实体类名称")]
    author: Annotated[str | None, Field(None, description="作者")]
    remark: Annotated[str | None, Field(None, description="备注")]
    template_type: Annotated[int, Field(default=1, description="模板类型")]
    front_type: Annotated[int, Field(default=0, description="前端类型")]
    scene: Annotated[int, Field(default=1, description="场景")]
    parent_menu_id: Annotated[SnowflakeReferenceInput | None, Field(None, description="父菜单编号")]
    module_name: Annotated[str, Field(default="", description="模块名")]
    business_name: Annotated[str, Field(default="", description="业务名")]
    class_comment: Annotated[str, Field(default="", description="类描述")]
    enable_export: Annotated[bool, Field(default=False, description="是否启用导出")]
    tree_parent_column_id: Annotated[
        SnowflakeIdInput | None, Field(None, description="树表-父字段编号")
    ]
    tree_name_column_id: Annotated[
        SnowflakeIdInput | None, Field(None, description="树表-名称字段编号")
    ]
    master_table_id: Annotated[SnowflakeIdInput | None, Field(None, description="主子表-主表编号")]
    sub_join_column_id: Annotated[
        SnowflakeIdInput | None, Field(None, description="主子表-子表关联字段编号")
    ]
    sub_join_many: Annotated[bool | None, Field(None, description="主子表-关联关系")]
    create_time: Annotated[datetime | None, Field(None, description="创建时间")]
    update_time: Annotated[datetime | None, Field(None, description="更新时间")]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "dataSourceConfigId": 0,
                    "tableName": "system_user",
                    "tableComment": "用户表",
                    "className": "User",
                    "author": "admin",
                    "remark": "",
                    "templateType": 1,
                    "frontType": 0,
                    "scene": 1,
                    "parentMenuId": 1024,
                    "moduleName": "system",
                    "businessName": "user",
                    "classComment": "用户",
                    "treeParentColumnId": None,
                    "treeNameColumnId": None,
                    "masterTableId": None,
                    "subJoinColumnId": None,
                    "subJoinMany": None,
                    "createTime": "2020-05-20T05:20:00Z",
                    "updateTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }
