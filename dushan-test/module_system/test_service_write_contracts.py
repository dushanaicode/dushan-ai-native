from contextlib import nullcontext
from datetime import datetime, timedelta
from inspect import unwrap
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from framework.common.enums import BuiltinTypeEnum, StatusEnum, UserTypeEnum
from framework.common.exception import ServiceException
from module_system.controller.admin.mail.vo.account.mail_account_save_req_vo import (
    MailAccountSaveReqVO,
)
from module_system.controller.admin.sms.vo.channel.sms_channel_save_req_vo import (
    SmsChannelSaveReqVO,
)
from module_system.controller.admin.social.vo.client.social_client_save_req_vo import (
    SocialClientSaveReqVO,
)
from module_system.controller.admin.tenant.vo.tenant.tenant_save_req_vo import TenantSaveReqVO
from module_system.dal.dataobject.mail.mail_account_do import MailAccountDO
from module_system.dal.dataobject.mail.mail_template_do import MailTemplateDO
from module_system.dal.dataobject.sms.sms_channel_do import SmsChannelDO
from module_system.dal.dataobject.sms.sms_template_do import SmsTemplateDO
from module_system.dal.dataobject.social.social_client_do import SocialClientDO
from module_system.dal.dataobject.tenant.tenant_do import TenantDO
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.definitions.enums.social.social_type_enum import SocialTypeEnum
from module_system.service.mail.mail_account_service_impl import MailAccountServiceImpl
from module_system.service.mail.mail_template_service_impl import MailTemplateServiceImpl
from module_system.service.sms.sms_channel_service_impl import SmsChannelServiceImpl
from module_system.service.sms.sms_template_service_impl import SmsTemplateServiceImpl
from module_system.service.social.social_client_service_impl import SocialClientServiceImpl
from module_system.service.tenant.tenant_service_impl import TenantServiceImpl


@pytest.mark.parametrize("password", [{}, {"password": None}, {"password": "replacement"}])
async def test_mail_account_update_preserves_unsubmitted_or_null_password(password):
    request = MailAccountSaveReqVO.model_validate(
        dict(
            id="42",
            mail="sender@example.com",
            username="sender",
            host="smtp.example.com",
            port=465,
            ssl_enable=True,
            starttls_enable=False,
            **password,
        )
    )
    service = MailAccountServiceImpl()
    service.database = SimpleNamespace(after_commit=Mock())
    service.mail_account_mapper = SimpleNamespace(
        select_by_id=AsyncMock(return_value=MailAccountDO(id=42)), update_by_id=AsyncMock()
    )

    await unwrap(service.update_mail_account)(service, request)

    written = service.mail_account_mapper.update_by_id.call_args.args[0]
    assert written.id == 42 and written.mail == request.mail
    if password.get("password") is None:
        assert "password" not in vars(written)
    else:
        assert written.password == "replacement"


@pytest.mark.parametrize(
    "optional",
    [
        {},
        {"api_key": None, "api_secret": None, "remark": None, "callback_url": None},
        {"api_key": "new-key", "api_secret": "new-secret"},
    ],
)
async def test_sms_channel_full_save_retains_secrets_and_clears_optional_fields(optional):
    request = SmsChannelSaveReqVO.model_validate(
        dict(id="42", signature="签名", code="ALIYUN", status=StatusEnum.ENABLE.code, **optional)
    )
    service = SmsChannelServiceImpl()
    service.sms_channel_mapper = SimpleNamespace(
        select_by_id=AsyncMock(return_value=SmsChannelDO(id=42, code="ALIYUN")),
        update_by_id=AsyncMock(),
    )

    await unwrap(service.update_sms_channel)(service, request)

    written = service.sms_channel_mapper.update_by_id.call_args.args[0]
    assert vars(written)["remark"] is None and vars(written)["callback_url"] is None
    for field in ("api_key", "api_secret"):
        if optional.get(field) is None:
            assert field not in vars(written)
        else:
            assert getattr(written, field) == optional[field]


@pytest.mark.parametrize(
    "optional",
    [
        {},
        {"agent_id": None, "client_secret": None},
        {"client_secret": "replacement", "auth_config": {}},
    ],
)
async def test_social_client_partial_save_preserves_secrets_and_explicit_clear(optional):
    request = SocialClientSaveReqVO.model_validate(
        dict(
            id="42",
            name="应用",
            social_type=SocialTypeEnum.GITHUB.code,
            user_type=UserTypeEnum.ADMIN.code,
            client_id="client",
            status=StatusEnum.ENABLE.code,
            **optional,
        )
    )
    service = SocialClientServiceImpl()
    service.social_client_mapper = SimpleNamespace(
        select_by_id=AsyncMock(
            return_value=SocialClientDO(
                id=42, auth_config={"credentials": {"alipay_secret": "preserved"}}
            )
        ),
        select_by_social_type_and_user_type=AsyncMock(return_value=None),
        update_by_id=AsyncMock(),
    )

    await unwrap(service.update_social_client)(service, request)

    written = service.social_client_mapper.update_by_id.call_args.args[0]
    assert ("agent_id" in vars(written)) == ("agent_id" in optional)
    if "agent_id" in optional:
        assert written.agent_id is None
    assert ("client_secret" in vars(written)) == (optional.get("client_secret") is not None)
    assert ("auth_config" in vars(written)) == ("auth_config" in optional)
    if "auth_config" in optional:
        assert written.client_secret == "replacement"
        assert written.auth_config == {"credentials": {"alipay_secret": "preserved"}}


