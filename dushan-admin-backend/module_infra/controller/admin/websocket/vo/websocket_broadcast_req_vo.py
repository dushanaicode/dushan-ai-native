from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_request_vo import BaseRequestVO
from module_infra.controller.admin.websocket.vo.websocket_message_vo import WebsocketMessageVO


class WebsocketBroadcastReqVO(BaseRequestVO):
    """管理后台 - WebSocket 广播消息 Request VO"""

    message: Annotated[
        WebsocketMessageVO, Field(description="消息内容，可以是JSON对象或JSON字符串")
    ]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {"message": {"type": "text", "payload": {"content": "Hello, world!"}}},
                {
                    "message": '{"type":"broadcast","payload":{"event":"new_announcement","title":"系统通知","content":"系统将于 2 小时后进行维护"}}'
                },
                {
                    "message": {
                        "type": "image",
                        "payload": {
                            "url": "https://example.com/image.jpg",
                            "width": 800,
                            "height": 600,
                        },
                    }
                },
                {
                    "message": {
                        "type": "file",
                        "payload": {
                            "url": "https://example.com/document.pdf",
                            "name": "文档.pdf",
                            "size": 1024,
                        },
                    }
                },
            ]
        }
    }
