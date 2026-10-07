from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import ValidationError

from module_infra.framework.websocket.handler.user_info_message_handler import (
    UserInfoMessageHandler,
)
from module_infra.framework.websocket.handler.user_info_resp_vo import UserInfoRespVO
from module_infra.framework.websocket.infra_socket_payload import InfraSocketPayload
from module_system.api.user.dto.admin_user_resp_dto import AdminUserRespDTO

pytestmark = pytest.mark.unit


class ExtendedAdminUserRespDTO(AdminUserRespDTO):
    internal_secret: str


@pytest.mark.parametrize(
    ("dept_id", "post_ids", "mobile", "avatar"),
    [
        (None, set(), None, None),
        (9007199254740995, {9007199254740997, 9007199254740999}, "13800138000", "avatar.png"),
    ],
)
async def test_user_info_message_preserves_public_response(dept_id, post_ids, mobile, avatar):
    """消息保持八个公开字段、字符串 ID、空关联和统一响应封装。"""
    user = AdminUserRespDTO(
        id=9007199254740993,
        username=" admin ",
        nickname="管理员",
        status=0,
        dept_id=dept_id,
        post_ids=post_ids,
        mobile=mobile,
        avatar=avatar,
    )
    handler = UserInfoMessageHandler()
    handler.service = SimpleNamespace(get_user=AsyncMock(return_value=user))
    handler.security = SimpleNamespace(
        require=Mock(return_value=SimpleNamespace(account_id=str(user.id)))
    )
    context = SimpleNamespace(reply=AsyncMock())

    await handler.handle(None, context)

    handler.service.get_user.assert_awaited_once_with(user.id)
    handler.security.require.assert_called_once_with()
    context.reply.assert_awaited_once_with(
        "get-user-info-response",
        InfraSocketPayload(
            data={
                "id": str(user.id),
                "username": " admin ",
                "nickname": "管理员",
                "status": 0,
                "deptId": None if dept_id is None else str(dept_id),
                "postIds": [str(identifier) for identifier in post_ids],
                "mobile": mobile,
                "avatar": avatar,
            }
        ),
    )


async def test_user_info_message_does_not_expose_new_dto_fields():
    """内部 DTO 扩展不会自动增加 WebSocket 的公开响应字段。"""
    user = ExtendedAdminUserRespDTO(
        id=1, username="admin", nickname="管理员", status=0, internal_secret="不公开"
    )
    handler = UserInfoMessageHandler()
    handler.service = SimpleNamespace(get_user=AsyncMock(return_value=user))
    handler.security = SimpleNamespace(require=Mock(return_value=SimpleNamespace(account_id="1")))

    result = await handler.process_message()

    assert set(result) == {
        "id",
        "username",
        "nickname",
        "status",
        "deptId",
        "postIds",
        "mobile",
        "avatar",
    }


@pytest.mark.parametrize("invalid_fields", [{"id": 0}, {"dept_id": -1}, {"post_ids": {1 << 63}}])
def test_user_info_response_rejects_invalid_snowflake_ids(invalid_fields):
    """响应边界复用雪花编号契约，拒绝非法主键及关联编号。"""
    user = AdminUserRespDTO(id=1, username="admin", nickname="管理员", status=0)
    user = user.model_copy(update=invalid_fields)

    with pytest.raises(ValidationError):
        UserInfoRespVO.model_validate(user)
