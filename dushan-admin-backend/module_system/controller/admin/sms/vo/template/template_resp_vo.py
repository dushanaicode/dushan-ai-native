from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdStr,
)
from framework.common.enums import StatusEnum
from framework.common.schemas import BaseVO
from framework.starter_excel.public import (
    EnumConverter,
    ExcelColumn,
)
from module_system.definitions.enums.sms.sms_template_type_enum import SmsTemplateTypeEnum
from module_system.framework.sms.enums.sms_channel_enum import SmsChannelEnum


class SmsTemplateRespVO(BaseVO):
    """管理后台 - 短信模板信息 Response VO"""

    id: Annotated[SnowflakeIdStr | None, Field(None, description="编号"), ExcelColumn(title="编号")]
    type: Annotated[
        int | None,
        Field(None, description="短信类型，参见 SmsTemplateTypeEnum 枚举类"),
        ExcelColumn(title="短信类型", converter=EnumConverter(SmsTemplateTypeEnum)),
    ]
    builtin: Annotated[int | None, Field(None, description="内置类型，参见 BuiltinTypeEnum")]
    status: Annotated[
        int | None,
        Field(None, description="开启状态，参见 StatusEnum 枚举类"),
        ExcelColumn(title="开启状态", converter=EnumConverter(StatusEnum)),
    ]
    code: Annotated[str | None, Field(None, description="模板编码"), ExcelColumn(title="模板编码")]
    name: Annotated[str | None, Field(None, description="模板名称"), ExcelColumn(title="模板名称")]
    content: Annotated[
        str | None, Field(None, description="模板内容"), ExcelColumn(title="模板内容")
    ]
    params: Annotated[list[str] | None, Field(None, description="参数数组")]
    remark: Annotated[str | None, Field(None, description="备注"), ExcelColumn(title="备注")]
    api_template_id: Annotated[
        str | None,
        Field(None, description="短信 API 的模板编号"),
        ExcelColumn(title="短信 API 的模板编号"),
    ]
    channel_id: Annotated[
        SnowflakeIdStr | None,
        Field(None, description="短信渠道编号"),
        ExcelColumn(title="短信渠道编号"),
    ]
    channel_code: Annotated[
        str | None,
        Field(None, description="短信渠道编码"),
        ExcelColumn(title="短信渠道编码", converter=EnumConverter(SmsChannelEnum)),
    ]
    create_time: Annotated[
        datetime | None, Field(None, description="创建时间"), ExcelColumn(title="创建时间")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "type": 1,
                    "status": 1,
                    "code": "test_01",
                    "name": "dushan",
                    "content": "你好，{name}。{like}！",
                    "params": ["name", "code"],
                    "remark": "哈哈哈",
                    "apiTemplateId": "4383920",
                    "channelId": 10,
                    "channelCode": "ALIYUN",
                    "createTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }
