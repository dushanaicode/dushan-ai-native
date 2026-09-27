from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from framework.common.security.request_identity import RequestIdentity
from framework.starter_ip.public import IpLocation
from framework.starter_security.bizlog.log_record_operation import LogRecordOperation
from framework.starter_security.model.request_audit import RequestAudit
from framework.starter_security.public import SecurityRealm
from module_system.controller.admin.logger.vo.operatelog.operatelog_operate_log_resp_vo import (
    OperateLogRespVO,
)
from module_system.service.logger.operate_log_service_impl import OperateLogServiceImpl

AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
)


@pytest.mark.parametrize("ip_enabled", [False, True])
async def test_reservation_freezes_actor_and_current_request_location(ip_enabled):
    service = OperateLogServiceImpl()
    user = SimpleNamespace(username="admin", nickname="管理员", dept_id=758634341423771648)
    service.users = SimpleNamespace(select_by_id=AsyncMock(return_value=user))
    service.ip_settings = SimpleNamespace(enabled=ip_enabled)
    service.ip_locations = SimpleNamespace(
        lookup=AsyncMock(return_value=IpLocation("127.0.0.1", "loopback", "回环地址"))
    )

    async def insert(row):
        row.id = 101

    service.operate_log_mapper = SimpleNamespace(insert=AsyncMock(side_effect=insert))
    operation = LogRecordOperation(
        event_id=uuid4().hex,
        type="SYSTEM 用户",
        sub_type="修改用户",
        occurred_at=datetime.now(timezone.utc),
        identity=RequestIdentity(principal_id="1", tenant_id="1"),
        realm=SecurityRealm.TENANT,
        actor_tenant_id="1",
        membership_id=None,
        trace_id="trace",
        request=RequestAudit("PUT", "/system/user/update", "127.0.0.1", AGENT),
    )
    await service.reserve.__wrapped__(service, operation)
    row = service.operate_log_mapper.insert.call_args.args[0]
    user.nickname = "事后改名"
    assert row.user_info["nickname"] == "管理员"
    assert row.user_info["username"] == "admin"
    assert row.user_info["dept_id"] == "758634341423771648"
    assert row.user_info["location_status"] == ("loopback" if ip_enabled else "disabled")
    assert row.user_ip == "127.0.0.1"
    assert row.user_agent == AGENT
    if ip_enabled:
        assert row.user_info["location"] == "回环地址"
        service.ip_locations.lookup.assert_awaited_once_with("127.0.0.1")
    else:
        service.ip_locations.lookup.assert_not_awaited()


@pytest.mark.parametrize("agent", [AGENT, ""])
def test_existing_log_client_information_is_derived_from_its_recorded_user_agent(agent):
    response = OperateLogRespVO(
        id="101",
        trace_id="trace",
        user_id="1",
        type="SYSTEM 用户",
        sub_type="修改用户",
        biz_id="2",
        request_method="PUT",
        request_url="/system/user/update",
        user_ip="127.0.0.1",
        user_agent=agent,
        create_time=datetime.now(timezone.utc),
        user_info={},
    ).model_dump(by_alias=True)
    assert response["browser"] == ("Chrome 153.0.0" if agent else None)
    assert response["os"] == ("Windows 10" if agent else None)
    assert response["userInfo"] == {}


@pytest.mark.asyncio(loop_scope="module")
async def test_real_operation_records_actor_snapshot_and_returns_browser(admin_client):
    response = await admin_client.post(
        "/admin-api/system/user/create",
        headers={"User-Agent": AGENT},
        json={
            "username": "audit" + uuid4().hex[:8],
            "nickname": "审计验证用户",
            "password": "AuditTest123!",
        },
    )
    assert response.json()["code"] == 0, response.text
    user_id = response.json()["data"]
    response = await admin_client.get(
        "/admin-api/system/logger/operate-log/page",
        params={"page": 1, "pageSize": 20, "bizId": user_id},
    )
    assert response.json()["code"] == 0, response.text
    log = response.json()["data"]["items"][0]
    assert log["browser"] == "Chrome 153.0.0"
    assert log["os"] == "Windows 10"
    assert log["userInfo"]["username"] == "admin"
    assert log["userInfo"]["nickname"]
    assert isinstance(log["userInfo"]["dept_id"], str)
    assert log["userInfo"]["location_status"] == "disabled"
    assert log["userIp"] == "127.0.0.1"
    assert "password" not in log["userInfo"]
