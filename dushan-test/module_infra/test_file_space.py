import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import boto3
import pytest
from botocore.config import Config
from httpx import ASGITransport, AsyncClient

from module_infra.framework.file.core.client.s3.s3_file_client_config import S3FileClientConfig
from module_infra.framework.file.core.client.s3.s3_service_factory import S3ServiceFactory


def test_file_space_menu_is_initialized(infra_database):
    with infra_database[2].cursor() as cursor:
        cursor.execute("SELECT name,component,path FROM system_menu WHERE id=10000000100211")
        assert cursor.fetchone() == ("文件空间", "infra/file/index", "list")


def test_s3_path_style_setting_is_used_for_signed_urls():
    config = S3FileClientConfig(
        endpoint="http://minio.internal:9000",
        bucket="file-space",
        access_key="fixture-key",
        access_secret="fixture-secret",
        enable_path_style_access=True,
    )
    client = S3ServiceFactory.create_client(config)
    try:
        url = client.generate_presigned_url(
            "get_object", Params={"Bucket": config.bucket, "Key": "docs/readme.txt"}
        )
        assert urlsplit(url).hostname == "minio.internal"
        assert urlsplit(url).path == "/file-space/docs/readme.txt"
    finally:
        client.close()


@pytest.mark.asyncio(loop_scope="module")
async def test_selected_storage_and_directory_upload_roundtrip(admin_client, infra_app):
    created = (
        await admin_client.post(
            "/admin-api/infra/file/config/create",
            json={
                "name": "File space fixture",
                "storage": 1,
                "config": {"domain": "http://testserver"},
            },
        )
    ).json()
    assert created["code"] == 0, created
    config_id = created["data"]
    for prefix in ("docs_1/", "docsX1/"):
        made = (
            await admin_client.post(
                "/admin-api/infra/file/create-directory",
                json={"configId": config_id, "directoryPath": prefix},
            )
        ).json()
        assert made["code"] == 0, made
        response = (
            await admin_client.post(
                "/admin-api/infra/file/upload",
                data={"configId": config_id, "directory": prefix},
                files={"file": ("readme.txt", b"file-space-content", "text/plain")},
            )
        ).json()
        assert response["code"] == 0, response
    listed = (
        await admin_client.get(
            "/admin-api/infra/file/list-objects",
            params={"configId": config_id, "prefix": "docs_1/"},
        )
    ).json()
    assert listed["code"] == 0, listed
    assert len(listed["data"]["objects"]) == 1
    item = listed["data"]["objects"][0]
    assert item["name"] == "readme.txt"
    assert item["key"].startswith("docs_1/")
    searched = (
        await admin_client.get(
            "/admin-api/infra/file/search",
            params={
                "configId": config_id,
                "prefix": "docs_1/",
                "keyword": "readme",
                "page": 1,
                "pageSize": 20,
            },
        )
    ).json()
    assert searched["code"] == 0, searched
    assert searched["data"]["total"] == 1
    assert searched["data"]["items"][0]["path"] == item["key"]
    async with AsyncClient(
        transport=ASGITransport(app=infra_app), base_url="http://testserver"
    ) as public:
        response = await public.get(urlsplit(item["url"]).path)
        assert response.content == b"file-space-content"
    renamed = (
        await admin_client.post(
            "/admin-api/infra/file/rename",
            json={"configId": config_id, "oldKey": item["key"], "newName": "renamed.txt"},
        )
    ).json()
    assert renamed["code"] == 0, renamed
    deleted = (
        await admin_client.delete(
            "/admin-api/infra/file/delete-by-key",
            params={"configId": config_id, "key": "docs_1/renamed.txt"},
        )
    ).json()
    assert deleted["code"] == 0, deleted
    refreshed = (
        await admin_client.get(
            "/admin-api/infra/file/list-objects",
            params={"configId": config_id, "prefix": "docs_1/"},
        )
    ).json()
    assert refreshed["data"]["objects"] == []


@pytest.mark.asyncio(loop_scope="module")
async def test_private_minio_bucket_switch_and_signed_read(admin_client):
    resource_path = os.environ.get("DUSHAN_FILE_TEST_MINIO")
    if resource_path is None:
        pytest.skip("需要独立 MinIO 资源清单")
    resource = json.loads(Path(resource_path).read_text(encoding="utf-8"))
    assert (
        Path(resource_path).resolve().is_relative_to(Path(__file__).resolve().parents[2] / "Temp")
    )
    assert resource["container"] == "dushan-file-space-minio"
    endpoint = f"http://127.0.0.1:{resource['port']}"
    storage = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id="file-space-fixture",
        aws_secret_access_key="fixture-only-secret",
        region_name="us-east-1",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    try:
        for bucket in ("file-space-a", "file-space-b"):
            storage.create_bucket(Bucket=bucket)
        created = (
            await admin_client.post(
                "/admin-api/infra/file/config/create",
                json={
                    "name": "Private MinIO",
                    "storage": 20,
                    "config": {
                        "endpoint": endpoint,
                        "bucket": "file-space-a",
                        "accessKey": "file-space-fixture",
                        "accessSecret": "fixture-only-secret",
                        "enablePathStyleAccess": True,
                    },
                },
            )
        ).json()
        assert created["code"] == 0, created
        identifier = created["data"]
        config = (
            await admin_client.get("/admin-api/infra/file/config/get", params={"id": identifier})
        ).json()["data"]
        assert "accessKey" not in config["config"] and "accessSecret" not in config["config"]
        config["config"]["bucket"] = "file-space-b"
        updated = (
            await admin_client.put(
                "/admin-api/infra/file/config/update",
                json={
                    "id": identifier,
                    "name": config["name"],
                    "storage": 20,
                    "config": config["config"],
                },
            )
        ).json()
        assert updated["code"] == 0, updated
        uploaded = (
            await admin_client.post(
                "/admin-api/infra/file/upload",
                data={"configId": identifier, "directory": "docs"},
                files={"file": ("private.txt", b"private-file-content", "text/plain")},
            )
        ).json()
        assert uploaded["code"] == 0, uploaded
        assert not storage.list_objects_v2(Bucket="file-space-a").get("Contents")
        listing = (
            await admin_client.get(
                "/admin-api/infra/file/list-objects",
                params={"configId": identifier, "prefix": "docs/"},
            )
        ).json()
        assert listing["code"] == 0, listing
        item = listing["data"]["objects"][0]
        assert item["name"] == "private.txt"
        async with AsyncClient() as public:
            assert (await public.get(uploaded["data"])).status_code == 403
            signed = await public.get(item["url"])
            assert signed.status_code == 200 and signed.content == b"private-file-content"
        assert "X-Amz-Signature=" in item["url"]
        found = (
            await admin_client.get(
                "/admin-api/infra/file/search",
                params={"configId": identifier, "keyword": "private", "page": 1, "pageSize": 20},
            )
        ).json()
        assert found["code"] == 0, found
        assert found["data"]["items"][0]["path"] == item["key"]
        assert "X-Amz-Signature=" in found["data"]["items"][0]["url"]
        assert (
            await admin_client.delete(
                "/admin-api/infra/file/delete-by-key",
                params={"configId": identifier, "key": item["key"]},
            )
        ).json()["code"] == 0
    finally:
        for bucket in ("file-space-a", "file-space-b"):
            for item in storage.list_objects_v2(Bucket=bucket).get("Contents", []):
                storage.delete_object(Bucket=bucket, Key=item["Key"])
            storage.delete_bucket(Bucket=bucket)
        storage.close()
