import base64
import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, UploadFile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.datastructures import Headers

from fixtures.config_factory import ConfigFactory
from fixtures.public_web_app import create_public_app
from framework.common.exception import ServiceException
from framework.common.page import PageResult
from framework.starter_database.query.row_access_policy import RowAccessPolicy
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_i18n.config.i18n_options import I18nOptions
from framework.starter_i18n.core.accept_language_parser import AcceptLanguageParser
from framework.starter_i18n.core.i18n_catalog import I18nCatalog
from framework.starter_i18n.core.i18n_translator import I18nTranslator
from framework.starter_security.public import SecurityRealm
from framework.starter_tenant.context.tenant_context import TenantContext
from framework.starter_tenant.core.tenant_model_registry import TenantModelRegistry
from framework.starter_tenant.core.tenant_session_policy import TenantSessionPolicy
from framework.starter_web.config.response_settings import ResponseSettings
from framework.starter_web.public import FileResult, RoutePolicy
from module_infra.controller.admin.file.file_controller import FileController, file_controller
from module_infra.controller.admin.file.vo.file.file_search_req_vo import FileSearchReqVO
from module_infra.dal.dataobject.file.file_config_do import FileConfigDO
from module_infra.dal.dataobject.file.file_do import FileDO
from module_infra.dal.mapper.file.file_mapper import FileMapper
from module_infra.definitions.constants.error_code_constants import ErrorCodeConstants
from module_infra.definitions.enums.file.file_upload_usage_enum import FileUploadUsageEnum
from module_infra.definitions.enums.file.file_visibility_enum import FileVisibilityEnum
from module_infra.service.file.file_service_impl import FileServiceImpl

pytestmark = pytest.mark.unit

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
)


@pytest.fixture
def file_service():
    storage = SimpleNamespace(
        get_id=lambda: 7,
        upload=AsyncMock(return_value="https://bucket.example.test/direct-object"),
        get_content=AsyncMock(return_value=PNG),
        presign_get_url=AsyncMock(return_value="https://bucket.example.test/signed-object"),
        list_objects=AsyncMock(),
        rename=AsyncMock(),
    )

    async def insert(row):
        row.id = 19
        row.create_time = datetime.now(UTC)

    mapper = SimpleNamespace(
        insert=AsyncMock(side_effect=insert),
        select_by_storage_path=AsyncMock(),
        select_by_config_and_prefix=AsyncMock(),
        select_by_url=AsyncMock(),
        search_files=AsyncMock(),
        update_by_id=AsyncMock(),
    )
    configs = SimpleNamespace(
        get_master_file_client=AsyncMock(return_value=storage),
        get_file_client=AsyncMock(return_value=storage),
    )
    service = FileServiceImpl()
    service.file_mapper, service.file_config_service = mapper, configs
    return service, storage, mapper, configs


@pytest.fixture
def files():
    return FileResult(ResponseSettings.model_validate(ConfigFactory.values()["response"]))


@pytest.mark.parametrize(
    "usage,visibility,limit,content",
    [
        (FileUploadUsageEnum.AVATAR, FileVisibilityEnum.PUBLIC, 2, PNG),
        (FileUploadUsageEnum.LOGO, FileVisibilityEnum.PUBLIC, 2, PNG),
        (FileUploadUsageEnum.FORM_IMAGE, FileVisibilityEnum.PRIVATE, 10, PNG),
        (FileUploadUsageEnum.FORM_FILE, FileVisibilityEnum.PRIVATE, 20, b"untyped content"),
    ],
)
async def test_business_upload_uses_usage_policy_and_master_storage(
    file_service, usage, visibility, limit, content
):
    service, storage, mapper, configs = file_service
    url = await service.create_business_file(content=content, name="sample.png", usage=usage)
    row = mapper.insert.await_args.args[0]
    assert row.visibility == visibility.code
    assert row.storage_path.startswith(f"usage/{usage.code}/")
    assert row.type == ("image/png" if content == PNG else "application/octet-stream")
    assert row.size == len(content)
    assert usage.max_size == limit * 1024 * 1024
    assert row.url == url
    configs.get_master_file_client.assert_awaited_once_with()
    configs.get_file_client.assert_not_awaited()
    if visibility is FileVisibilityEnum.PRIVATE:
        assert url == f"/admin-api/infra/file/private/7/{row.storage_path}"
    else:
        assert url == storage.upload.return_value


