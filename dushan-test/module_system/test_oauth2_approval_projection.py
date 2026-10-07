from unittest.mock import Mock

import pytest

from module_system.api.oauth2.dto.oauth2_client_dto import OAuth2ClientDTO
from module_system.convert.oauth2 import oauth2_open_convert
from module_system.convert.oauth2.oauth2_open_convert import OAuth2OpenConvert
from module_system.dal.dataobject.oauth2.oauth2_approve_do import OAuth2ApproveDO

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("approvals", "expected"),
    [
        ([], ["False", "False", "False"]),
        ([("read", True), ("write", False)], ["False", "True", "False"]),
        ([("read", True), ("read", False)], ["False", "False", "False"]),
        ([("read", False), ("read", True)], ["False", "True", "False"]),
        ([("other", True)], ["False", "False", "False"]),
    ],
)
def test_approval_projection_preserves_order_and_values_without_creating_entities(
    monkeypatch, approvals, expected
):
    """批准映射保留顺序、字符串协议和最后一条记录，转换时不构造 ORM 实体。"""
    client = OAuth2ClientDTO(
        id=1,
        client_id="test",
        name="测试应用",
        logo="",
        status=1,
        access_token_validity_seconds=60,
        refresh_token_validity_seconds=120,
        credential_revision=1,
        scopes=["missing", "read", "write"],
    )
    rows = [OAuth2ApproveDO(scope=scope, approved=approved) for scope, approved in approvals]
    constructor = Mock(side_effect=AssertionError("转换不应构造持久化实体"))
    monkeypatch.setattr(oauth2_open_convert, "OAuth2ApproveDO", constructor)

    result = OAuth2OpenConvert.convert_oauth_info(client, rows)

    assert [scope.key for scope in result.scopes] == client.scopes
    assert [scope.value for scope in result.scopes] == expected
    assert result.client.name == client.name
    assert result.client.logo == client.logo
    constructor.assert_not_called()
