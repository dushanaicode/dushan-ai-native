from typing import Annotated

from pydantic import EmailStr, Field

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.enums import StatusEnum
from framework.common.schemas import BaseRequestVO
from framework.starter_excel.public import (
    EnumConverter,
    ExcelColumn,
)
from module_system.definitions.enums.common.common_sex_enum import CommonSexEnum


class UserImportExcelVO(BaseRequestVO):
    """管理后台 - 用户 Excel 导入 VO"""

    username: Annotated[
        str | None, Field(None, description="登录名称"), ExcelColumn(title="用户账号")
    ]
    nickname: Annotated[
        str | None, Field(None, description="用户名称"), ExcelColumn(title="用户昵称")
    ]
    dept_id: Annotated[
        SnowflakeIdInput | None, Field(None, description="部门编号"), ExcelColumn(title="部门编号")
    ]
    email: Annotated[
        EmailStr | None, Field(None, description="用户邮箱"), ExcelColumn(title="用户邮箱")
    ]
    mobile: Annotated[
        str | None, Field(None, description="手机号码"), ExcelColumn(title="手机号码")
    ]
    sex: Annotated[
        int | None,
        Field(None, description="用户性别"),
        ExcelColumn(title="性别", converter=EnumConverter(CommonSexEnum)),
    ]
    status: Annotated[
        int | None,
        Field(None, description="账号状态"),
        ExcelColumn(title="状态", converter=EnumConverter(StatusEnum)),
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "dushan",
                    "nickname": "渡山",
                    "deptId": 1024,
                    "email": "729227973@qq.com",
                    "mobile": "18888888888",
                    "sex": 1,
                    "status": 1,
                }
            ]
        }
    }
