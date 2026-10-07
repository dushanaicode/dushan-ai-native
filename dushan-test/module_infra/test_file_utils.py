import hashlib
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from module_infra.definitions.enums.file.file_visibility_enum import FileVisibilityEnum
from module_infra.framework.file.core.client.abstract_file_client import AbstractFileClient
from module_infra.service.file.file_service_impl import FileServiceImpl
from module_infra.util.file import file_utils
from module_infra.util.file.file_utils import FileUtils

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "name, mime_type, expected",
    [
        (None, "image/jpeg", hashlib.sha256(b"content").hexdigest() + ".jpg"),
        ("", None, hashlib.sha256(b"content").hexdigest()),
        ("report", "application/msword", "report.doc"),
        ("picture", "IMAGE/JPEG", "picture.jpg"),
        ("page", "text/html", "page.html"),
        ("report.txt", "application/pdf", "report.txt"),
        ("unknown", "application/x-unknown-file-type", "unknown"),
        ("unknown", None, "unknown"),
    ],
)
def test_resolve_file_name_preserves_upload_naming_rules(name, mime_type, expected):
    assert FileUtils.resolve_file_name(name, b"content", mime_type) == expected


@pytest.mark.parametrize(
    "name, directory, suffix, expected",
    [
        ("readme.txt", None, True, "readme_123456.txt"),
        ("archive.tar.gz", "docs///", True, "docs/archive.tar_123456.gz"),
        ("plain", "docs", True, "docs/plain_123456"),
        ("readme.txt", "docs/", False, "docs/readme.txt"),
        ("readme.txt", None, False, "readme.txt"),
    ],
)
def test_generate_storage_path_preserves_directory_and_suffix(
    monkeypatch, name, directory, suffix, expected
):
    monkeypatch.setattr(file_utils.time, "time", lambda: 123.456)
    assert FileUtils.generate_storage_path(name, directory, suffix) == expected


@pytest.mark.parametrize(
    "timestamp_suffix, explicit_path, expected_path",
    [
        (True, None, "docs/report_123456.doc"),
        (False, None, "docs/report.doc"),
        (True, "selected/report.doc", "selected/report.doc"),
    ],
)
async def test_create_file_keeps_generated_name_path_and_upload_metadata(
    monkeypatch, timestamp_suffix, explicit_path, expected_path
):
    monkeypatch.setattr(file_utils.time, "time", lambda: 123.456)
    storage = SimpleNamespace(
        get_id=lambda: 7,
        upload=AsyncMock(return_value="https://files.example.test/report.doc"),
    )

    async def insert(row):
        row.id = 19

    mapper = SimpleNamespace(insert=AsyncMock(side_effect=insert))
    service = FileServiceImpl()
    service.file_mapper = mapper
    service.file_config_service = SimpleNamespace(
        get_master_file_client=AsyncMock(return_value=storage)
    )
    service.PATH_SUFFIX_TIMESTAMP_ENABLE = timestamp_suffix

    result = await service.create_file_full(
        b"content",
        FileVisibilityEnum.PUBLIC,
        name="report",
        directory="docs/",
        type_hint="application/msword",
        path=explicit_path,
    )

    assert result == (19, storage.upload.return_value, 7, expected_path)
    storage.upload.assert_awaited_once_with(
        path=expected_path, content=b"content", file_type="application/msword"
    )
    row = mapper.insert.await_args.args[0]
    assert row.name == "report.doc"
    assert row.original_name == "report"
    assert row.path == expected_path.rsplit("/", 1)[1]
    assert row.storage_path == expected_path
    assert row.size == 7
    assert row.type == "application/msword"


@pytest.mark.parametrize("type_hint", [None, "", "application/x-custom"])
async def test_create_file_uses_the_same_resolved_mime_for_storage_and_record(type_hint):
    """未知内容由类型工具兜底，显式类型保持原值。"""
    storage = SimpleNamespace(get_id=lambda: 7, upload=AsyncMock(return_value="/file"))
    service = FileServiceImpl()
    service.file_mapper = SimpleNamespace(insert=AsyncMock())
    service.file_config_service = SimpleNamespace(
        get_master_file_client=AsyncMock(return_value=storage)
    )

    await service.create_file_full(
        b"unknown content", FileVisibilityEnum.PUBLIC, name="opaque", type_hint=type_hint
    )

    expected = "application/x-custom" if type_hint else "application/octet-stream"
    assert storage.upload.await_args.kwargs["file_type"] == expected
    assert service.file_mapper.insert.await_args.args[0].type == expected


