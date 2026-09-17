from typing import Annotated

from pydantic import Field

from framework.common.schemas.base_dto import BaseDTO


class NotificationRecipient(BaseDTO):
    """通知接收者的最小身份及联系方式，不暴露完整用户实体。"""

    id: int
    email: Annotated[str | None, Field(None)]
    mobile: Annotated[str | None, Field(None)]
    nickname: Annotated[str | None, Field(None)]
