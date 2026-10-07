from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from framework.common.exception import ServiceException
from module_infra.api.file.file_api_impl import FileApiImpl
from module_infra.dal.dataobject.file.file_do import FileDO
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.definitions.enums.file.file_visibility_enum import FileVisibilityEnum
from module_infra.service.file.bo.file_content_bo import FileContentBO
from module_infra.service.file.file_service_impl import FileServiceImpl

pytestmark = pytest.mark.unit


@pytest.fixture
def file_service():
    row = FileDO(name="报告.txt", type="image/png", visibility=FileVisibilityEnum.PUBLIC.code)
    mapper = SimpleNamespace(select_by_storage_path=AsyncMock(return_value=row))
    storage = SimpleNamespace(get_content=AsyncMock(return_value=b"content"))
    configs = SimpleNamespace(get_file_client=AsyncMock(return_value=storage))
    service = FileServiceImpl()
    service.file_mapper, service.file_config_service = mapper, configs
    return service, mapper, storage, configs


@pytest.mark.parametrize(
    "visibility,public_only",
    [
        (FileVisibilityEnum.PUBLIC, True),
        (FileVisibilityEnum.PUBLIC, False),
        (FileVisibilityEnum.PRIVATE, False),
    ],
)
async def test_find_file_returns_database_name_and_mime(file_service, visibility, public_only):
    service, mapper, storage, configs = file_service
    mapper.select_by_storage_path.return_value.visibility = visibility.code

    file = await service.find_file(7, "docs/report_123456.txt", public_only=public_only)

    assert file == FileContentBO(name="报告.txt", type="image/png", content=b"content")
    mapper.select_by_storage_path.assert_awaited_once_with(7, "docs/report_123456.txt")
    configs.get_file_client.assert_awaited_once_with(7)
    storage.get_content.assert_awaited_once_with("docs/report_123456.txt")


@pytest.mark.parametrize("unavailable", ["missing_record", "private_record", "missing_object"])
async def test_find_file_returns_none_for_unavailable_files(file_service, unavailable):
    service, mapper, storage, configs = file_service
    if unavailable == "missing_record":
        mapper.select_by_storage_path.return_value = None
    elif unavailable == "private_record":
        mapper.select_by_storage_path.return_value.visibility = FileVisibilityEnum.PRIVATE.code
    else:
        storage.get_content.side_effect = FileNotFoundError("docs/report.txt")

    assert await service.find_file(7, "docs/report.txt", public_only=True) is None

    if unavailable == "missing_object":
        storage.get_content.assert_awaited_once_with("docs/report.txt")
    else:
        configs.get_file_client.assert_not_awaited()
        storage.get_content.assert_not_awaited()


async def test_find_file_does_not_hide_storage_failures(file_service):
    service, _, storage, _ = file_service
    storage.get_content.side_effect = PermissionError("access denied")
    with pytest.raises(PermissionError, match="access denied"):
        await service.find_file(7, "docs/report.txt", public_only=False)


async def test_find_file_preserves_missing_configuration_error(file_service):
    service, _, storage, configs = file_service
    configs.get_file_client.return_value = None
    with pytest.raises(ServiceException) as caught:
        await service.find_file(7, "docs/report.txt", public_only=False)
    assert caught.value.error_code is ErrorCodeConstants.FILE_CONFIG_DATA_NOT_EXISTS
    storage.get_content.assert_not_awaited()


@pytest.fixture
def file_api():
    service = SimpleNamespace(
        find_file=AsyncMock(
            return_value=FileContentBO(name="报告.txt", type="text/plain", content=b"content")
        )
    )
    api = FileApiImpl()
    api.file_service = service
    return api, service


async def test_file_api_get_content_preserves_bytes_and_missing_error(file_api):
    api, service = file_api
    assert await api.get_file_content(7, "docs/report.txt") == b"content"
    service.find_file.assert_awaited_once_with(7, "docs/report.txt", public_only=False)

    service.find_file.return_value = None
    with pytest.raises(FileNotFoundError, match="docs/report.txt"):
        await api.get_file_content(7, "docs/report.txt")


async def test_file_api_get_content_rejects_empty_path(file_api):
    api, service = file_api
    with pytest.raises(ValueError, match="文件路径不能为空"):
        await api.get_file_content(7, "")
    service.find_file.assert_not_awaited()


@pytest.mark.parametrize("route", ["7/get", "private/7"])
async def test_file_api_url_reads_decoded_path_and_returns_none_for_missing(file_api, route):
    api, service = file_api
    url = (
        f"https://files.example.test/admin-api/infra/file/{route}/docs/report%20one.txt?download=1"
    )
    assert await api.get_content_by_url(url) == b"content"
    service.find_file.assert_awaited_once_with(7, "docs/report one.txt", public_only=False)

    service.find_file.return_value = None
    assert await api.get_content_by_url(url) is None


async def test_file_api_url_ignores_unrelated_urls(file_api):
    api, service = file_api
    assert await api.get_content_by_url("https://files.example.test/report.txt") is None
    service.find_file.assert_not_awaited()


async def test_file_api_url_does_not_hide_storage_failures(file_api):
    api, service = file_api
    service.find_file.side_effect = PermissionError("access denied")
    with pytest.raises(PermissionError, match="access denied"):
        await api.get_content_by_url("/admin-api/infra/file/7/get/report.txt")
