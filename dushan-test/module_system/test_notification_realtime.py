import asyncio
import json
import os
import socket
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
import uvicorn
from httpx import AsyncClient
from websockets.asyncio.client import connect
from websockets.exceptions import InvalidStatus

from fixtures.config_factory import ConfigFactory

pytestmark = pytest.mark.asyncio(loop_scope="module")
ORIGIN = os.environ.get("DUSHAN_NOTIFICATION_ORIGIN", "http://notification.test")


@pytest.fixture(scope="module")
def system_allowed_origins():
    return ["http://testserver", ORIGIN]


@pytest.fixture(scope="module", autouse=True)
def enable_notification_socket():
    original = ConfigFactory.values

    def values():
        data = original()
        data["config"]["models"]["websocket"].update(
            enabled=True,
            transport="redis",
            signing_secret=uuid4().hex + uuid4().hex,
            allowed_origins=[ORIGIN],
        )
        return data

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(ConfigFactory, "values", staticmethod(values))
        yield


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def notification_server(system_app):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(
            system_app,
            host="127.0.0.1",
            port=port,
            lifespan="off",
            log_level="warning",
            access_log=False,
        )
    )
    task = asyncio.create_task(server.serve(sockets=[listener]))
    try:
        for _ in range(100):
            if server.started:
                break
            if task.done():
                await task
            await asyncio.sleep(0.05)
        assert server.started
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        await asyncio.wait_for(task, timeout=15)
        listener.close()


async def login(client, username="admin", password="admin123"):
    result = (
        await client.post(
            "/admin-api/system/auth/login",
            headers={"X-Tenant-Id": "1"},
            json={"username": username, "password": password},
        )
    ).json()
    assert result["code"] == 0, result
    client.headers["Authorization"] = "Bearer " + result["data"]["accessToken"]


async def ticket(client):
    result = (await client.post("/admin-api/system/auth/websocket-ticket")).json()
    assert result["code"] == 0, result
    return result["data"]


async def test_notice_routes_ticket_delivery_and_unread(notification_server):
    async with AsyncClient(base_url=notification_server, timeout=10) as client:
        await login(client)
        page = (
            await client.get(
                "/admin-api/system/notification/page", params={"page": 1, "pageSize": 20}
            )
        ).json()
        assert page["code"] == 0
        assert (await client.get("/admin-api/system/notification/notice/page")).json()[
            "code"
        ] == 404
        user = (await client.get("/admin-api/system/auth/get-permission-info")).json()["data"][
            "user"
        ]
        created = (
            await client.post(
                "/admin-api/system/notification/create",
                json={
                    "title": "实时通知集成验证",
                    "content": "仅发送到独立测试账号",
                    "type": 1,
                    "userType": 2,
                    "channels": ["INTERNAL"],
                    "status": 1,
                    "publisher": "测试",
                },
            )
        ).json()
        assert created["code"] == 0, created
        notice_id = created["data"]
        assert isinstance(notice_id, str)
        ws_base = notification_server.replace("http://", "ws://") + "/api/ws"
        one_use = await ticket(client)
        address = f"{ws_base}?audience=system&ticket={one_use}"
        with pytest.raises(InvalidStatus) as rejected:
            async with connect(address, origin="http://untrusted.test"):
                pytest.fail("错误 Origin 不应接受")
        assert rejected.value.response.status_code == 403
        async with connect(address, origin=ORIGIN) as ws:
            connected = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            assert connected["type"] == "connect"
            await ws.send(json.dumps({"type": "ping", "requestId": "heartbeat-check"}))
            pong = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            assert pong["type"] == "pong"
            pushed = (
                await client.post(
                    "/admin-api/system/notification/push-targets",
                    json={
                        "id": notice_id,
                        "userIds": [user["id"]],
                    },
                )
            ).json()
            assert pushed["code"] == 0, pushed
            frame = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            assert frame["type"] == "notification"
            assert set(frame["payload"]) == {"messageId"}
            assert frame["requestId"]
            message_id = frame["payload"]["messageId"]
            assert isinstance(message_id, str)
        with pytest.raises(InvalidStatus):
            async with connect(address, origin=ORIGIN):
                pytest.fail("票据不可重复消费")
        items = (await client.get("/admin-api/system/notification/message/get-unread-list")).json()
        assert items["code"] == 0, items
        assert any(
            item["id"] == message_id and item["noticeTitle"] == "实时通知集成验证"
            for item in items["data"]
        )
        assert items["data"][0]["publisherInfo"]["id"] == user["id"]
        logs = (
            await client.get(
                "/admin-api/system/notification/log/page", params={"page": 1, "pageSize": 20}
            )
        ).json()
        assert logs["code"] == 0, logs
        assert logs["data"]["items"][0]["publisherInfo"]["id"] == user["id"]
        assert (await client.get("/admin-api/system/notification/message/get-unread-count")).json()[
            "data"
        ] == 1
        async with connect(
            f"{ws_base}?audience=system&ticket={await ticket(client)}", origin=ORIGIN
        ):
            refreshed = (
                await client.get("/admin-api/system/notification/message/get-unread-list")
            ).json()
            assert refreshed["data"][0]["id"] == message_id
        read = (
            await client.put(
                "/admin-api/system/notification/message/update-read", json={"ids": [message_id]}
            )
        ).json()
        assert read["code"] == 0, read
        assert (await client.get("/admin-api/system/notification/message/get-unread-count")).json()[
            "data"
        ] == 0


async def test_live_browser_window(notification_server, request):
    """显式指定浏览器验收文件时保留隔离服务，供外部浏览器完成真实链路。"""
    case_name = os.environ.get("DUSHAN_NOTIFICATION_BROWSER_CASE")
    if case_name is None:
        pytest.skip("未配置外部浏览器验收会话")
    if request.session.testsfailed:
        pytest.skip("先修复后端协议用例，再启动浏览器验收")
    path = Path(case_name).resolve()
    assert path.is_relative_to((Path.cwd() / "Temp").resolve())
    path.write_text(
        json.dumps({"backendUrl": notification_server, "origin": ORIGIN}), encoding="utf-8"
    )
    result_path = path.with_name("browser-result.json")
    for _ in range(1200):
        if result_path.exists():
            assert json.loads(result_path.read_text(encoding="utf-8"))["passed"] is True
            return
        await asyncio.sleep(0.5)
    pytest.fail("浏览器验收未在 10 分钟内结束；保留证据并关闭测试服务")