@pytest.mark.parametrize("usage", list(FileUploadUsageEnum))
async def test_business_upload_size_boundary_and_explicit_error(file_service, usage):
    service, storage, mapper, _ = file_service
    content = PNG + bytes(usage.max_size - len(PNG))
    await service.create_business_file(content=content, name="limit.png", usage=usage)
    assert mapper.insert.await_args.args[0].size == usage.max_size
    storage.upload.reset_mock()
    mapper.insert.reset_mock()
    with pytest.raises(ServiceException) as caught:
        await service.create_business_file(content=content + b"x", name="limit.png", usage=usage)
    assert caught.value.error_code is ErrorCodeConstants.FILE_UPLOAD_SIZE_EXCEEDED
    storage.upload.assert_not_awaited()
    mapper.insert.assert_not_awaited()


@pytest.mark.parametrize(
    "usage", [FileUploadUsageEnum.AVATAR, FileUploadUsageEnum.LOGO, FileUploadUsageEnum.FORM_IMAGE]
)
async def test_business_upload_rejects_forged_filename_and_client_mime(file_service, usage):
    service, storage, mapper, _ = file_service
    upload = UploadFile(
        BytesIO(b"<html>not an image</html>"),
        filename="avatar.png",
        headers=Headers({"content-type": "image/png"}),
    )
    with pytest.raises(ServiceException) as caught:
        await FileController.business_upload_file(file=upload, usage=usage, file_service=service)
    assert caught.value.error_code is ErrorCodeConstants.FILE_UPLOAD_TYPE_NOT_ALLOWED
    storage.upload.assert_not_awaited()
    mapper.insert.assert_not_awaited()


@pytest.mark.parametrize(
    "content,mime",
    [
        (PNG, "image/png"),
        (b"\xff\xd8\xff\xe0" + bytes(16), "image/jpeg"),
        (b"GIF89a" + bytes(16), "image/gif"),
        (b"RIFF" + bytes(4) + b"WEBPVP8 " + bytes(16), "image/webp"),
    ],
)
async def test_avatar_allows_only_detected_raster_types(file_service, content, mime):
    service, _, mapper, _ = file_service
    await service.create_business_file(
        content=content, name="wrong.txt", usage=FileUploadUsageEnum.AVATAR
    )
    assert mapper.insert.await_args.args[0].type == mime


def test_upload_and_read_route_policies_and_removed_endpoints():
    routes = {
        (method, route.path): route for route in file_controller.routes for method in route.methods
    }
    for method, path, permissions in [
        ("POST", "/file/upload", ("infra:file:upload",)),
        ("POST", "/file/business-upload", ()),
        ("GET", "/file/private/{config_id}/{path:path}", ()),
    ]:
        policy = getattr(routes[(method, path)].endpoint, RoutePolicy.ATTRIBUTE)
        assert policy.permissions == permissions
        assert policy.requires_identity and policy.tenant_required
        assert policy.realm is SecurityRealm.TENANT
    public = getattr(
        routes[("GET", "/file/{config_id}/get/{path:path}")].endpoint, RoutePolicy.ATTRIBUTE
    )
    assert public == RoutePolicy.public()
    assert ("GET", "/file/presigned-url") not in routes
    assert ("POST", "/file/create") not in routes
    app = FastAPI()
    app.include_router(file_controller)
    schemas = app.openapi()["components"]["schemas"]
    upload_schema = next(
        value for name, value in schemas.items() if name.startswith("Body_upload_file_")
    )
    business_schema = next(
        value for name, value in schemas.items() if name.startswith("Body_business_upload_file_")
    )
    assert set(upload_schema["required"]) == {"file", "visibility"}
    assert set(business_schema["properties"]) == {"file", "usage"}
    assert set(business_schema["required"]) == {"file", "usage"}


