from datetime import datetime

import pytest

from module_system.api.user.dto.admin_user_resp_dto import AdminUserRespDTO
from module_system.controller.admin.tenant.vo.package.tenant_package_resp_vo import (
    TenantPackageRespVO,
)
from module_system.controller.admin.tenant.vo.package.tenant_package_save_req_vo import (
    TenantPackageSaveReqVO,
)
from module_system.convert.notification.notice_log_convert import NoticeLogConvert
from module_system.dal.dataobject.notification.notice_log_do import NoticeLogDO
from module_system.dal.dataobject.notification.notice_message_do import NoticeMessageDO
from module_system.dal.dataobject.tenant.tenant_package_do import TenantPackageDO


@pytest.mark.parametrize("with_user", [True, False])
def test_notice_log_detail_converts_message_entities(with_user):
    created = datetime(2026, 10, 5, 10, 30)
    user_id = 9_007_199_254_740_995
    message = NoticeMessageDO(
        id=9_007_199_254_740_996,
        user_id=user_id,
        user_type=2,
        read_status=True,
        read_time=created,
        create_time=created,
    )
    log = NoticeLogDO(
        id=9_007_199_254_740_997,
        notice_id=9_007_199_254_740_998,
        notice_title="通知明细",
        notice_type=2,
        push_target_type=1,
        push_channels=["INTERNAL"],
        total_count=1,
        success_count=1,
        fail_count=0,
        push_status=1,
        create_time=created,
    )
    user_map = (
        {user_id: AdminUserRespDTO(id=user_id, username="demo", nickname="演示用户", status=1)}
        if with_user
        else {}
    )

    response = NoticeLogConvert.convert_detail(log, [message], user_map).to_response()

    assert response["id"] == str(log.id)
    assert response["messages"] == [
        {
            "id": str(message.id),
            "userId": str(user_id),
            "username": "demo" if with_user else None,
            "nickname": "演示用户" if with_user else None,
            "userType": 2,
            "readStatus": True,
            "readTime": "2026-10-05T10:30:00",
            "createTime": "2026-10-05T10:30:00",
        }
    ]


def test_tenant_package_quota_round_trips_request_storage_and_response():
    quota = {
        "ai": {
            "enabled": True,
            "billingMode": 3,
            "monthlyTokenLimit": 500_000,
            "monthlyAmountLimit": 100.0,
            "dailyTokenLimit": -1,
        }
    }
    request = TenantPackageSaveReqVO.model_validate(
        {"name": "套餐", "status": 1, "menuIds": ["1"], "quotaConfig": quota}
    )
    values = request.to_write_dict(fields={"name", "status", "menu_ids", "quota_config"})
    assert values["quota_config"]["ai"]["monthly_token_limit"] == 500_000
    package = TenantPackageDO(id=42, create_time=datetime(2026, 10, 5, 10, 30), **values)

    response = TenantPackageRespVO.model_validate(package).to_response()

    assert response["quotaConfig"] == quota
    assert response["menuIds"] == ["1"]
