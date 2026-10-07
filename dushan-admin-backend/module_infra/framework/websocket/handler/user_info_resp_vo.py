from framework.common.contracts import SnowflakeIdStr
from framework.common.schemas import BaseVO


class UserInfoRespVO(BaseVO):
    """用户信息消息的公开响应字段。"""

    id: SnowflakeIdStr
    username: str
    nickname: str
    status: int
    dept_id: SnowflakeIdStr | None
    post_ids: list[SnowflakeIdStr]
    mobile: str | None
    avatar: str | None