@pytest.mark.parametrize("visibility", [None, FileVisibilityEnum.PRIVATE])
async def test_anonymous_missing_and_private_have_identical_error(file_service, files, visibility):
    service, storage, mapper, _ = file_service
    mapper.select_by_storage_path.return_value = (
        None if visibility is None else SimpleNamespace(visibility=visibility.code)
    )
    scopes = []

    @asynccontextmanager
    async def scope(name, tenant_id):
        scopes.append((name, tenant_id))
        yield

    with pytest.raises(ServiceException) as caught:
        await FileController.get_file_content(
            config_id=7,
            path="secret.png",
            file_service=service,
            workloads=SimpleNamespace(scope=scope),
            tenant=SimpleNamespace(default_tenant_id="1"),
            files=files,
        )
    assert caught.value.error_code is ErrorCodeConstants.FILE_NOT_EXISTS
    assert caught.value.__cause__ is None
    assert scopes == [("infra.file.read", "1")]
    mapper.select_by_storage_path.assert_awaited_once_with(7, "secret.png")
    storage.get_content.assert_not_awaited()


@pytest.mark.parametrize(
    "filename,media_type,disposition",
    [("image.png", "image/png", "inline"), ("page.html", "text/html", "attachment")],
)
async def test_anonymous_public_content_preserves_cache_csp_and_attachment(
    file_service, files, filename, media_type, disposition
):
    service, storage, mapper, _ = file_service
    mapper.select_by_storage_path.return_value = SimpleNamespace(
        visibility=FileVisibilityEnum.PUBLIC.code, name=filename, type=media_type
    )

    @asynccontextmanager
    async def scope(name, tenant_id):
        yield

    arguments = dict(
        config_id=7,
        path=filename,
        file_service=service,
        workloads=SimpleNamespace(scope=scope),
        tenant=SimpleNamespace(default_tenant_id="1"),
        files=files,
    )
    response = await FileController.get_file_content(**arguments)
    assert response.status_code == 200
    assert b"".join([part async for part in response.body_iterator]) == PNG
    assert response.headers["content-security-policy"] == "sandbox; default-src 'none'"
    assert response.headers["content-disposition"].startswith(disposition + ";")
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert response.headers["x-content-type-options"] == "nosniff"
    storage.get_content.assert_awaited_with(filename)


