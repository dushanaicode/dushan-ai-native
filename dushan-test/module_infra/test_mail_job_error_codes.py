import inspect
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from starlette.requests import Request

from framework.common.enums import UserTypeEnum
from framework.common.exception import ServiceException
from framework.common.schemas.request import IdReqVO
from framework.starter_web.exception.global_exception_handler import GlobalExceptionHandler
from module_infra.controller.admin.job.job_log_controller import JobLogController
from module_infra.definitions.constants.error_code_constants import (
    ErrorCodeConstants as InfraErrors,
)
from module_infra.service.job.job_service_impl import JobServiceImpl
from module_system.api.social.dto.social_user_bind_req_dto import SocialUserBindReqDTO
from module_system.definitions.constants.error_code_constants import (
    ErrorCodeConstants as SystemErrors,
)
from module_system.definitions.enums.social.social_type_enum import SocialTypeEnum
from module_system.service.social.social_user_service_impl import SocialUserServiceImpl


async def assert_localized_response(error, locale, expected_code, expected_message):
    """用实际语言资源和异常响应入口验证专用业务码及翻译。"""
    module, domain, key = error.message_key.split(".")
    resources = (
        Path(__file__).resolve().parents[2]
        / "dushan-admin-backend"
        / f"module_{module}"
        / "definitions/i18n"
        / f"{locale}.json"
    )
    messages = json.loads(resources.read_text(encoding="utf-8"))
    translator = SimpleNamespace(
        translate_any_scope=Mock(return_value=messages[module][domain][key])
    )
    request = Request(
        {
            "type": "http",
            "headers": [(b"accept-language", locale.encode())],
            "method": "GET",
            "path": "/test",
        }
    )
    response = await GlobalExceptionHandler(translator=translator).handle_business_exception(
        request, error
    )
    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["code"] == expected_code
    assert body["message"] == expected_message
    assert body["data"] is None
    assert not error.is_system_error
    assert not error.record_error
    translator.translate_any_scope.assert_called_once_with(
        error.message_key, locale, default=error.msg, args=[]
    )


@pytest.mark.parametrize(
    "locale,message",
    [
        ("zh-CN", "定时任务日志不存在"),
        ("en-US", "Scheduled job log does not exist"),
    ],
)
async def test_missing_job_log_uses_localized_business_error(locale, message):
    """不存在或不可见的日志均使用可翻译的专用错误。"""
    service = SimpleNamespace(get_job_log=AsyncMock(return_value=None))
    with pytest.raises(ServiceException) as failure:
        await JobLogController.get_job_log(IdReqVO(id="99"), service)
    service.get_job_log.assert_awaited_once_with(99)
    assert failure.value.error_code == InfraErrors.JOB_LOG_NOT_EXISTS
    await assert_localized_response(failure.value, locale, 1001001013, message)


@pytest.mark.parametrize(
    "locale,message",
    [
        ("zh-CN", "该社交身份已绑定其他账号"),
        ("en-US", "This social identity is already bound to another account"),
    ],
)
async def test_social_binding_conflict_is_localized_without_mutation(locale, message):
    """拒绝抢占社交绑定且不执行删除或写入。"""
    service = SocialUserServiceImpl()
    service.permission_service = SimpleNamespace(require_user_writable=AsyncMock())
    service._auth_social_user = AsyncMock(return_value=SimpleNamespace(id=7))
    service.social_user_bind_mapper = SimpleNamespace(
        select_by_user_type_and_social_user_id=AsyncMock(return_value=SimpleNamespace(user_id=2)),
        delete_by_user_type_and_social_user_id=AsyncMock(),
        delete_by_user_type_and_user_id_and_social_type=AsyncMock(),
        insert=AsyncMock(),
    )
    req = SocialUserBindReqDTO(
        user_id=1,
        user_type=UserTypeEnum.ADMIN.code,
        type=next(iter(SocialTypeEnum)).code,
        code="authorization-code",
        state="state",
    )
    with pytest.raises(ServiceException) as failure:
        await inspect.unwrap(SocialUserServiceImpl.bind_social_user)(service, req)
    service.permission_service.require_user_writable.assert_awaited_once_with(1)
    mapper = service.social_user_bind_mapper
    mapper.delete_by_user_type_and_social_user_id.assert_not_awaited()
    mapper.delete_by_user_type_and_user_id_and_social_type.assert_not_awaited()
    mapper.insert.assert_not_awaited()
    assert failure.value.error_code == SystemErrors.SOCIAL_USER_ALREADY_BOUND
    await assert_localized_response(failure.value, locale, 1002032015, message)


@pytest.mark.parametrize(
    "locale,message",
    [
        ("zh-CN", "手动触发使用已保存参数；修改参数需更新任务定义"),
        (
            "en-US",
            "Manual execution uses saved parameters; update the job definition to change them",
        ),
    ],
)
async def test_trigger_parameter_mismatch_is_business_error(locale, message):
    """触发参数冲突不调度任务，也不再作为系统故障返回。"""
    row = SimpleNamespace(id=11, handler_param="{}")
    service = JobServiceImpl()
    service.mapper = SimpleNamespace(select_by_handler_name=AsyncMock(return_value=row))
    service._require = AsyncMock(return_value=row)
    service.native = SimpleNamespace(trigger=AsyncMock())
    with pytest.raises(ServiceException) as failure:
        await inspect.unwrap(JobServiceImpl.trigger_job_by_handler)(service, "handler", "[]")
    service._require.assert_awaited_once_with(11)
    service.native.trigger.assert_not_awaited()
    assert failure.value.error_code == InfraErrors.JOB_PARAMETERS_MISMATCH
    await assert_localized_response(failure.value, locale, 1001001014, message)


async def test_trigger_saved_parameters_keeps_native_result():
    """保存参数一致时仍返回调度器原始结果。"""
    row = SimpleNamespace(id=11, handler_param="{}")
    service = JobServiceImpl()
    service.mapper = SimpleNamespace(select_by_handler_name=AsyncMock(return_value=row))
    service._require = AsyncMock(return_value=row)
    service.native = SimpleNamespace(trigger=AsyncMock(return_value="request-11"))
    result = await inspect.unwrap(JobServiceImpl.trigger_job_by_handler)(service, "handler", "{}")
    assert result == "request-11"
    service.native.trigger.assert_awaited_once_with("11")
