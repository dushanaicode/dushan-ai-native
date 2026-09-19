from datetime import datetime

from framework.common.schemas import BaseDTO


class OAuth2SessionDTO(BaseDTO):
    family_id: str
    user_id: int
    username: str
    nickname: str | None
    dept_name: str | None
    ipaddr: str | None
    login_location: str | None
    browser: str | None
    os: str | None
    login_time: datetime