@pytest.mark.parametrize("public", [True, False])
@pytest.mark.parametrize(
    "filename,media_type,disposition",
    [("image.png", "text/html", "attachment"), ("page.html", "image/png", "inline")],
)
def test_file_controller_http_cache_and_localized_error(
    config_dir, file_service, files, public, filename, media_type, disposition
):
    """读取使用记录中的名称和类型，公开缓存支持 304，缺失文件沿用双语业务错误。"""
    app = create_public_app(base_dir=config_dir(), environ={})
    service, storage, mapper, _ = file_service
    row = SimpleNamespace(name=filename, type=media_type, visibility=FileVisibilityEnum.PUBLIC.code)
    mapper.select_by_storage_path.return_value = row

    @asynccontextmanager
    async def workload_scope(name, tenant_id):
        """隔离工作负载授权依赖，不连接外部服务。"""
        yield

    @app.get("/file-content")
    async def read_file():
        """通过真实 Controller 方法验证响应协议。"""
        arguments = dict(config_id=7, path="stored.bin", file_service=service, files=files)
        if public:
            return await FileController.get_file_content(
                **arguments,
                workloads=SimpleNamespace(scope=workload_scope),
                tenant=SimpleNamespace(default_tenant_id="1"),
            )
        return await FileController.get_private_file_content(**arguments)

    resource_root = (
        Path(__file__).resolve().parents[2] / "dushan-admin-backend/module_infra/definitions/i18n"
    )
    messages = {
        locale: json.loads((resource_root / f"{locale}.json").read_text(encoding="utf-8"))["infra"][
            "file"
        ]["not_exists"]
        for locale in ("zh-CN", "en-US")
    }
    options = ConfigFactory.build(I18nOptions, "i18n")
    translator = I18nTranslator(
        I18nCatalog(
            {
                locale: {"infra": {ErrorCodeConstants.FILE_NOT_EXISTS.message_key: message}}
                for locale, message in messages.items()
            },
            options,
        ),
        AcceptLanguageParser(options),
    )
    with TestClient(app) as client:
        app.state.bootstrap.exception_handler.translator = translator
        response = client.get("/file-content")
        assert response.status_code == 200 and response.content == PNG
        assert response.headers["cache-control"] == (
            "public, max-age=31536000, immutable" if public else "no-store"
        )
        assert response.headers["content-disposition"].startswith(disposition + ";")
        assert response.headers["content-disposition"].endswith(filename)
        assert response.headers["content-type"].split(";")[0] == media_type
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["content-security-policy"] == "sandbox; default-src 'none'"
        mapper.select_by_storage_path.assert_awaited_with(7, "stored.bin")
        storage.get_content.assert_awaited_with("stored.bin")
        if public:
            cached = client.get(
                "/file-content", headers={"If-None-Match": response.headers["etag"]}
            )
            assert cached.status_code == 304 and cached.content == b""
            assert "content-length" not in cached.headers
            for header in (
                "cache-control",
                "content-security-policy",
                "x-content-type-options",
                "etag",
            ):
                assert cached.headers[header] == response.headers[header]
        else:
            assert "etag" not in response.headers
            conditional = client.get("/file-content", headers={"If-None-Match": "*"})
            assert conditional.status_code == 200 and conditional.content == PNG
            assert "etag" not in conditional.headers
        missing_cases = ["record", "storage"]
        if public:
            missing_cases.append("private")
        for case in missing_cases:
            mapper.select_by_storage_path.return_value = None if case == "record" else row
            row.visibility = (
                FileVisibilityEnum.PRIVATE.code
                if case == "private"
                else FileVisibilityEnum.PUBLIC.code
            )
            storage.get_content.side_effect = (
                FileNotFoundError("stored.bin") if case == "storage" else None
            )
            for locale, message in messages.items():
                missing = client.get("/file-content", headers={"Accept-Language": locale})
                assert missing.status_code == 200
                assert missing.json() == {
                    "code": 1001003001,
                    "message": message,
                    "data": None,
                    "error": None,
                }
                assert missing.headers["cache-control"] == "no-store"
                assert missing.headers["vary"] == "Accept-Language"


@pytest.mark.parametrize("visibility", list(FileVisibilityEnum))
async def test_private_read_uses_current_tenant_and_rejects_other_tenant(
    file_service, files, monkeypatch, visibility
):
    service, storage, _, _ = file_service
    application = object()
    execution = SimpleNamespace(application=application, active=True)
    monkeypatch.setattr(ApplicationContext, "current_execution", lambda: execution)
    tenant = TenantContext(application)
    registry = TenantModelRegistry([FileConfigDO, FileDO])
    policy = RowAccessPolicy([TenantSessionPolicy(registry, tenant)])
    engine = create_engine("sqlite://")
    FileConfigDO.__table__.create(engine)
    FileDO.__table__.create(engine)
    audit = dict(create_time=datetime.now(UTC), update_time=datetime.now(UTC))
    with Session(engine) as session:
        for identifier, tenant_id, config_id in [(1, "42", 7), (2, "43", 8)]:
            session.add(
                FileConfigDO(
                    id=config_id, tenant_id=tenant_id, name="fixture", storage=1, config={}, **audit
                )
            )
            session.add(
                FileDO(
                    id=identifier,
                    tenant_id=tenant_id,
                    config_id=config_id,
                    name="secret.html",
                    original_name="secret.html",
                    path="secret.html",
                    storage_path="secret.html",
                    url=f"/admin-api/infra/file/private/{config_id}/secret.html",
                    visibility=visibility.code,
                    type="text/html",
                    size=len(PNG),
                    **audit,
                )
            )
        session.commit()
    mapper = FileMapper()
    service.file_mapper = mapper
    arguments = dict(config_id=7, path="secret.html", file_service=service, files=files)
    try:
        with tenant._bind("42", None, seconds=30), Session(engine) as session:
            policy.bind(session)
            mapper.read = AsyncMock(side_effect=session.execute)
            response = await FileController.get_private_file_content(**arguments)
            assert tenant.get_required_tenant_id() == "42"
            assert b"".join([part async for part in response.body_iterator]) == PNG
            assert response.headers["content-disposition"].startswith("attachment;")
            assert response.headers["content-security-policy"] == "sandbox; default-src 'none'"
            assert response.headers["cache-control"] == "no-store"
        storage.get_content.reset_mock()
        with tenant._bind("43", None, seconds=30), Session(engine) as session:
            policy.bind(session)
            mapper.read = AsyncMock(side_effect=session.execute)
            with pytest.raises(ServiceException) as caught:
                await FileController.get_private_file_content(**arguments)
            assert caught.value.error_code is ErrorCodeConstants.FILE_NOT_EXISTS
            assert caught.value.__cause__ is None
            storage.get_content.assert_not_awaited()
            other = await FileController.get_private_file_content(**{**arguments, "config_id": 8})
            assert other.status_code == 200
            assert b"".join([part async for part in other.body_iterator]) == PNG
    finally:
        engine.dispose()


