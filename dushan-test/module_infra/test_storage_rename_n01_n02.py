import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import boto3
import pytest
from botocore.config import Config
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from framework.starter_security.public import SecurityRealm, SecurityService
from framework.starter_web.public import RoutePolicy
from module_infra.framework.file.core.client.s3.s3_file_client import S3FileClient
from module_infra.framework.file.core.client.s3.s3_file_client_config import S3FileClientConfig
from module_infra.service.file.file_service import FileService


@asynccontextmanager
async def authorized(app, client):
    application = app.state.application_context
    with application.execution(), app.state.database.scope():
        async with application.container.get(SecurityService).authorized(
            client.headers["Authorization"].removeprefix("Bearer "),
            RoutePolicy(tenant_required=True, realm=SecurityRealm.TENANT),
        ):
            yield application.container


async def config(client, storage=1, values=None):
    result = (
        await client.post(
            "/admin-api/infra/file/config/create",
            json={
                "name": uuid4().hex,
                "storage": storage,
                "config": values or {"domain": "http://testserver"},
            },
        )
    ).json()
    assert result["code"] == 0, result
    return int(result["data"])


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.parametrize(
    "prefix, neighbor", [("team_/", "teamX/"), ("team%/", "teamOther/"), ("team/", "teamX/")]
)
async def test_db_directory_rename_is_a_literal_prefix(
    prefix, neighbor, admin_client, infra_app, infra_database
):
    first, other = await config(admin_client), await config(admin_client)
    async with authorized(infra_app, admin_client) as container:
        service = container.get(FileService)
        for identifier, key in (
            (first, prefix + "a.txt"),
            (first, neighbor + "b.txt"),
            (other, prefix + "c.txt"),
            (first, prefix + "deleted.txt"),
        ):
            await service.create_file(b"fixture", name=key, path=key, config_id=identifier)
        await service.delete_by_key(first, prefix + "deleted.txt")
        await service.rename_object(first, prefix, "archive")
    with infra_database[2].cursor() as cursor:
        for table, column in (("infra_file", "storage_path"), ("infra_file_content", "path")):
            cursor.execute(
                f"SELECT config_id,{column} FROM {table} WHERE config_id IN (%s,%s) AND deleted=0",
                (first, other),
            )
            assert set(cursor.fetchall()) == {
                (first, "archive/a.txt"),
                (first, neighbor + "b.txt"),
                (other, prefix + "c.txt"),
            }
            cursor.execute(
                f"SELECT {column} FROM {table} WHERE config_id=%s AND deleted=1", (first,)
            )
            assert cursor.fetchall() == ((prefix + "deleted.txt",),)


@pytest.fixture
def s3_settings():
    resource_manifest = os.environ.get("DUSHAN_N01_N07_S3")
    if resource_manifest is None:
        pytest.skip("?????? MinIO ???? DUSHAN_N01_N07_S3")
    path = Path(resource_manifest)
    assert path.resolve().is_relative_to(Path(__file__).resolve().parents[2] / "Temp")
    settings = json.loads(path.read_text(encoding="utf-8"))
    assert settings["container"] == "dushan-n01-n07-minio"
    return settings


@pytest.fixture
def s3(s3_settings):
    client = boto3.client(
        "s3",
        endpoint_url=s3_settings["endpoint"],
        aws_access_key_id=s3_settings["access_key"],
        aws_secret_access_key=s3_settings["secret_key"],
        region_name="us-east-1",
        config=Config(
            signature_version="s3v4", s3={"addressing_style": "path"}, retries={"max_attempts": 0}
        ),
    )
    bucket = "n01-n07-" + uuid4().hex
    client.create_bucket(Bucket=bucket)
    try:
        yield client, bucket
    finally:
        client.close()


