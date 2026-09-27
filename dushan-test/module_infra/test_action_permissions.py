import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="module")
ROOT = Path(__file__).resolve().parents[2]


async def test_seed_and_permission_response_cover_all_frontend_action_codes(admin_client):
    response = (await admin_client.get("/admin-api/system/auth/get-permission-info")).json()
    assert response["code"] == 0, response
    assert response["data"]["roles"] == ["super_admin"]
    permissions = set(response["data"]["permissions"])
    expected = set()
    for path in (ROOT / "dushan-admin-frontend/apps/web-ele/src").rglob("*"):
        if path.suffix in {".vue", ".ts"}:
            expected.update(
                re.findall(
                    r"['\"]((?:system|infra):[a-zA-Z0-9:*-]+)['\"]",
                    path.read_text(encoding="utf-8"),
                )
            )
    assert expected <= permissions, sorted(expected - permissions)


async def test_initial_menu_data_has_current_action_permissions(infra_database):
    with infra_database[2].cursor() as cursor:
        cursor.execute(
            "SELECT id, permission FROM system_menu WHERE id BETWEEN 10000000100122 AND 10000000100126 ORDER BY id"
        )
        assert cursor.fetchall() == tuple(
            (10000000100122 + index, "infra:config:" + operation)
            for index, operation in enumerate(("query", "create", "update", "delete", "export"))
        )
        cursor.execute(
            "SELECT permission FROM system_menu WHERE id IN (10000000100215, 10000000100216) ORDER BY id"
        )
        assert cursor.fetchall() == (("infra:file:create",), ("infra:file:update",))
        cursor.execute(
            "SELECT permission,kind,status,parent_id FROM system_menu WHERE id=10000000100803"
        )
        assert cursor.fetchone() == ("infra:websocket:send", "action", 1, 10000000100801)


async def test_release_seed_has_three_linked_users(infra_database):
    assert not (ROOT / "dushan-admin-backend/sql/mysql" / "upgrade").exists()
    ids = (10100000010001, 10100000010002, 10100000010003)
    with infra_database[2].cursor() as cursor:
        cursor.execute("SELECT id,username FROM system_users ORDER BY id")
        assert cursor.fetchall() == tuple(zip(ids, ("admin", "dushan", "zhangsan")))
        for table in ("system_user_profiles", "system_user_role", "system_user_post"):
            cursor.execute(f"SELECT user_id FROM {table} ORDER BY user_id")
            assert cursor.fetchall() == tuple((identifier,) for identifier in ids)
        cursor.execute("SELECT name FROM system_dept WHERE parent_id=0")
        assert cursor.fetchall() == (("渡山无界",),)
