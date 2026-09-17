from datetime import datetime
from typing import Annotated

from pydantic import Field

from framework.common.contracts.snowflake_id import (
    SnowflakeIdStr,
)
from framework.common.schemas.base_vo import BaseVO
from framework.starter_excel.model.excel_column import ExcelColumn


class MailAccountRespVO(BaseVO):
    """管理后台 - 邮箱账号信息 Response VO"""

    id: Annotated[SnowflakeIdStr, Field(..., description="编号"), ExcelColumn(title="编号")]
    mail: Annotated[str, Field(..., description="邮箱"), ExcelColumn(title="邮箱")]
    username: Annotated[str, Field(..., description="用户名"), ExcelColumn(title="用户名")]
    password: Annotated[
        str, Field(..., description="密码", exclude=True), ExcelColumn(title="密码")
    ]
    host: Annotated[
        str, Field(..., description="SMTP 服务器域名"), ExcelColumn(title="SMTP 服务器域名")
    ]
    port: Annotated[int, Field(..., description="SMTP 服务器端口"), ExcelColumn(title="SMTP 端口")]
    ssl_enable: Annotated[
        bool, Field(..., description="是否开启 ssl"), ExcelColumn(title="开启 ssl")
    ]
    starttls_enable: Annotated[
        bool, Field(..., description="是否开启 starttls"), ExcelColumn(title="开启 starttls")
    ]
    create_time: Annotated[
        datetime, Field(..., description="创建时间"), ExcelColumn(title="创建时间")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1024,
                    "mail": "729227973@qq.com",
                    "username": "dushan",
                    "password": "123456",
                    "host": "www.dushan.info",
                    "port": 80,
                    "sslEnable": True,
                    "starttlsEnable": True,
                    "createTime": "2020-05-20T05:20:00Z",
                }
            ]
        }
    }
