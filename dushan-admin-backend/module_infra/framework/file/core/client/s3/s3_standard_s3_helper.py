from __future__ import annotations

import asyncio

import boto3
from botocore.exceptions import ClientError

from module_infra.framework.file.core.client.s3.s3_file_client_config import S3FileClientConfig


class StandardS3Helper:
    """标准S3辅助类，处理标准S3服务或MinIO等其他S3兼容服务"""

    @staticmethod
    def build_domain(config: S3FileClientConfig) -> str:
        """根据配置构建访问域名"""
        endpoint = config.endpoint
        bucket = config.bucket
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return f"{endpoint}/{bucket}"
        else:
            return f"https://{bucket}.{endpoint}"

    @staticmethod
    def build_endpoint(endpoint: str) -> str:
        """确保endpoint格式正确并添加协议前缀"""
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        return f"https://{endpoint}"

    @staticmethod
    def create_client(config: S3FileClientConfig) -> boto3.client:
        """创建标准S3客户端"""
        endpoint = StandardS3Helper.build_endpoint(config.endpoint)
        region = config.region or "us-east-1"
        s3_config = boto3.session.Config(
            s3={
                "addressing_style": "virtual",
                "payload_signing_enabled": True,
                "chunked_encoding": False,
                "use_accelerate_endpoint": False,
                "use_dualstack_endpoint": False,
            },
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
        )
        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=config.access_key,
            aws_secret_access_key=config.access_secret,
            region_name=region,
            config=s3_config,
        )
        return client

    @staticmethod
    async def upload_file(
        client: boto3.client,
        bucket: str,
        key: str,
        content: bytes,
        file_type: str = "application/octet-stream",
    ) -> None:
        """上传文件到标准S3，处理错误情况"""
        try:
            await asyncio.to_thread(
                client.put_object, Bucket=bucket, Key=key, Body=content, ContentType=file_type
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            error_message = e.response.get("Error", {}).get("Message", "")
            if error_code == "SignatureDoesNotMatch":
                raise IOError(f"S3 签名无效: {error_message}") from e
            elif error_code == "InvalidBucketName":
                raise IOError(f"S3 Bucket名称无效: {error_message}") from e
            else:
                raise