@pytest.mark.parametrize("create", [True, False])
@pytest.mark.parametrize("optional", [{}, {"contact_mobile": None, "websites": None}])
async def test_tenant_full_save_excludes_credentials_and_keeps_optional_nulls(create, optional):
    payload = dict(
        name="租户",
        contact_name="联系人",
        status=StatusEnum.ENABLE.code,
        package_id="7",
        expire_time=datetime.now() + timedelta(days=1),
        account_count=5,
        username="tenantadmin",
        password="test-password",
        **optional,
    )
    if not create:
        payload["id"] = "42"
    request = TenantSaveReqVO.model_validate(payload)
    service = TenantServiceImpl()
    service.database = SimpleNamespace(next_id=lambda: 42, transaction=nullcontext)
    service.workloads = SimpleNamespace(scope=lambda *_: nullcontext())
    service.tenant_mapper = SimpleNamespace(
        select_by_name=AsyncMock(return_value=None),
        select_by_id=AsyncMock(return_value=TenantDO(id=42, package_id=7)),
        insert=AsyncMock(),
        update_by_id=AsyncMock(),
    )
    service.packages = SimpleNamespace(
        select_by_id=AsyncMock(
            return_value=SimpleNamespace(status=StatusEnum.ENABLE.code, menu_ids=[])
        )
    )
    service.roles = SimpleNamespace(insert=AsyncMock(return_value=SimpleNamespace(id=10)))
    service.users = SimpleNamespace(insert=AsyncMock(return_value=SimpleNamespace(id=11)))
    service.passwords = SimpleNamespace(hash=AsyncMock(return_value="hashed"))
    service.user_roles = SimpleNamespace(insert=AsyncMock())
    service.role_menus = SimpleNamespace(insert_batch=AsyncMock())
    service.revisions = SimpleNamespace(advance=AsyncMock())

    if create:
        assert await service.create_tenant(request) == 42
        written = service.tenant_mapper.insert.call_args.args[0]
        user = service.users.insert.call_args.args[0]
        assert user.username == "tenantadmin" and user.password == "hashed"
    else:
        await service.update_tenant(request)
        written = service.tenant_mapper.update_by_id.call_args.args[0]
    assert written.id == 42 and written.package_id == 7
    assert vars(written)["contact_mobile"] is None and vars(written)["websites"] is None
    assert "username" not in vars(written) and "password" not in vars(written)


@pytest.mark.parametrize(
    "service_type,mapper_name,method,record,error",
    [
        (
            MailAccountServiceImpl,
            "mail_account_mapper",
            "_validate_exists",
            MailAccountDO(id=42),
            ErrorCodeConstants.MAIL_ACCOUNT_NOT_EXISTS,
        ),
        (
            MailTemplateServiceImpl,
            "mail_template_mapper",
            "_validate_exists",
            MailTemplateDO(id=42),
            ErrorCodeConstants.MAIL_TEMPLATE_NOT_EXISTS,
        ),
        (
            SmsTemplateServiceImpl,
            "sms_template_mapper",
            "_validate_for_update",
            SmsTemplateDO(id=42, builtin=BuiltinTypeEnum.CUSTOM.code),
            ErrorCodeConstants.SMS_TEMPLATE_NOT_EXISTS,
        ),
        (
            TenantServiceImpl,
            "tenant_mapper",
            "valid_tenant",
            TenantDO(id=42, status=StatusEnum.ENABLE.code),
            ErrorCodeConstants.TENANT_NOT_EXISTS,
        ),
    ],
)
async def test_required_record_validation_returns_entity_or_business_error(
    service_type, mapper_name, method, record, error
):
    service = service_type()
    mapper = SimpleNamespace(select_by_id=AsyncMock(return_value=record))
    setattr(service, mapper_name, mapper)
    assert await getattr(service, method)(42) is record
    mapper.select_by_id.return_value = None
    with pytest.raises(ServiceException) as failure:
        await getattr(service, method)(42)
    assert failure.value.error_code == error


async def test_sms_template_builtin_guard_still_rejects_update():
    service = SmsTemplateServiceImpl()
    service.sms_template_mapper = SimpleNamespace(
        select_by_id=AsyncMock(
            return_value=SmsTemplateDO(id=42, builtin=BuiltinTypeEnum.BUILTIN.code)
        )
    )
    with pytest.raises(ServiceException) as failure:
        await service._validate_for_update(42)
    assert failure.value.error_code == ErrorCodeConstants.SMS_TEMPLATE_CAN_NOT_UPDATE_BUILTIN
