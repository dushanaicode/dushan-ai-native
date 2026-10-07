from inspect import unwrap
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from framework.common.enums import StatusEnum
from framework.common.exception import ServiceException
from module_system.controller.admin.dept.vo.post.post_save_req_vo import PostSaveReqVO
from module_system.controller.admin.oauth2.vo.client.oauth2_client_save_req_vo import (
    OAuth2ClientSaveReqVO,
)
from module_system.dal.dataobject.dept.dept_do import DeptDO
from module_system.dal.dataobject.dept.post_do import PostDO
from module_system.dal.dataobject.dict.dict_data_do import DictDataDO
from module_system.dal.dataobject.dict.dict_type_do import DictTypeDO
from module_system.dal.dataobject.oauth2.oauth2_client_do import OAuth2ClientDO
from module_system.definitions.constants.error_code_constants import ErrorCodeConstants
from module_system.service.dept.dept_service_impl import DeptServiceImpl
from module_system.service.dept.post_service_impl import PostServiceImpl
from module_system.service.dict.dict_data_service_impl import DictDataServiceImpl
from module_system.service.dict.dict_type_service_impl import DictTypeServiceImpl
from module_system.service.oauth2.oauth2_client_service_impl import OAuth2ClientServiceImpl

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "service_type,mapper_name,method_name,entity_type,error_code",
    [
        (
            PostServiceImpl,
            "post_mapper",
            "_validate_exists",
            PostDO,
            ErrorCodeConstants.POST_NOT_FOUND,
        ),
        (
            DeptServiceImpl,
            "dept_mapper",
            "_validate_dept_exists",
            DeptDO,
            ErrorCodeConstants.DEPT_NOT_FOUND,
        ),
        (
            DictDataServiceImpl,
            "dict_data_mapper",
            "_validate_exists",
            DictDataDO,
            ErrorCodeConstants.DICT_DATA_NOT_EXISTS,
        ),
        (
            DictTypeServiceImpl,
            "dict_type_mapper",
            "_validate_exists",
            DictTypeDO,
            ErrorCodeConstants.DICT_TYPE_NOT_EXISTS,
        ),
        (
            OAuth2ClientServiceImpl,
            "oauth2_client_mapper",
            "_validate_exists",
            OAuth2ClientDO,
            ErrorCodeConstants.OAUTH2_CLIENT_NOT_EXISTS,
        ),
    ],
)
async def test_required_entity_returns_record_or_business_error(
    service_type, mapper_name, method_name, entity_type, error_code
):
    service = service_type()
    entity = entity_type(id=10)
    mapper = SimpleNamespace(select_by_id=AsyncMock(return_value=entity))
    setattr(service, mapper_name, mapper)
    validate = getattr(service, method_name)

    assert await validate(10) is entity
    mapper.select_by_id.assert_awaited_once_with(10)

    mapper.select_by_id.return_value = None
    with pytest.raises(ServiceException) as error:
        await validate(20)
    assert error.value.error_code == error_code


async def test_create_post_checks_uniqueness_without_loading_existing_record():
    service = PostServiceImpl()

    async def insert(post):
        post.id = 10

    service.post_mapper = SimpleNamespace(
        select_by_id=AsyncMock(),
        select_by_name=AsyncMock(return_value=None),
        select_by_code=AsyncMock(return_value=None),
        insert=AsyncMock(side_effect=insert),
    )
    request = PostSaveReqVO(name="测试岗位", code="fixture", sort=1, status=StatusEnum.ENABLE.code)

    assert await unwrap(PostServiceImpl.create_post)(service, request) == 10
    service.post_mapper.select_by_id.assert_not_awaited()
    service.post_mapper.select_by_name.assert_awaited_once_with(request.name)
    service.post_mapper.select_by_code.assert_awaited_once_with(request.code)


@pytest.mark.parametrize("id_values", [{}, {"id": "20"}])
async def test_update_post_requires_existing_record_before_writing(id_values):
    service = PostServiceImpl()
    service.post_mapper = SimpleNamespace(
        select_by_id=AsyncMock(return_value=None),
        select_by_name=AsyncMock(),
        update_by_id=AsyncMock(),
    )
    request = PostSaveReqVO(
        name="测试岗位", code="fixture", sort=1, status=StatusEnum.ENABLE.code, **id_values
    )

    with pytest.raises(ServiceException) as error:
        await unwrap(PostServiceImpl.update_post)(service, request)
    assert error.value.error_code == ErrorCodeConstants.POST_NOT_FOUND
    service.post_mapper.select_by_name.assert_not_awaited()
    service.post_mapper.update_by_id.assert_not_awaited()


async def test_dict_type_reference_returns_enabled_record_and_rejects_invalid_reference():
    service = DictDataServiceImpl()
    entity = DictTypeDO(id=10, type="fixture", status=StatusEnum.ENABLE.code)
    service.dict_type_service = SimpleNamespace(
        get_dict_type_by_type=AsyncMock(return_value=entity)
    )

    assert await service._validate_dict_type_exists("fixture") is entity
    entity.status = StatusEnum.DISABLE.code
    with pytest.raises(ServiceException) as error:
        await service._validate_dict_type_exists("fixture")
    assert error.value.error_code == ErrorCodeConstants.DICT_TYPE_NOT_ENABLE

    service.dict_type_service.get_dict_type_by_type.return_value = None
    with pytest.raises(ServiceException) as error:
        await service._validate_dict_type_exists("fixture")
    assert error.value.error_code == ErrorCodeConstants.DICT_TYPE_NOT_EXISTS


@pytest.mark.parametrize(
    "changes", [{}, {"secret": None}, {"secret": "Updated-OAuth-Secret-123456789!AaBb"}]
)
async def test_oauth_client_update_reuses_validated_record_and_preserves_secret(changes):
    service = OAuth2ClientServiceImpl()
    client = OAuth2ClientDO(id=10, secret="Original-OAuth-Secret-123456789!AaBb")
    service.database = SimpleNamespace(after_commit=Mock())
    service.oauth2_client_mapper = SimpleNamespace(
        select_by_id=AsyncMock(return_value=client),
        select_by_client_id=AsyncMock(return_value=client),
        update_by_id=AsyncMock(),
        update_by_condition=AsyncMock(),
    )
    request = OAuth2ClientSaveReqVO(
        id="10",
        client_id="fixture",
        name="测试客户端",
        logo="https://example.com/logo.png",
        status=StatusEnum.ENABLE.code,
        access_token_validity_seconds=3600,
        refresh_token_validity_seconds=7200,
        redirect_uris=["https://example.com/callback"],
        authorized_grant_types=["authorization_code"],
        **changes,
    )

    await unwrap(OAuth2ClientServiceImpl.update_oauth2_client)(service, request)

    service.oauth2_client_mapper.select_by_id.assert_awaited_once_with(10)
    written = service.oauth2_client_mapper.update_by_id.await_args.args[0]
    assert written.secret == (changes.get("secret") or client.secret)
    assert written.id == 10
    assert written.description is None
    service.oauth2_client_mapper.update_by_condition.assert_awaited_once()
