from datetime import datetime
from typing import Annotated, Any

from pydantic import Field

from framework.common.contracts import SnowflakeIdStr
from framework.common.enums import UserTypeEnum
from framework.common.schemas import BaseVO
from framework.starter_excel.public import (
    EnumConverter,
    ExcelColumn,
    JsonConverter,
)
from module_system.definitions.enums.mail.mail_send_status_enum import MailSendStatusEnum


class MailLogRespVO(BaseVO):
    """管理后台 - 邮件日志信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="编号"), ExcelColumn(title="编号")]
    user_id: Annotated[
        SnowflakeIdStr | None, Field(None, description="用户编号"), ExcelColumn(title="用户编号")
    ]
    user_type: Annotated[
        int | None,
        Field(None, description="用户类型，参见 UserTypeEnum 枚举"),
        ExcelColumn(title="用户类型", converter=EnumConverter(UserTypeEnum)),
    ]
    to_mail: Annotated[str, Field(..., description="接收邮箱地址"), ExcelColumn(title="接收邮箱")]
    cc_mail: Annotated[
        str | None, Field(None, description="抄送邮箱地址"), ExcelColumn(title="抄送邮箱")
    ]
    bcc_mail: Annotated[
        str | None, Field(None, description="密送邮箱地址"), ExcelColumn(title="密送邮箱")
    ]
    account_id: Annotated[
        SnowflakeIdStr, Field(..., description="邮箱账号编号"), ExcelColumn(title="邮箱账号编号")
    ]
    from_mail: Annotated[str, Field(..., description="发送邮箱地址"), ExcelColumn(title="发送邮箱")]
    template_id: Annotated[
        SnowflakeIdStr, Field(..., description="模板编号"), ExcelColumn(title="模板编号")
    ]
    template_code: Annotated[str, Field(..., description="模板编码"), ExcelColumn(title="模板编码")]
    template_nickname: Annotated[
        str | None, Field(None, description="模板发送人名称"), ExcelColumn(title="模板发送人名称")
    ]
    template_title: Annotated[
        str, Field(..., description="邮件标题"), ExcelColumn(title="邮件标题")
    ]
    template_content: Annotated[
        str, Field(..., description="邮件内容"), ExcelColumn(title="邮件内容")
    ]
    template_params: Annotated[
        dict[str, Any],
        Field(..., description="模版参数"),
        ExcelColumn(title="模板参数", converter=JsonConverter()),
    ]
    send_status: Annotated[
        int,
        Field(..., description="发送状态，参见 MailSendStatusEnum 枚举"),
        ExcelColumn(title="发送状态", converter=EnumConverter(MailSendStatusEnum)),
    ]
    send_time: Annotated[
        datetime | None, Field(None, description="发送时间"), ExcelColumn(title="发送时间")
    ]
    send_message_id: Annotated[
        str | None, Field(None, description="发送返回的消息 ID"), ExcelColumn(title="消息 ID")
    ]
    send_exception: Annotated[
        str | None, Field(None, description="发送异常"), ExcelColumn(title="发送异常")
    ]
    create_time: Annotated[
        datetime, Field(..., description="创建时间"), ExcelColumn(title="创建时间")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 31020,
                    "userId": 30883,
                    "userType": 2,
                    "toMail": "729227973@qq.com",
                    "ccMail": "cc1@example.com,cc2@example.com",
                    "bccMail": "bcc1@example.com,bcc2@example.com",
                    "accountId": 18107,
                    "fromMail": "729227973@qq.com",
                    "templateId": 5678,
                    "templateCode": "test_01",
                    "templateNickname": "渡山",
                    "templateTitle": "测试标题",
                    "templateContent": "测试内容",
                    "templateParams": {},
                    "sendStatus": 1,
                    "sendTime": "2020-05-20 05:20:00",
                    "sendMessageId": "1",
                    "sendException": None,
                    "createTime": "2020-05-20 05:20:00",
                }
            ]
        }
    }
