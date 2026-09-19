from datetime import datetime, timedelta, timezone

import pytest

from framework.starter_security.core.opaque_token import OpaqueToken
from framework.starter_security.core.password_encoder import PasswordEncoder
from framework.starter_security.definitions.constants.security_error_codes import SecurityErrorCodes
from framework.starter_security.exception.security_exception import SecurityException
from framework.starter_web.routing.route_policy import RoutePolicy


async def test_public_protected_bearer_and_identity_source(security_factory):
    async with security_factory() as case:
        token, _ = await case.issue()
        assert (await case.get(path="/public")).status_code == 200
        missing = await case.get()
        assert (
            missing.status_code == 200 and missing.json()["code"] == SecurityErrorCodes.MISSING.code
        )
        assert missing.headers["www-authenticate"] == "Bearer"
        response = await case.get(
            token, headers={"user_id": "root", "roles": "admin", "tenant_id": "other"}
        )
        assert response.json() == {"account": "account-1", "tenant": None}
        assert set(missing.json()) == {"code", "message", "data"} or set(missing.json()) == {
            "code",
            "message",
            "data",
            "error",
        }
        assert case.service.context.current() is None
        schema = case.app.openapi()
        assert schema["paths"]["/protected"]["get"]["security"]


@pytest.mark.parametrize(
    "header",
    [
        "Basic abc",
        "Bearer short",
        "Bearer a.b.c",
        "Bearer " + "x" * 257,
        "Bearer " + "x" * 32 + " ",
        "Bearer",
        "Bearer " + "é" * 32,
    ],
)
async def test_malformed_bearer_rejected_before_provider(security_factory, header):
    async with security_factory() as case:
        if "é" in header:
            headers = [(b"authorization", header.encode("latin1"))]
        else:
            headers = {"authorization": header}
        response = await case.client.get("/protected", headers=headers)
        assert response.json()["code"] == SecurityErrorCodes.INVALID.code
        assert "invalid_token" in response.headers["www-authenticate"]
        assert case.service.tokens.reads == 0


async def test_duplicate_credentials_rejected(security_factory):
    async with security_factory() as case:
        token, _ = await case.issue()
        response = await case.client.get(
            "/protected",
            headers=[("Authorization", "Bearer " + token), ("Authorization", "Bearer " + token)],
        )
        assert response.json()["code"] == SecurityErrorCodes.INVALID.code
        assert case.service.tokens.reads == 0


@pytest.mark.parametrize(
    ("change", "message", "expected"),
    [
        (
            {"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)},
            "过期",
            SecurityErrorCodes.EXPIRED.code,
        ),
        ({"revoked": True}, "撤销", SecurityErrorCodes.REVOKED.code),
        ({"account_enabled": False}, "禁用", SecurityErrorCodes.DISABLED.code),
        ({"current_credential_revision": 2}, "失效", SecurityErrorCodes.CREDENTIALS.code),
        ({"application_id": "foreign"}, "无效", SecurityErrorCodes.INVALID.code),
        ({"domain": "foreign"}, "无效", SecurityErrorCodes.INVALID.code),
    ],
)
async def test_live_session_state_is_checked(security_factory, change, message, expected):
    async with security_factory() as case:
        token, _ = await case.issue(**change)
        response = await case.get(token)
        assert response.json()["code"] == expected and message in response.json()["message"]
        assert response.headers["www-authenticate"] == 'Bearer error="invalid_token"'


async def test_no_token_parsing_or_provider_digest_substitution(security_factory, monkeypatch):
    async with security_factory() as case:
        token, session = await case.issue()

        async def bogus(*args, **kwargs):
            return session

        monkeypatch.setattr(case.service.tokens, "resolve", bogus)
        assert (await case.get(OpaqueToken.generate())).json()[
            "code"
        ] == SecurityErrorCodes.INVALID.code
        assert (await case.get(token)).status_code == 200


async def test_logout_revokes_family(security_factory):
    async with security_factory() as case:
        first, session = await case.issue()
        second, _ = await case.issue(family_id=session.family_id)
        unrelated, _ = await case.issue()
        with case.application.execution():
            await case.service.logout(first)
        for token in (first, second):
            response = await case.get(token)
            assert (
                response.json()["code"] == SecurityErrorCodes.REVOKED.code
                and "撤销" in response.json()["message"]
            )
        assert (await case.get(unrelated)).json()["account"] == "account-1"


async def test_roles_permissions_scopes_and_any_policy(security_factory):
    policy = RoutePolicy(
        ("write", "read"), roles=("reader",), scopes=("profile",), permission_mode="any"
    )
    async with security_factory(policy=policy) as case:
        good, _ = await case.issue()
        no_role, _ = await case.issue(roles=())
        no_scope, _ = await case.issue(scopes=frozenset())
        denied, _ = await case.issue(granted=())
        assert (await case.get(good)).json()["account"] == "account-1"
        for token in (no_role, no_scope, denied):
            response = await case.get(token)
            assert response.json()["code"] == SecurityErrorCodes.DENIED.code
            assert "insufficient_scope" in response.headers["www-authenticate"]


async def test_password_real_hash_rounds_unicode_and_errors(security_factory):
    async with security_factory() as case:
        with case.application.execution():
            encoder = case.application.get_bean(PasswordEncoder)
            hashed = await encoder.hash("安全密码🔐")
            assert hashed.startswith("$2b$12$") and "安全" not in hashed
            assert await encoder.verify("安全密码🔐", hashed)
            assert not await encoder.verify("wrong", hashed)
            for plain in ("é" * 37, "a" * 73, ""):
                with pytest.raises(ValueError):
                    await encoder.hash(plain)
            for invalid in (
                "plaintext",
                "$2b$04$" + "x" * 53,
                "$2a$12$" + "x" * 53,
                "$2b$31$" + "x" * 53,
            ):
                with pytest.raises(ValueError):
                    await encoder.verify("password", invalid)
            boundary = await encoder.hash("é" * 36)
            assert await encoder.verify("é" * 36, boundary)


def test_token_entropy_format_and_no_weak_fallback():
    tokens = {OpaqueToken.generate() for _ in range(200)}
    assert len(tokens) == 200 and all(len(item) == 64 for item in tokens)
    with pytest.raises(SecurityException):
        OpaqueToken.digest("eyJhbGciOiJub25lIn0.eyJzdWIiOiJyb290In0.")


async def test_explicit_permission_queries_revalidate_and_logout_clears_context(security_factory):
    async with security_factory(cache=True) as case:
        token, session = await case.issue()
        with case.application.execution():
            async with case.service.authorized(token, RoutePolicy()):
                assert await case.service.has_permissions("read")
                assert await case.service.has_roles("reader")
                assert await case.service.has_scopes("profile")
                await case.change(session, authorization_revision="next", granted=(), roles=())
                assert not await case.service.has_permissions("read")
                assert not await case.service.has_roles("reader")
                await case.service.logout(token)
                assert case.service.context.current() is None


async def test_enum_permission_uses_current_native_enum_contract(security_factory):
    from framework.common.enums.base_enum import BaseEnum

    class Operation(BaseEnum):
        READ = (1, "读取")
        WRITE = (2, "修改")

        @property
        def permission(self):
            return "read" if self is Operation.READ else "write"

    async with security_factory() as case:
        token, _ = await case.issue()
        with case.application.execution():
            async with case.service.authorized(token, RoutePolicy()):
                await case.service.require_enum_permission(1, Operation)
                for code in (2, None, True, "1", 3):
                    with pytest.raises(SecurityException):
                        await case.service.require_enum_permission(code, Operation)
