from __future__ import annotations

import asyncio

import boto3
from botocore.exceptions import ClientError

from module_infra.framework.file.core.client.s3.s3_file_client_config import S3FileClientConfig


class VolcanoTosHelper:
    """火山云TOS辅助类，提供TOS专用的客户端初始化和上传操作"""

    @staticmethod
    def build_domain(config: S3FileClientConfig) -> str:
        """根据配置构建火山云TOS的访问域名"""
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
        """创建火山云TOS客户端"""
        endpoint = VolcanoTosHelper.build_endpoint(config.endpoint)
        region = config.region or "cn-beijing"
        s3_config = boto3.session.Config(
            s3={
                "addressing_style": "virtual",
                "payload_signing_enabled": False,
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
        """上传文件到火山云TOS，处理特殊错误情况"""
        try:
            await asyncio.to_thread(
                client.put_object, Bucket=bucket, Key=key, Body=content, ContentType=file_type
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            error_message = e.response.get("Error", {}).get("Message", "")
            if error_code == "ContentSHA256Mismatch":
                raise IOError(
                    f"火山云TOS SHA256校验失败: {error_message}\n建议尝试升级boto3或使用火山云官方SDK"
                ) from e
            else:
                raise
