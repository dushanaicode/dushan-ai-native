from typing import Annotated

from pydantic import Field

from framework.common.schemas import BaseRequestVO


class OnlineForceLogoutReqVO(BaseRequestVO):
    """管理后台 - 强制退出在线用户 Request VO"""

    token_id: Annotated[str, Field(..., description="会话编号")]
    model_config = {"json_schema_extra": {"examples": [{"tokenId": "abc123"}]}}