@pytest.mark.asyncio(loop_scope="module")
@pytest.mark.parametrize("directory", [False, True])
async def test_s3_existing_destination_keeps_objects_and_metadata(
    directory, admin_client, infra_app, infra_database, s3, s3_settings
):
    storage, bucket = s3
    identifier = await config(
        admin_client,
        20,
        {
            "endpoint": s3_settings["endpoint"],
            "bucket": bucket,
            "accessKey": s3_settings["access_key"],
            "accessSecret": s3_settings["secret_key"],
            "enablePathStyleAccess": True,
        },
    )
    keys = (
        ["source/a.txt", "source/sub/b.txt", "target/sub/b.txt"]
        if directory
        else ["a.txt", "b.txt"]
    )
    async with authorized(infra_app, admin_client) as container:
        service = container.get(FileService)
        for key in keys:
            await service.create_file(key.encode(), name=key, path=key, config_id=identifier)
        with pytest.raises(FileExistsError):
            await service.rename_object(
                identifier, "source/" if directory else "a.txt", "target" if directory else "b.txt"
            )
    assert {item["Key"] for item in storage.list_objects_v2(Bucket=bucket)["Contents"]} == set(keys)
    for key in keys:
        response = storage.get_object(Bucket=bucket, Key=key)
        with response["Body"] as body:
            assert body.read() == key.encode()
    with infra_database[2].cursor() as cursor:
        cursor.execute(
            "SELECT storage_path FROM infra_file WHERE config_id=%s AND deleted=0", (identifier,)
        )
        assert {row[0] for row in cursor.fetchall()} == set(keys)


@pytest.mark.asyncio
@pytest.mark.parametrize("directory", [False, True])
async def test_s3_rename_success_and_copy_failure(directory, s3, s3_settings, monkeypatch):
    storage, bucket = s3
    client = S3FileClient(
        1,
        S3FileClientConfig(
            endpoint=s3_settings["endpoint"],
            bucket=bucket,
            access_key=s3_settings["access_key"],
            access_secret=s3_settings["secret_key"],
            enable_path_style_access=True,
        ),
    )
    client.sync_client = storage
    keys = ["source/a.txt", "source/sub/b.txt"] if directory else ["source.txt"]
    for key in keys:
        storage.put_object(Bucket=bucket, Key=key, Body=key.encode())
    old, new = ("source/", "target/") if directory else ("source.txt", "target.txt")
    if directory:
        copy = storage.copy_object
        copied = []

        def fail_second(**kwargs):
            copied.append(kwargs["Key"])
            if len(copied) == 2:
                raise ClientError(
                    {
                        "Error": {"Code": "InternalError", "Message": "fixture copy failure"},
                        "ResponseMetadata": {"HTTPStatusCode": 500},
                    },
                    "CopyObject",
                )
            return copy(**kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(storage, "copy_object", fail_second)
            with pytest.raises(ClientError, match="fixture copy failure"):
                await client.rename(old, new)
        actual = {item["Key"] for item in storage.list_objects_v2(Bucket=bucket)["Contents"]}
        assert set(keys).issubset(actual)
        assert "target/a.txt" in actual
        storage.delete_object(Bucket=bucket, Key="target/a.txt")
    await client.rename(old, new)
    assert {item["Key"] for item in storage.list_objects_v2(Bucket=bucket)["Contents"]} == {
        new + key[len(old) :] for key in keys
    }
    for key in keys:
        with storage.get_object(Bucket=bucket, Key=new + key[len(old) :])["Body"] as body:
            assert body.read() == key.encode()


@pytest.mark.asyncio
async def test_s3_preflight_uses_supported_sdk_and_preserves_access_errors():
    storage = boto3.client(
        "s3", region_name="us-east-1", aws_access_key_id="fixture", aws_secret_access_key="fixture"
    )
    client = S3FileClient(
        1,
        S3FileClientConfig(
            endpoint="https://s3.example.test",
            bucket="fixture",
            access_key="fixture",
            access_secret="fixture",
        ),
    )
    client.sync_client = storage
    model = storage.meta.service_model.operation_model("CopyObject")
    assert "IfNoneMatch" not in model.input_shape.members
    with Stubber(storage) as stub:
        stub.add_client_error(
            "head_object",
            service_error_code="AccessDenied",
            http_status_code=403,
            expected_params={"Bucket": "fixture", "Key": "target.txt"},
        )
        with pytest.raises(ClientError, match="AccessDenied"):
            await client.rename("source.txt", "target.txt")
        stub.assert_no_pending_responses()
    await client.close()
