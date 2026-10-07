import json
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio(loop_scope="module")
async def test_user_profile_patch_preserves_omissions_and_persists_clear_values(
    admin_client, system_app, system_database
):
    """通过真实接口与数据库验证资料省略、清空、空集合和非法昵称的写入合同。"""
    username = "profile" + uuid4().hex[:8]
    created = (
        await admin_client.post(
            "/admin-api/system/user/create",
            json={"username": username, "nickname": "资料用户", "password": "Profile123!"},
        )
    ).json()
    assert created["code"] == 0, created
    user_id = created["data"]
    async with AsyncClient(
        transport=ASGITransport(app=system_app), base_url="http://testserver"
    ) as client:
        login = (
            await client.post(
                "/admin-api/system/auth/login",
                json={"username": username, "password": "Profile123!"},
                headers={"X-Tenant-Id": "1"},
            )
        ).json()
        assert login["code"] == 0, login
        client.headers["Authorization"] = "Bearer " + login["data"]["accessToken"]
        initial = (
            await client.put(
                "/admin-api/system/user/profile/update",
                json={
                    "email": username + "@example.com",
                    "sex": 1,
                    "avatar": "https://example.com/avatar.png",
                    "bio": "原简介",
                    "address": "保持地址",
                    "tags": ["原标签"],
                    "skills": ["原技能"],
                    "aiPreference": {"style": "concise"},
                },
            )
        ).json()
        assert initial["code"] == 0, initial
        cleared = (
            await client.put(
                "/admin-api/system/user/profile/update",
                json={
                    "email": None,
                    "sex": None,
                    "avatar": None,
                    "bio": None,
                    "tags": [],
                    "skills": [],
                    "aiPreference": {},
                },
            )
        ).json()
        assert cleared["code"] == 0, cleared
        rejected = (
            await client.put(
                "/admin-api/system/user/profile/update", json={"nickname": None, "address": None}
            )
        ).json()
        assert rejected["code"] == 400, rejected
        current = (await client.get("/admin-api/system/user/profile/get")).json()
        assert current["code"] == 0, current
        assert current["data"]["nickname"] == "资料用户"
        assert current["data"]["posts"] == []
        assert current["data"]["address"] == "保持地址"
    with system_database[2].cursor() as cursor:
        cursor.execute(
            "SELECT nickname, email, sex, avatar FROM system_users WHERE id=%s", (user_id,)
        )
        assert cursor.fetchone() == ("资料用户", None, None, None)
        cursor.execute(
            "SELECT bio, address, tags, skills, ai_preference FROM system_user_profiles "
            "WHERE user_id=%s AND deleted=0",
            (user_id,),
        )
        bio, address, tags, skills, preference = cursor.fetchone()
        assert bio is None
        assert address == "保持地址"
        assert json.loads(tags) == []
        assert json.loads(skills) == []
        assert json.loads(preference) == {}
