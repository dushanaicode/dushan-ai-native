from datetime import datetime
from typing import Annotated

from pydantic import EmailStr, Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.enums.status_enum import StatusEnum
from framework.common.schemas.base_vo import BaseVO
from framework.common.validator.in_enum import InEnum
from framework.starter_excel.converter.enum_converter import EnumConverter
from framework.starter_excel.converter.ids_converter import IdsConverter
from framework.starter_excel.model.excel_column import ExcelColumn
from module_system.definitions.enums.common.common_sex_enum import CommonSexEnum


class UserRespVO(BaseVO):
    """管理后台 - 用户信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="用户编号"), ExcelColumn(title="用户编号")]
    username: Annotated[str, Field(..., description="用户账号"), ExcelColumn(title="用户账号")]
    nickname: Annotated[str, Field(..., description="用户昵称"), ExcelColumn(title="用户昵称")]
    remark: Annotated[str | None, Field(None, description="备注"), ExcelColumn(title="备注")]
    dept_id: Annotated[SnowflakeIdStr | None, Field(None, description="部门ID")]
    dept_name: Annotated[
        str | None, Field(None, description="部门名称"), ExcelColumn(title="部门名称")
    ]
    post_ids: Annotated[
        list[SnowflakeIdStr] | None,
        Field(None, description="岗位编号数组"),
        ExcelColumn(title="岗位", converter=IdsConverter("posts")),
    ]
    email: Annotated[
        EmailStr | None, Field(None, description="用户邮箱"), ExcelColumn(title="用户邮箱")
    ]
    mobile: Annotated[
        str | None, Field(None, description="手机号码"), ExcelColumn(title="手机号码")
    ]
    sex: Annotated[
        int | None,
        Field(None, description="用户性别，参见 CommonSexEnum 枚举类"),
        ExcelColumn(title="用户性别", converter=EnumConverter(CommonSexEnum)),
    ]
    avatar: Annotated[
        str | None, Field(None, description="用户头像"), ExcelColumn(title="用户头像")
    ]
    status: Annotated[
        int,
        Field(..., description="状态，参见 StatusEnum 枚举类"),
        ExcelColumn(title="状态", converter=EnumConverter(StatusEnum)),
    ]
    login_ip: Annotated[
        str, Field(..., description="最后登录 IP"), ExcelColumn(title="最后登录 IP")
    ]
    login_date: Annotated[
        datetime | None, Field(None, description="最后登录时间"), ExcelColumn(title="最后登录时间")
    ]
    create_time: Annotated[
        datetime | None, Field(None, description="创建时间"), ExcelColumn(title="创建时间")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "username": "dushan",
                    "nickname": "渡山",
                    "remark": "我是一个用户",
                    "deptId": 1024,
                    "deptName": "IT 部",
                    "postIds": [1],
                    "email": "729227973@qq.com",
                    "mobile": "18888888888",
                    "sex": 1,
                    "avatar": "https://www.dushan.cn/xxx.png",
                    "status": 1,
                    "loginIp": "192.168.1.1",
                    "loginDate": "2020-05-20T05:20:00Z",
                    "createTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }

    @field_validator("sex", mode="before")
    @classmethod
    def _validate_sex_in_enum(cls, v: int | None) -> int | None:
        if v is not None:
            InEnum.require_in_enum(
                field_name="sex",
                value=v,
                enum_class=CommonSexEnum,
                error_msg="用户性别必须在指定范围内",
            )
        return v

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status_in_enum(cls, v: int) -> int:
        InEnum.require_in_enum(
            field_name="status", value=v, enum_class=StatusEnum, error_msg="状态必须在指定范围内"
        )
        return v

    @field_validator("email", mode="before")
    @classmethod
    def _empty_str_to_none(cls, v):
        """
        如果传入 '' 或 全是空白，就返回 None，
        这样下面的 EmailStr | None 校验就能通过。
        """
        if isinstance(v, str) and (not v.strip()):
            return None
        return v
