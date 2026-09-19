from typing import Annotated

from pydantic import Field

from framework.common.contracts import (
    SnowflakeIdInput,
)
from framework.common.schemas import BaseRequestVO
from module_infra.controller.admin.websocket.vo.websocket_message_vo import WebsocketMessageVO


class WebsocketSendToUserReqVO(BaseRequestVO):
    """管理后台 - WebSocket 发送消息给指定用户 Request VO"""

    user_type: Annotated[int, Field(..., description="用户类型")]
    user_id: Annotated[SnowflakeIdInput, Field(..., description="用户编号")]
    message: Annotated[
        WebsocketMessageVO, Field(..., description="消息内容，可以是JSON对象或JSON字符串")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "userType": 1,
                    "userId": 1024,
                    "message": {"type": "text", "payload": {"content": "Hello, world!"}},
                },
                {
                    "userType": 1,
                    "userId": 1024,
                    "message": '{"type":"broadcast","payload":{"event":"new_announcement","title":"系统通知","content":"系统将于 2 小时后进行维护"}}',
                },
                {
                    "userType": 1,
                    "userId": 1024,
                    "message": {
                        "type": "image",
                        "payload": {
                            "url": "https://example.com/image.jpg",
                            "width": 800,
                            "height": 600,
                        },
                    },
                },
                {
                    "userType": 1,
                    "userId": 1024,
                    "message": {
                        "type": "file",
                        "payload": {
                            "url": "https://example.com/document.pdf",
                            "name": "文档.pdf",
                            "size": 1024,
                        },
                    },
                },
            ]
        }
    }