async def test_private_urls_never_become_storage_signed_urls(file_service):
    service, storage, mapper, _ = file_service
    url = await service.create_file(
        PNG, visibility=FileVisibilityEnum.PRIVATE, name="a b.png", path="docs/a b.png", config_id=7
    )
    assert url == "/admin-api/infra/file/private/7/docs/a%20b.png"
    row = mapper.insert.await_args.args[0]
    mapper.select_by_config_and_prefix.return_value = [row]
    mapper.select_by_url.return_value = row
    mapper.search_files.return_value = PageResult(items=[row], total=1)
    storage.list_objects.return_value = {
        "directories": [],
        "files": [{"key": row.storage_path, "name": row.name, "size": len(PNG)}],
        "isTruncated": False,
        "nextMarker": "",
    }
    listed = await service.list_objects(7, "docs/", "/")
    assert listed.objects[0].url == url
    found = await service.search_files(
        FileSearchReqVO(config_id="7", keyword="a", page=1, page_size=20)
    )
    assert found.items[0].url == url
    assert await service.presign_get_url(url) == url
    storage.presign_get_url.assert_not_awaited()
    mapper.select_by_storage_path.return_value = row
    await service.rename_object(7, "docs/a b.png", "c d.png")
    assert row.url == "/admin-api/infra/file/private/7/docs/c%20d.png"


def test_visibility_is_required_without_orm_default():
    column = FileDO.__table__.c.visibility
    assert column.type.length == 16
    assert column.nullable is False
    assert column.default is None and column.server_default is None


@pytest.mark.parametrize("usage", [FileUploadUsageEnum.LOGO, FileUploadUsageEnum.FORM_IMAGE])
async def test_other_image_formats_allowed_for_logo_and_form_image(file_service, usage):
    service, _, mapper, _ = file_service
    content = b"BM" + bytes(54)
    await service.create_business_file(content=content, name="image.bmp", usage=usage)
    assert mapper.insert.await_args.args[0].type == "image/bmp"


async def test_avatar_rejects_detected_image_outside_allowed_formats(file_service):
    service, storage, _, _ = file_service
    with pytest.raises(ServiceException) as caught:
        await service.create_business_file(
            content=b"BM" + bytes(54), name="image.png", usage=FileUploadUsageEnum.AVATAR
        )
    assert caught.value.error_code is ErrorCodeConstants.FILE_UPLOAD_TYPE_NOT_ALLOWED
    storage.upload.assert_not_awaited()


async def test_unregistered_storage_object_does_not_gain_a_signed_url(file_service):
    service, storage, mapper, _ = file_service
    mapper.select_by_config_and_prefix.return_value = []
    storage.list_objects.return_value = {
        "directories": [],
        "files": [{"key": "orphan.txt", "name": "orphan.txt", "size": 1}],
        "isTruncated": False,
        "nextMarker": "",
    }
    listed = await service.list_objects(7, "", "/")
    assert listed.objects[0].url is None
    storage.presign_get_url.assert_not_awaited()
