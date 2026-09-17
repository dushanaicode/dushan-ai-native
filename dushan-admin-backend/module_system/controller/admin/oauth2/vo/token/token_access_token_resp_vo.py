from datetime import datetime

from framework.common.contracts.snowflake_id import SnowflakeIdStr
from framework.common.schemas.base_vo import BaseVO


class OAuth2AccessTokenRespVO(BaseVO):
    """令牌管理只展示元数据；随机令牌不能从摘要恢复。"""

    id: SnowflakeIdStr
    refresh_token_id: SnowflakeIdStr | None
    family_id: str
    user_id: SnowflakeIdStr
    user_type: int
    client_id: str
    scopes: list[str] | None
    revoked: bool
    create_time: datetime
    expires_time: datetime