@pytest.mark.parametrize(
    "old_key, new_name, expected",
    [
        ("old.txt", "new.txt", "new.txt"),
        ("docs/old.txt", "new.txt", "docs/new.txt"),
        ("old/", "new", "new/"),
        ("docs/old/", "new", "docs/new/"),
        ("docs/old///", "new", "docs/new/"),
        ("docs/old.txt", "sub/new.txt", "docs/sub/new.txt"),
        ("docs/old/", "sub/new", "docs/sub/new/"),
        ("docs/old.txt", "/new.txt", "docs//new.txt"),
        ("docs/old.txt", "../new.txt", "docs/../new.txt"),
    ],
)
def test_rename_storage_key_preserves_path_semantics(old_key, new_name, expected):
    """保留相对名称、目录尾斜杠与待存储边界校验的原始路径。"""
    assert FileUtils.rename_storage_key(old_key, new_name) == expected


@pytest.mark.parametrize("old_key", ["old.txt", "docs/old.txt", "old/", "docs/old/"])
async def test_rename_updates_storage_and_private_metadata_consistently(old_key):
    """顶层和嵌套对象重命名后，记录路径与私有访问地址一致。"""
    directory = old_key.endswith("/")
    old_path = old_key + "child.txt" if directory else old_key
    row = SimpleNamespace(
        config_id=7,
        name="child.txt" if directory else "old.txt",
        storage_path=old_path,
        visibility=FileVisibilityEnum.PRIVATE.code,
    )
    storage = SimpleNamespace(rename=AsyncMock())
    mapper = SimpleNamespace(
        select_by_storage_path=AsyncMock(return_value=row),
        select_by_config_and_prefix=AsyncMock(return_value=[row]),
        update_by_id=AsyncMock(),
    )
    service = FileServiceImpl()
    service.file_mapper = mapper
    service.file_config_service = SimpleNamespace(get_file_client=AsyncMock(return_value=storage))
    new_name = "archive" if directory else "new.txt"
    parent = "docs/" if old_key.startswith("docs/") else ""
    new_key = parent + new_name + ("/" if directory else "")
    expected_path = new_key + "child.txt" if directory else new_key

    await service.rename_object(7, old_key, new_name)

    storage.rename.assert_awaited_once_with(old_key, new_key)
    mapper.update_by_id.assert_awaited_once_with(row)
    assert row.storage_path == expected_path
    assert row.path == ("child.txt" if directory else "new.txt")
    assert row.name == ("child.txt" if directory else "new.txt")
    assert row.url == f"/admin-api/infra/file/private/7/{expected_path}"


@pytest.mark.parametrize("new_name", ["../escape.txt", "bad\\name.txt", "C:drive.txt", "bad\x00"])
async def test_rename_keeps_storage_key_validation(new_name):
    """非法重命名仍由现有存储键边界拒绝，失败时不改记录。"""

    async def rename(old_key, new_key):
        """复用生产存储边界验证两个键。"""
        AbstractFileClient.key(old_key)
        AbstractFileClient.key(new_key)

    storage = SimpleNamespace(rename=AsyncMock(side_effect=rename))
    mapper = SimpleNamespace(
        select_by_storage_path=AsyncMock(return_value=None), update_by_id=AsyncMock()
    )
    service = FileServiceImpl()
    service.file_mapper = mapper
    service.file_config_service = SimpleNamespace(get_file_client=AsyncMock(return_value=storage))

    with pytest.raises(ValueError, match="文件路径必须是存储根目录内的相对路径"):
        await service.rename_object(7, "docs/old.txt", new_name)

    mapper.update_by_id.assert_not_awaited()
