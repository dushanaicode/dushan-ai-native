import json

import pytest
from pydantic import ValidationError

from framework.starter_security.enums.security_realm import SecurityRealm
from framework.starter_security.enums.tenant_access_mode import TenantAccessMode
from framework.starter_security.model.login_session import LoginSession
from framework.starter_web.routing.route_policy import RoutePolicy


@pytest.fixture
def session_payload():
    return {
        "application_id": "enum-test",
        "domain": "admin",
        "token_digest": "a" * 64,
        "session_id": "session",
        "family_id": "family",
        "account_id": "account",
        "realm": "account",
        "expires_at": "2099-01-01T00:00:00Z",
        "revoked": False,
        "account_enabled": True,
        "credential_revision": 1,
        "current_credential_revision": 1,
        "authorization_revision": "1",
        "scopes": [],
    }


@pytest.mark.parametrize(
    "authority",
    [
        {"realm": "account"},
        {"realm": "platform", "platform_operator_id": "operator"},
        {
            "realm": "tenant",
            "tenant_id": "tenant",
            "access_mode": "direct_membership",
            "membership_id": "member",
            "authority_tenant_id": "tenant",
            "authority_membership_id": "member",
        },
        {
            "realm": "tenant",
            "tenant_id": "tenant",
            "access_mode": "group_managed",
            "authority_tenant_id": "group-tenant",
            "authority_membership_id": "group-member",
            "group_id": "group",
            "management_relation_id": "relation",
        },
        {
            "realm": "support",
            "tenant_id": "tenant",
            "platform_operator_id": "operator",
            "support_session_id": "support",
            "approved_resource": "overview",
            "approved_action": "read",
        },
    ],
)
def test_session_enum_roundtrip_preserves_wire_codes(session_payload, authority):
    session = LoginSession.model_validate_json(json.dumps(session_payload | authority))
    assert session.realm is SecurityRealm.from_code(authority["realm"])
    assert session.realm.code == session.realm.value == authority["realm"]
    assert session.realm.label != session.realm.code
    if "access_mode" in authority:
        assert session.access_mode is TenantAccessMode.from_code(authority["access_mode"])
    encoded = json.loads(session.model_dump_json())
    assert all(encoded[name] == value for name, value in authority.items())
    assert LoginSession.model_validate_json(session.model_dump_json()) == session

    # JSON 边界解析编码；内部 Python 模型继续要求已经解析的枚举成员。
    with pytest.raises(ValidationError, match="realm"):
        LoginSession.model_validate(session.model_dump() | {"realm": authority["realm"]})
    if "access_mode" in authority:
        with pytest.raises(ValidationError, match="access_mode"):
            LoginSession.model_validate(
                session.model_dump() | {"access_mode": authority["access_mode"]}
            )


def test_enum_openapi_names_and_values_remain_stable():
    definitions = LoginSession.model_json_schema()["$defs"]
    assert definitions["SecurityRealm"]["type"] == "string"
    assert definitions["SecurityRealm"]["enum"] == ["account", "tenant", "platform", "support"]
    assert definitions["TenantAccessMode"]["type"] == "string"
    assert definitions["TenantAccessMode"]["enum"] == ["direct_membership", "group_managed"]


def test_route_policy_requires_typed_security_enums():
    with pytest.raises(TypeError, match="realm"):
        RoutePolicy(realm="tenant")
    with pytest.raises(ValueError, match="租户访问模式"):
        RoutePolicy(
            realm=SecurityRealm.TENANT,
            allowed_tenant_access_modes=frozenset({"group_managed"}),
        )
    policy = RoutePolicy(realm=SecurityRealm.TENANT)
    assert policy.allowed_tenant_access_modes == frozenset({TenantAccessMode.DIRECT_MEMBERSHIP})
