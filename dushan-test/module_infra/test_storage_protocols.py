import io

import pytest

from module_infra.framework.file.core.client.s3.s3_file_client import S3FileClient
from module_infra.framework.file.core.client.s3.s3_file_client_config import S3FileClientConfig
from module_infra.framework.file.core.client.sftp.sftp_file_client_config import (
    SftpFileClientConfig,
)


class StorageClient:
    def __init__(self):
        self.objects = {}
        self.closed = False
        self.body = None
        self.fail_delete = False

    def put_object(self, **values):
        self.objects[values["Key"]] = values["Body"]
        assert values["ContentLength"] == len(values["Body"])

    def get_object(self, **values):
        self.body = io.BytesIO(self.objects[values["Key"]])
        return {"Body": self.body}

    def delete_object(self, **values):
        if self.fail_delete:
            raise OSError("provider-delete-failed")
        self.objects.pop(values["Key"], None)

    def generate_presigned_url(self, operation, *, Params, ExpiresIn, HttpMethod):
        assert Params["Bucket"] == "test-bucket"
        assert (operation, HttpMethod) in {("get_object", "GET"), ("put_object", "PUT")}
        assert ExpiresIn > 0
        return "https://files.example.test/signed"

    def close(self):
        self.closed = True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint",
    [
        "s3.us-east-1.amazonaws.com",
        "oss-cn-hangzhou.aliyuncs.com",
        "cos.ap-shanghai.myqcloud.com",
        "obs.cn-north-4.myhuaweicloud.com",
        "tos-s3-cn-beijing.volces.com",
    ],
)
async def test_s3_protocol_variants_and_resource_cleanup(monkeypatch, endpoint):
    import boto3

    sdk = StorageClient()
    created = []

    def client(service, **kwargs):
        assert service == "s3"
        assert kwargs["aws_access_key_id"] == "test-key"
        assert kwargs["aws_secret_access_key"] == "test-secret"
        created.append(kwargs)
        return sdk

    monkeypatch.setattr(boto3, "client", client)
    config = S3FileClientConfig(
        endpoint=endpoint,
        bucket="test-bucket",
        access_key="test-key",
        access_secret="test-secret",
        region="cn-beijing",
        domain="https://files.example.test",
    )
    storage = S3FileClient(1, config)
    await storage.init()
    assert len(created) == 1
    assert (
        await storage.upload("folder/a b.txt", b"contents", "text/plain")
        == "https://files.example.test/folder/a%20b.txt"
    )
    assert await storage.get_content("folder/a b.txt") == b"contents"
    assert sdk.body.closed
    assert (await storage.get_presigned_object_url("upload.txt")).upload_url.endswith("signed")
    assert (await storage.presign_get_url("download.txt", 30)).endswith("signed")
    sdk.fail_delete = True
    with pytest.raises(OSError, match="provider-delete-failed"):
        await storage.delete("folder/a b.txt")
    sdk.fail_delete = False
    await storage.delete("folder/a b.txt")
    await storage.close()
    assert sdk.closed


def test_sftp_requires_explicit_host_verification():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SftpFileClientConfig(
            base_path="/files",
            domain="https://files.example.test",
            host="localhost",
            port=22,
            username="test",
            password="secret",
            known_hosts=None,
        )


def test_masked_file_configuration_preserves_existing_secret():
    from module_infra.service.file.file_config_service_impl import FileConfigServiceImpl

    previous = dict(
        endpoint="s3.us-east-1.amazonaws.com",
        bucket="test-bucket",
        access_key="key",
        access_secret="secret",
        region="us-east-1",
        domain="https://files.example.test",
        enable_path_style_access=False,
    )
    updated = FileConfigServiceImpl._config(
        20,
        {
            "endpoint": previous["endpoint"],
            "bucket": "test-bucket",
            "accessKey": "key",
            "accessSecret": "new-secret",
            "region": "us-east-1",
            "domain": previous["domain"],
        },
        previous,
    )
    assert updated["access_secret"] == "new-secret"
    omitted = FileConfigServiceImpl._config(
        20,
        {
            "endpoint": previous["endpoint"],
            "bucket": "test-bucket",
            "region": "us-east-1",
            "domain": previous["domain"],
        },
        previous,
    )
    assert omitted["access_secret"] == "secret"


class RemoteFilesystem:
    def __init__(self):
        self.data = {}
        self.closed = 0

    async def make_directory(self, path, **kwargs):
        return None

    async def makedirs(self, path, **kwargs):
        return None

    async def exists(self, path):
        return str(path) in self.data

    async def rename(self, source, target):
        self.data[str(target)] = self.data.pop(str(source))

    async def remove_file(self, path):
        del self.data[str(path)]

    async def remove(self, path):
        del self.data[str(path)]

    def open(self, path, mode):
        from contextlib import asynccontextmanager

        owner = self

        class Stream:
            async def write(self, data):
                owner.data[str(path)] = data

            async def read(self):
                return owner.data[str(path)]

        @asynccontextmanager
        async def opened():
            try:
                yield Stream()
            finally:
                owner.closed += 1

        return opened()

    def upload_stream(self, path):
        return self.open(path, "wb")

    def download_stream(self, path):
        return self.open(path, "rb")


@pytest.mark.asyncio
@pytest.mark.parametrize("protocol", ["ftp", "sftp"])
async def test_remote_storage_uses_explicit_credentials_and_closes_streams(monkeypatch, protocol):
    from contextlib import asynccontextmanager

    remote = RemoteFilesystem()

    @asynccontextmanager
    async def remote_context():
        yield remote

    config = dict(
        base_path="/files",
        domain="https://files.example.test",
        host="localhost",
        port=22,
        username="account",
        password="test-secret",
    )
    if protocol == "ftp":
        import aioftp

        from module_infra.framework.file.core.client.ftp.ftp_file_client import FtpFileClient
        from module_infra.framework.file.core.client.ftp.ftp_file_client_config import (
            FtpFileClientConfig,
        )

        def context(host, port, **kwargs):
            assert kwargs["user"] == "account" and kwargs["password"] == "test-secret"
            return remote_context()

        monkeypatch.setattr(aioftp.Client, "context", context)
        client = FtpFileClient(1, FtpFileClientConfig(**config, mode="PASV"))
    else:
        import asyncssh

        from module_infra.framework.file.core.client.sftp.sftp_file_client import SftpFileClient

        class Connection:
            def start_sftp_client(self):
                return remote_context()

        @asynccontextmanager
        async def connect(host, **kwargs):
            assert kwargs["known_hosts"] == "explicit-host-keys"
            assert (
                kwargs["client_keys"] == []
                and kwargs["config"] == []
                and kwargs["agent_path"] is None
            )
            yield Connection()

        monkeypatch.setattr(asyncssh, "connect", connect)
        client = SftpFileClient(1, SftpFileClientConfig(**config, known_hosts="explicit-host-keys"))
    await client.init()
    await client.upload("one.txt", b"value", "text/plain")
    assert remote.data == {"/files/one.txt": b"value"}
    assert await client.get_content("one.txt") == b"value"
    assert remote.closed == 2
    await client.rename("one.txt", "two.txt")
    await client.delete("two.txt")
    assert remote.data == {}
