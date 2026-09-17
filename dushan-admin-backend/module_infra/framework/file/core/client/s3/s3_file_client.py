import asyncio
from urllib.parse import quote

from framework.common.utils.asyncio.asyncio_utils import AsyncioUtils
from module_infra.framework.file.core.client.abstract_file_client import AbstractFileClient
from module_infra.framework.file.core.client.s3.s3_file_presigned_url_resp_dto import (
    FilePresignedUrlRespDTO,
)
from module_infra.framework.file.core.client.s3.s3_service_factory import S3ServiceFactory


class S3FileClient(AbstractFileClient):
    def __init__(self, identifier, config):
        super().__init__(identifier, config)
        self.sync_client = None

    async def do_init(self):
        self.domain = (self.config.domain or S3ServiceFactory.build_domain(self.config)).rstrip("/")
        self.sync_client = await self._call(S3ServiceFactory.create_client, self.config)

    @staticmethod
    async def _call(callback, *args, **kwargs):
        return await AsyncioUtils.run_cancellation_shielded(
            asyncio.to_thread(callback, *args, **kwargs)
        )

    async def upload(self, path, content, file_type=None):
        path = self.key(path)
        await self._call(
            self.sync_client.put_object,
            Bucket=self.config.bucket,
            Key=path,
            Body=content,
            ContentType=file_type or "application/octet-stream",
            ContentLength=len(content),
        )
        return self.domain + "/" + quote(path, safe="/")

    async def delete(self, path):
        await self._call(
            self.sync_client.delete_object, Bucket=self.config.bucket, Key=self.key(path)
        )

    async def get_content(self, path):
        return await self._call(self._read, self.key(path))

    def _read(self, path):
        response = self.sync_client.get_object(Bucket=self.config.bucket, Key=path)
        try:
            return response["Body"].read()
        finally:
            response["Body"].close()

    async def get_presigned_object_url(self, path):
        path = self.key(path)
        url = await self._call(
            self.sync_client.generate_presigned_url,
            "put_object",
            Params={"Bucket": self.config.bucket, "Key": path},
            ExpiresIn=86400,
            HttpMethod="PUT",
        )
        return FilePresignedUrlRespDTO(
            upload_url=url, url=self.domain + "/" + quote(path, safe="/")
        )

    async def presign_get_url(self, path, expiration_seconds=None):
        return await self._call(
            self.sync_client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self.config.bucket, "Key": self.key(path)},
            ExpiresIn=3600 if expiration_seconds is None else expiration_seconds,
            HttpMethod="GET",
        )

    async def list_objects(self, prefix="", delimiter="/"):
        result = await self._call(
            self.sync_client.list_objects_v2,
            Bucket=self.config.bucket,
            Prefix=self.key(prefix) if prefix else "",
            Delimiter=delimiter,
            MaxKeys=1000,
        )
        return {
            "files": [
                {
                    "key": row["Key"],
                    "name": row["Key"].rsplit("/", 1)[-1],
                    "size": row["Size"],
                    "lastModified": row["LastModified"].isoformat(),
                }
                for row in result.get("Contents", [])
                if not row["Key"].endswith("/")
            ],
            "directories": [
                {"prefix": row["Prefix"], "name": row["Prefix"].rstrip("/").rsplit("/", 1)[-1]}
                for row in result.get("CommonPrefixes", [])
            ],
            "isTruncated": result["IsTruncated"],
            "nextMarker": result.get("NextContinuationToken", ""),
        }

    async def rename(self, old_key, new_key):
        old_key, new_key = self.key(old_key), self.key(new_key)
        if old_key == new_key or old_key.endswith("/") and new_key.startswith(old_key):
            raise ValueError("目标不能位于源目录内")
        await self._call(self._rename, old_key, new_key)

    def _rename(self, old_key, new_key):
        if old_key.endswith("/"):
            pages = self.sync_client.get_paginator("list_objects_v2").paginate(
                Bucket=self.config.bucket, Prefix=old_key
            )
            keys = [row["Key"] for page in pages for row in page.get("Contents", [])]
        else:
            keys = [old_key]
        for key in keys:
            target = new_key + key[len(old_key) :]
            self.sync_client.copy_object(
                Bucket=self.config.bucket,
                Key=target,
                CopySource={"Bucket": self.config.bucket, "Key": key},
            )
            self.sync_client.delete_object(Bucket=self.config.bucket, Key=key)

    async def close(self):
        if self.sync_client is not None:
            await self._call(self.sync_client.close)
            self.sync_client = None
