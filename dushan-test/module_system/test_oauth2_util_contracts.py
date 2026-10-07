from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit

import pytest

from module_system.api.oauth2.dto.oauth2_access_token_resp_dto import OAuth2AccessTokenRespDTO
from module_system.controller.admin.oauth2.oauth2_open_controller import Oauth2OpenController
from module_system.controller.admin.oauth2.vo.open.oauth2_authorize_req_vo import (
    OAuth2AuthorizeReqVO,
)
from module_system.convert.auth.auth_convert import AuthConvert
from module_system.convert.oauth2.oauth2_open_convert import OAuth2OpenConvert
from module_system.util.oauth2.oauth2_utils import OAuth2Utils

pytestmark = pytest.mark.unit


def test_authorization_redirect_replaces_duplicate_parameters_and_preserves_other_parts():
    result = OAuth2Utils.build_authorization_code_redirect_uri(
        "https://example.test/callback?keep=&code=old&code=older#done",
        "a+b&c",
        "hello world",
    )
    assert result == ("https://example.test/callback?keep=&code=a%2Bb%26c&state=hello+world#done")


@pytest.mark.parametrize("response_type", ["code", "token"])
def test_denied_redirect_encodes_errors_in_the_protocol_location(response_type):
    result = urlsplit(
        OAuth2Utils.build_unsuccessful_redirect(
            "https://example.test/callback?keep=#done",
            response_type,
            "state+&",
            "access_denied",
            "User denied & canceled",
        )
    )
    expected = {
        "error": ["access_denied"],
        "error_description": ["User denied & canceled"],
        "state": ["state+&"],
    }
    if response_type == "token":
        assert result.query == "keep="
        assert parse_qs(result.fragment) == expected
    else:
        assert result.fragment == "done"
        assert parse_qs(result.query, keep_blank_values=True) == {"keep": [""], **expected}


def test_implicit_redirect_returns_fragment_with_nonnegative_expiry():
    result = urlsplit(
        OAuth2Utils.build_implicit_redirect_uri(
            "https://example.test/callback?keep=#old",
            "access+&",
            "",
            datetime(2000, 1, 1),
            ["read", "write"],
            '{"name":"测试"}',
        )
    )
    assert result.query == "keep="
    assert parse_qs(result.fragment, keep_blank_values=True) == {
        "access_token": ["access+&"],
        "token_type": ["Bearer"],
        "expires_in": ["0"],
        "scope": ["read write"],
        "state": [""],
        "additional_information": ['{"name":"测试"}'],
    }


@pytest.mark.parametrize(
    "scope, expected", [(None, []), ("", []), (" read\twrite\n", ["read", "write"])]
)
def test_scopes_are_synchronous_and_whitespace_separated(scope, expected):
    assert OAuth2Utils.build_scopes(scope) == expected
    assert OAuth2Utils.build_scopes(OAuth2Utils.build_scope_str(expected)) == expected


def test_token_converters_preserve_expiry_units_without_date_dependency():
    expiry = datetime(2000, 1, 2, 3, 4, 5)
    refresh_expiry = datetime(2000, 2, 2, 3, 4, 5)
    token = OAuth2AccessTokenRespDTO(
        access_token="access",
        refresh_token="refresh",
        user_id=123,
        user_type=2,
        tenant_id="1",
        client_id="client",
        scopes=["read", "write"],
        expires_time=expiry,
        refresh_expires_time=refresh_expiry,
    )
    login = AuthConvert.convert_oauth_to_auth_login_resp(token)
    assert login.user_id == "123"
    assert login.tenant_id == "1"
    assert login.access_token == "access"
    assert login.refresh_token == "refresh"
    assert login.expires_time == int(expiry.replace(tzinfo=timezone.utc).timestamp() * 1000)
    assert login.refresh_expires_time == int(
        refresh_expiry.replace(tzinfo=timezone.utc).timestamp() * 1000
    )
    opened = OAuth2OpenConvert.convert(token)
    assert opened.access_token == "access"
    assert opened.refresh_token == "refresh"
    assert opened.token_type == "Bearer"
    assert opened.scope == "read write"
    assert opened.expires_in == 0


@pytest.mark.parametrize(
    "response_type, approved", [("code", True), ("token", True), ("code", False), ("token", False)]
)
async def test_controller_uses_synchronous_redirect_helpers(response_type, approved):
    client = SimpleNamespace(client_id="client", additional_information=None)
    clients = SimpleNamespace(validate_client=AsyncMock(return_value=client))
    approvals = SimpleNamespace(update_after_approval=AsyncMock(return_value=approved))
    grants = SimpleNamespace(
        grant_authorization_code_for_code=AsyncMock(return_value="code+&"),
        grant_implicit=AsyncMock(
            return_value=SimpleNamespace(access_token="access+&", expires_time=datetime(2000, 1, 1))
        ),
    )
    result = await Oauth2OpenController.approve_or_deny(
        req_vo=OAuth2AuthorizeReqVO(
            redirect_uri="https://example.test/callback",
            auto_approve=False,
            response_type=response_type,
            client_id="client",
            scope='{"read":true}',
            state="state+&",
        ),
        oauth2_grant_service=grants,
        oauth2_client_service=clients,
        oauth2_approve_service=approvals,
        security=SimpleNamespace(require=lambda: SimpleNamespace(account_id="123")),
    )
    redirect = urlsplit(result.data)
    parameters = parse_qs(redirect.fragment if response_type == "token" else redirect.query)
    assert parameters["state"] == ["state+&"]
    if not approved:
        assert parameters["error"] == ["access_denied"]
        grants.grant_authorization_code_for_code.assert_not_awaited()
        grants.grant_implicit.assert_not_awaited()
    elif response_type == "code":
        assert parameters["code"] == ["code+&"]
    else:
        assert parameters["access_token"] == ["access+&"]
        assert parameters["scope"] == ["read"]
