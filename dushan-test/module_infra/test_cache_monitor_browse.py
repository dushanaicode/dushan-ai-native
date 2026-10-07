import pytest

pytestmark = pytest.mark.asyncio(loop_scope="module")
PREFIX = "/admin-api/infra/cache/monitor"


async def test_owner_can_list_db_keys_and_read_key_detail(admin_client):
    """Redis 监控页按 DB 浏览键与查看键详情，登录会话本身会在 default 中留下键。"""
    keys = (
        await admin_client.get(PREFIX + "/db-keys", params={"dbName": "default", "pattern": "*"})
    ).json()
    assert keys["code"] == 0, keys
    assert keys["data"], keys
    detail = (
        await admin_client.get(
            PREFIX + "/key-detail", params={"dbName": "default", "key": keys["data"][0]}
        )
    ).json()
    assert detail["code"] == 0, detail
