from datetime import datetime
from typing import Annotated, Any

from pydantic import Field, field_validator

from framework.common.contracts.snowflake_id import (
    SnowflakeCursorStr,
    SnowflakeIdStr,
)
from framework.common.enums.user_type_enum import UserTypeEnum
from framework.common.schemas.base_vo import BaseVO
from framework.common.validator.in_enum import InEnum
from framework.common.validator.not_empty import NotEmpty
from framework.common.validator.not_null import NotNull
from framework.starter_excel.converter.enum_converter import EnumConverter
from framework.starter_excel.model.excel_column import ExcelColumn
from module_system.definitions.enums.logger.logger_login_result_enum import LoggerLoginResultEnum
from module_system.definitions.enums.logger.login_log_type_enum import LoginLogTypeEnum


class LoginLogRespVO(BaseVO):
    """管理后台 - 登录日志信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="日志编号"), ExcelColumn(title="日志主键")]
    log_type: Annotated[
        int,
        Field(..., description="日志类型，参见 LoginLogTypeEnum 枚举类"),
        ExcelColumn(title="日志类型", converter=EnumConverter(LoginLogTypeEnum)),
    ]
    user_id: Annotated[SnowflakeCursorStr | None, Field(None, description="用户编号")]
    user_type: Annotated[int, Field(..., description="用户类型，参见 UserTypeEnum 枚举")]
    trace_id: Annotated[str | None, Field(None, description="链路追踪编号")]
    username: Annotated[str, Field(..., description="用户账号"), ExcelColumn(title="用户账号")]
    result: Annotated[
        int,
        Field(..., description="登录结果，参见 LoggerLoginResultEnum 枚举类"),
        ExcelColumn(title="登录结果", converter=EnumConverter(LoggerLoginResultEnum)),
    ]
    user_ip: Annotated[str, Field(..., description="用户 IP"), ExcelColumn(title="登录 IP")]
    user_agent: Annotated[
        str | None, Field(None, description="浏览器 UserAgent"), ExcelColumn(title="浏览器 UA")
    ]
    create_time: Annotated[
        datetime, Field(..., description="登录时间"), ExcelColumn(title="登录时间")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "logType": 1,
                    "userId": 666,
                    "userType": 2,
                    "traceId": "89aca178-a370-411c-ae02-3f0d672be4ab",
                    "username": "dushan",
                    "result": 1,
                    "userIp": "127.0.0.1",
                    "userAgent": "Mozilla/5.0",
                    "createTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="id", value=v, error_msg="日志编号不能为空")
        return v

    @field_validator("log_type", mode="before")
    @classmethod
    def _validate_log_type(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="log_type", value=v, error_msg="日志类型不能为空")
        InEnum.require_in_enum(
            field_name="log_type",
            value=v,
            enum_class=LoginLogTypeEnum,
            error_msg="日志类型必须在指定范围",
        )
        return v

    @field_validator("user_type", mode="before")
    @classmethod
    def _validate_user_type(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="user_type", value=v, error_msg="用户类型不能为空")
        InEnum.require_in_enum(
            field_name="user_type",
            value=v,
            enum_class=UserTypeEnum,
            error_msg="用户类型必须在指定范围",
        )
        return v

    @field_validator("username", mode="before")
    @classmethod
    def _validate_username(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="username", value=v, error_msg="用户账号不能为空")
        return v

    @field_validator("result", mode="before")
    @classmethod
    def _validate_result(cls, v: Any) -> Any:
        NotNull.require_not_null(field_name="result", value=v, error_msg="登录结果不能为空")
        InEnum.require_in_enum(
            field_name="result",
            value=v,
            enum_class=LoggerLoginResultEnum,
            error_msg="登录结果必须在指定范围",
        )
        return v

    @field_validator("user_ip", mode="before")
    @classmethod
    def _validate_user_ip(cls, v: Any) -> Any:
        NotEmpty.require_not_empty(field_name="user_ip", value=v, error_msg="用户 IP 不能为空")
        return v
